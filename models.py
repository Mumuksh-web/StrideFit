from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Product(Base):
	__tablename__ = "products"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	merchant_id: Mapped[str] = mapped_column(String(100), index=True)
	name: Mapped[str] = mapped_column(String(255))
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	category: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
	sku: Mapped[str] = mapped_column(String(100), unique=True, index=True)
	price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
	currency: Mapped[str] = mapped_column(String(3), default="INR")
	inventory_count: Mapped[int] = mapped_column(Integer, default=0)
	is_active: Mapped[bool] = mapped_column(default=True, index=True)
	product_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	search_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(
		DateTime, server_default=func.now(), onupdate=func.now()
	)


class Conversation(Base):
	__tablename__ = "conversations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
	buyer_id: Mapped[str] = mapped_column(String(100), index=True)
	merchant_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
	channel: Mapped[str] = mapped_column(String(50), default="web")
	status: Mapped[str] = mapped_column(String(30), default="active", index=True)
	context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	last_message_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Order(Base):
	__tablename__ = "orders"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	buyer_id: Mapped[str] = mapped_column(String(100), index=True)
	merchant_id: Mapped[str] = mapped_column(String(100), index=True)
	razorpay_order_id: Mapped[str | None] = mapped_column(
		String(100), unique=True, index=True, nullable=True
	)
	razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
	status: Mapped[str] = mapped_column(String(30), default="created", index=True)
	currency: Mapped[str] = mapped_column(String(3), default="INR")
	subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
	discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
	tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
	total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
	items: Mapped[list | None] = mapped_column(JSON, nullable=True)
	shipping_address: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(
		DateTime, server_default=func.now(), onupdate=func.now()
	)


class AuditLog(Base):
	__tablename__ = "audit_logs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	action_type: Mapped[str] = mapped_column(String(50), index=True, default="unknown")
	reason: Mapped[str | None] = mapped_column(Text, nullable=True)
	limit_check_passed: Mapped[bool] = mapped_column(default=True)
	flagged_for_review: Mapped[bool] = mapped_column(default=False)
	actor_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
	actor_type: Mapped[str] = mapped_column(String(30), default="system")
	action: Mapped[str] = mapped_column(String(100), index=True)
	entity_type: Mapped[str] = mapped_column(String(50), index=True)
	entity_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
	request_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
	details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class MerchantInsight(Base):
	__tablename__ = "merchant_insights"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	merchant_id: Mapped[str] = mapped_column(String(100), index=True)
	insight_type: Mapped[str] = mapped_column(String(50), index=True)
	title: Mapped[str] = mapped_column(String(255))
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	suggested_offer: Mapped[str | None] = mapped_column(Text, nullable=True)
	revenue_impact_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
	priority: Mapped[str] = mapped_column(String(20), default="medium", index=True)
	status: Mapped[str] = mapped_column(String(30), default="new", index=True)
	insight_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
	created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BuyerIntentRecord(Base):
	__tablename__ = "buyer_intents"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	session_id: Mapped[str] = mapped_column(String(100), index=True)
	buyer_id: Mapped[str] = mapped_column(String(100), index=True)
	category: Mapped[str | None] = mapped_column(String(100), nullable=True)
	requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
	budget_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
	intent: Mapped[str | None] = mapped_column(String(30), nullable=True)
	product_found: Mapped[bool] = mapped_column(default=False)
	product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
	purchased: Mapped[bool] = mapped_column(default=False)
	abandoned: Mapped[bool] = mapped_column(default=False)
	rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
	confidence: Mapped[str] = mapped_column(String(10), default="low")
	language: Mapped[str] = mapped_column(String(10), default="english")
	timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


Index("ix_products_merchant_active", Product.merchant_id, Product.is_active)
Index("ix_insights_merchant_status", MerchantInsight.merchant_id, MerchantInsight.status)


__all__ = [
	"AuditLog",
	"Base",
	"BuyerIntentRecord",
	"Conversation",
	"MerchantInsight",
	"Order",
	"Product",
]
