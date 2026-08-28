from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Product
from services.negotiation_rules import MAX_DISCOUNT_PERCENT

router = APIRouter()

MERCHANT_NAME = "StrideFit"
MERCHANT_ID = "stridefit"
CURRENCY = "INR"


class AgentCatalogProduct(BaseModel):
	id: int
	name: str
	category: str | None
	price: Decimal
	description: str | None
	in_stock: bool


class AgentCommerceCapabilities(BaseModel):
	checkout_supported: bool
	order_creation_endpoint: str
	order_confirmation_endpoint: str
	requires_explicit_confirmation: bool


class AgentCommercePolicies(BaseModel):
	max_discount_percent: int
	discount_negotiable: bool


class AgentCommerceCatalogResponse(BaseModel):
	merchant: str
	currency: str
	products: list[AgentCatalogProduct]
	capabilities: AgentCommerceCapabilities
	policies: AgentCommercePolicies


@router.get(
	"/catalog",
	response_model=AgentCommerceCatalogResponse,
	summary="Machine-readable StrideFit catalog for external AI agents",
	description=(
		"This read-only endpoint exposes StrideFit's machine-readable catalog and transaction "
		"capabilities for external AI agents. It never creates orders, modifies data, or triggers "
		"Razorpay — it only reads the existing products table."
	),
)
def get_agent_commerce_catalog(db: Session = Depends(get_db)) -> AgentCommerceCatalogResponse:
	products = list(
		db.scalars(
			select(Product)
			.where(Product.merchant_id == MERCHANT_ID, Product.is_active.is_(True))
			.order_by(Product.id)
		).all()
	)
	return AgentCommerceCatalogResponse(
		merchant=MERCHANT_NAME,
		currency=CURRENCY,
		products=[
			AgentCatalogProduct(
				id=product.id,
				name=product.name,
				category=product.category,
				price=product.price,
				description=product.description,
				in_stock=product.inventory_count > 0,
			)
			for product in products
		],
		capabilities=AgentCommerceCapabilities(
			checkout_supported=True,
			order_creation_endpoint="/payments/create-order",
			order_confirmation_endpoint="/payments/confirm-order",
			requires_explicit_confirmation=True,
		),
		policies=AgentCommercePolicies(
			max_discount_percent=MAX_DISCOUNT_PERCENT,
			discount_negotiable=True,
		),
	)
