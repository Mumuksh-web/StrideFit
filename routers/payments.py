from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import BuyerIntentRecord, Conversation, Order, Product
from services.razorpay_service import create_order
from routers.audit import record_money_decision
from services.negotiation_rules import MAX_DISCOUNT_PERCENT, evaluate_discount

router = APIRouter()


class CreateOrderRequest(BaseModel):
	product_id: int = Field(gt=0)
	session_id: str = Field(min_length=1, max_length=100)


class CreateOrderResponse(BaseModel):
	order_id: str | None = None
	pending_order_id: int | None = None
	amount: Decimal
	discount_amount: Decimal
	final_amount: Decimal
	currency: str
	status: str
	confirmation_required: bool


class PaymentFailureResponse(BaseModel):
	status: str = "failed"
	message: str
	retry_available: bool = True


class ConfirmOrderRequest(BaseModel):
	pending_order_id: int = Field(gt=0)
	session_id: str = Field(min_length=1, max_length=100)
	confirmation: str = Field(min_length=1)
	simulate_failure: bool = False


@router.post("/create-order", response_model=CreateOrderResponse)
def create_product_order(
	request: CreateOrderRequest,
	db: Session = Depends(get_db),
) -> CreateOrderResponse:
	product = db.scalar(
		select(Product).where(
			Product.id == request.product_id,
			Product.merchant_id == "stridefit",
			Product.is_active.is_(True),
			Product.inventory_count > 0,
		)
	)
	if product is None:
		raise HTTPException(status_code=404, detail="Product not found or unavailable")
	conversation = db.scalar(select(Conversation).where(Conversation.session_id == request.session_id))
	buyer_id = conversation.buyer_id if conversation and conversation.buyer_id != "guest" else request.session_id

	discount = evaluate_discount(True, product.price)
	final_amount = product.price - discount

	order = Order(
		buyer_id=buyer_id,
		merchant_id=product.merchant_id,
		status="pending_confirmation",
		currency=product.currency,
		subtotal=product.price,
		discount_amount=discount,
		tax_amount=Decimal("0"),
		total_amount=final_amount,
		items=[{"product_id": product.id, "sku": product.sku, "name": product.name, "quantity": 1}],
	)
	db.add(order)
	record_money_decision(
		db,
		action_type="discount_offered" if discount else "order_quote_created",
		reason=f"Checkout discount offered for the selected product; discount capped at {MAX_DISCOUNT_PERCENT}%.",
		limit_check_passed=discount <= product.price * Decimal(MAX_DISCOUNT_PERCENT) / Decimal("100"),
		entity_id=str(product.id),
		actor_id=buyer_id,
	)
	db.commit()

	return CreateOrderResponse(
		pending_order_id=order.id,
		amount=product.price,
		discount_amount=discount,
		final_amount=final_amount,
		currency=product.currency,
		status=order.status,
		confirmation_required=True,
	)


@router.post("/confirm-order", response_model=CreateOrderResponse | PaymentFailureResponse)
def confirm_product_order(
	request: ConfirmOrderRequest,
	db: Session = Depends(get_db),
) -> CreateOrderResponse:
	if request.confirmation.strip().lower() not in {"yes", "confirm", "confirmed", "haan", "han"}:
		raise HTTPException(status_code=400, detail="Explicit yes/confirm is required")

	conversation = db.scalar(select(Conversation).where(Conversation.session_id == request.session_id))
	buyer_id = conversation.buyer_id if conversation and conversation.buyer_id != "guest" else request.session_id
	order = db.scalar(
		select(Order).where(
			Order.id == request.pending_order_id,
			Order.buyer_id == buyer_id,
			Order.status == "pending_confirmation",
		)
	)
	if order is None:
		raise HTTPException(status_code=404, detail="Pending order not found")

	try:
		if request.simulate_failure:
			raise RuntimeError("Simulated Razorpay gateway failure for demo testing")
		razorpay_order = create_order(order.total_amount, order.currency)
	except Exception as error:
		order.status = "failed"
		record_money_decision(
			db,
			action_type="payment_failed",
			reason=str(error),
			limit_check_passed=True,
			entity_id=str(order.id),
			actor_id=buyer_id,
		)
		db.commit()
		return PaymentFailureResponse(
			message="Maaf kijiye, payment process karne mein dikkat aa rahi hai. Aapke account se koi paisa deduct NAHI hua hai. Kripya thodi der baad dobara try karein ya support se contact karein.",
		)

	order.razorpay_order_id = razorpay_order["id"]
	order.status = "confirmed"
	latest_intent = db.scalar(
		select(BuyerIntentRecord)
		.where(BuyerIntentRecord.session_id == request.session_id)
		.order_by(BuyerIntentRecord.timestamp.desc())
	)
	if latest_intent is not None:
		latest_intent.purchased = True
	record_money_decision(
		db,
		action_type="order_confirmed",
		reason="Buyer explicitly confirmed the pending order; Razorpay order created for final amount.",
		limit_check_passed=order.discount_amount <= order.subtotal * Decimal(MAX_DISCOUNT_PERCENT) / Decimal("100"),
		entity_id=str(order.id),
			actor_id=buyer_id,
	)
	db.commit()
	return CreateOrderResponse(
		order_id=order.razorpay_order_id,
		amount=order.subtotal,
		discount_amount=order.discount_amount,
		final_amount=order.total_amount,
		currency=order.currency,
		status=order.status,
		confirmation_required=False,
	)
