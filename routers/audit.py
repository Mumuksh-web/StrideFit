from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import AuditLog, Order

router = APIRouter()


class AuditLogResponse(BaseModel):
	id: int
	timestamp: str
	action: str
	amount: str | None
	reason: str | None
	limit_check_passed: bool
	status: str
	actor_id: str | None
	flagged_for_review: bool


def _to_response(db: Session, log: AuditLog) -> AuditLogResponse:
	amount = None
	status = "recorded"
	if log.entity_id and log.entity_type == "order":
		order = db.scalar(select(Order).where(Order.id == int(log.entity_id)))
		if order:
			amount = str(order.total_amount)
			status = order.status
	return AuditLogResponse(
		id=log.id,
		timestamp=log.created_at.isoformat() if log.created_at else "",
		action=log.action_type or log.action,
		amount=amount,
		reason=log.reason or log.details.get("reason") if log.details else log.reason,
		limit_check_passed=log.limit_check_passed,
		status=status,
		actor_id=log.actor_id,
		flagged_for_review=log.flagged_for_review,
	)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db)) -> list[AuditLogResponse]:
	logs = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)).all())
	return [_to_response(db, log) for log in logs]


@router.patch("/audit-logs/{log_id}/flag", response_model=AuditLogResponse)
def flag_audit_log(log_id: int, db: Session = Depends(get_db)) -> AuditLogResponse:
	log = db.get(AuditLog, log_id)
	if not log:
		raise HTTPException(status_code=404, detail="Audit log not found")
	log.flagged_for_review = True
	db.commit()
	return _to_response(db, log)


def record_money_decision(
	db: Session,
	*,
	action_type: str,
	reason: str,
	limit_check_passed: bool,
	entity_id: str | None = None,
	actor_id: str | None = None,
) -> AuditLog:
	entry = AuditLog(
		action_type=action_type,
		action=action_type,
		reason=reason,
		limit_check_passed=limit_check_passed,
		entity_type="order",
		entity_id=entity_id,
		actor_id=actor_id,
		actor_type="buyer" if actor_id else "system",
		created_at=datetime.utcnow(),
	)
	db.add(entry)
	return entry
