from collections import Counter
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from models import AuditLog, BuyerIntentRecord, MerchantInsight, Order, Product

router = APIRouter()

MERCHANT_ID = "stridefit"
QUALIFYING_STATUSES = ("confirmed",)


class InsightResponse(BaseModel):
	id: int
	insight_type: str
	description: str | None
	suggested_offer: str | None
	revenue_impact_estimate: Decimal
	priority: str
	status: str


class InsightsResponse(BaseModel):
	insights: list[InsightResponse]
	orders_analyzed: int


class DashboardResponse(BaseModel):
	total_orders: int
	order_breakdown: dict[str, int]
	total_revenue: Decimal
	ai_assisted_revenue: Decimal
	estimated_opportunity_impact: Decimal
	active_insights: list[InsightResponse]
	insight_groups: dict[str, int]
	summary: str


def _as_response(insight: MerchantInsight) -> InsightResponse:
	return InsightResponse(
		id=insight.id,
		insight_type=insight.insight_type,
		description=insight.description,
		suggested_offer=insight.suggested_offer,
		revenue_impact_estimate=insight.revenue_impact_estimate,
		priority=insight.priority,
		status=insight.status,
	)


def generate_insights(db: Session) -> tuple[list[MerchantInsight], int]:
	orders = list(
		db.scalars(
			select(Order).where(
				Order.merchant_id == MERCHANT_ID,
				Order.status.in_(QUALIFYING_STATUSES),
			)
		).all()
	)
	pair_counts: Counter[tuple[str, str]] = Counter()
	product_counts: Counter[str] = Counter()
	product_revenue: Counter[str] = Counter()
	category_revenue: Counter[str] = Counter()
	product_categories: dict[str, str] = {}
	for order in orders:
		items = order.items or []
		names = sorted({item.get("name", item.get("sku", "Unknown")) for item in items})
		for item in items:
			name = item.get("name", item.get("sku", "Unknown"))
			quantity = int(item.get("quantity", 1))
			product_counts[name] += quantity
			product_revenue[name] += (order.total_amount / max(len(items), 1)) * quantity
			category = item.get("category")
			if not category:
				product = db.scalar(select(Product).where(Product.id == item.get("product_id")))
				category = product.category if product else "unknown"
			product_categories[name] = category or "unknown"
			category_revenue[category or "unknown"] += order.total_amount / max(len(items), 1)
		for index, first in enumerate(names):
			for second in names[index + 1 :]:
				pair_counts[(first, second)] += 1
		for item in items:
			if item.get("category"):
				product_categories[item.get("name", item.get("sku", "Unknown"))] = item["category"]

	db.query(MerchantInsight).filter(MerchantInsight.merchant_id == MERCHANT_ID, MerchantInsight.status == "active").update({"status": "archived"})
	insights: list[MerchantInsight] = []
	for (first, second), count in pair_counts.most_common(5):
		first_count = product_counts[first]
		percentage = round((count / first_count) * 100) if first_count else 0
		pair_revenue = sum(
			(order.total_amount for order in orders if {item.get("name") for item in (order.items or [])} >= {first, second}),
			Decimal("0"),
		)
		estimate = (pair_revenue * Decimal("0.10")).quantize(Decimal("0.01"))
		insights.append(MerchantInsight(
			merchant_id=MERCHANT_ID,
			insight_type="cross_sell_pattern",
			title=f"{first} + {second}",
			description=f"{percentage}% of {first} buyers also purchase {second} ({count} of {first_count} analyzed orders).",
			suggested_offer=f"{first} + {second} combo par 10% off",
			revenue_impact_estimate=estimate,
			priority="high" if percentage >= 50 else "medium",
			status="active",
			insight_data={"pair_count": count, "base_product_orders": first_count},
		))

	if orders:
		sorted_orders = sorted(orders, key=lambda order: order.created_at or datetime.min)
		recent = sorted_orders[-5:]
		previous = sorted_orders[-10:-5]
		recent_revenue = sum((order.total_amount for order in recent), Decimal("0"))
		previous_revenue = sum((order.total_amount for order in previous), Decimal("0"))
		if previous_revenue:
			trend_percent = ((recent_revenue - previous_revenue) / previous_revenue * 100).quantize(Decimal("0.01"))
			trend = "up" if trend_percent >= 0 else "down"
		else:
			trend_percent = Decimal("0.00")
			trend = "up" if recent_revenue else "flat"
		insights.append(MerchantInsight(
			merchant_id=MERCHANT_ID,
			insight_type="revenue_trend",
			title="Recent revenue trend",
			description=f"Revenue is trending {trend} by {abs(trend_percent)}%: recent {len(recent)} orders generated ₹{recent_revenue}, compared with ₹{previous_revenue} from the prior period.",
			suggested_offer="Run a limited-time campaign if the recent trend is down." if trend == "down" else "Keep the current winning campaign active.",
			revenue_impact_estimate=(recent_revenue * Decimal("0.05")).quantize(Decimal("0.01")),
			priority="high" if abs(trend_percent) >= 20 else "medium",
			status="active",
			insight_data={"recent_revenue": str(recent_revenue), "previous_revenue": str(previous_revenue), "trend_percent": str(trend_percent)},
		))

	if product_counts:
		best_seller, units = product_counts.most_common(1)[0]
		insights.append(MerchantInsight(
			merchant_id=MERCHANT_ID,
			insight_type="top_performing_product",
			title="Top performing product",
			description=f"{best_seller} is your best-seller with {units} units across qualifying orders.",
			suggested_offer=f"Feature {best_seller} prominently and pair it with a complementary accessory.",
			revenue_impact_estimate=product_revenue[best_seller].quantize(Decimal("0.01")),
			priority="high",
			status="active",
			insight_data={"units": units, "product_revenue": str(product_revenue[best_seller])},
		))

	discount_sessions = set(db.scalars(select(AuditLog.actor_id).where(AuditLog.action_type == "discount_offered", AuditLog.actor_id.is_not(None))).all())
	confirmed_buyers = set(db.scalars(select(Order.buyer_id).where(Order.merchant_id == MERCHANT_ID, Order.status.in_(("created", "confirmed")))).all())
	converted_discounts = discount_sessions & confirmed_buyers
	conversion = (Decimal(len(converted_discounts)) / Decimal(len(discount_sessions)) * 100).quantize(Decimal("0.01")) if discount_sessions else Decimal("0.00")
	insights.append(MerchantInsight(
		merchant_id=MERCHANT_ID,
		insight_type="discount_effectiveness",
		title="Discount conversion",
		description=f"Discounts convert {conversion}% of hesitant buyers into qualifying orders ({len(converted_discounts)} of {len(discount_sessions)} sessions).",
		suggested_offer="Continue the bounded 10% offer for hesitant buyers." if discount_sessions else "Collect more discount and order events before optimizing offers.",
		revenue_impact_estimate=sum((order.total_amount for order in orders if order.buyer_id in converted_discounts), Decimal("0")).quantize(Decimal("0.01")),
		priority="high" if conversion >= 50 else "medium",
		status="active",
		insight_data={"discount_sessions": len(discount_sessions), "converted_sessions": len(converted_discounts)},
	))

	if category_revenue:
		best_category, revenue = category_revenue.most_common(1)[0]
		insights.append(MerchantInsight(
			merchant_id=MERCHANT_ID,
			insight_type="category_performance",
			title="Top revenue category",
			description=f"{best_category} generated the highest revenue this period at ₹{revenue}.",
			suggested_offer=f"Build bundles around {best_category} with a complementary StrideFit product.",
			revenue_impact_estimate=revenue.quantize(Decimal("0.01")),
			priority="high",
			status="active",
			insight_data={"category_revenue": {category: str(value) for category, value in category_revenue.items()}},
		))
	if not insights:
		insights.append(MerchantInsight(
			merchant_id=MERCHANT_ID,
			insight_type="cross_sell_pattern",
			title="Early catalog opportunity",
			description="Not enough qualifying orders yet; start testing footwear and sports socks bundles.",
			suggested_offer="Any StrideFit footwear + sports socks combo par 10% off",
			revenue_impact_estimate=Decimal("0.00"),
			priority="low",
			status="active",
			insight_data={"orders_analyzed": len(orders)},
		))
	db.add_all(insights)
	db.commit()
	return insights, len(orders)


@router.get("/insights", response_model=InsightsResponse)
def get_insights(db: Session = Depends(get_db)) -> InsightsResponse:
	insights, orders_analyzed = generate_insights(db)
	under_review = list(
		db.scalars(
			select(MerchantInsight)
			.where(MerchantInsight.merchant_id == MERCHANT_ID, MerchantInsight.status == "under_review")
			.order_by(MerchantInsight.id.desc())
		).all()
	)
	return InsightsResponse(insights=[_as_response(insight) for insight in under_review + insights], orders_analyzed=orders_analyzed)


class BuyerIntentResponse(BaseModel):
	id: int
	session_id: str
	buyer_id: str
	category: str | None
	requirement: str | None
	budget_max: Decimal | None
	intent: str | None
	product_found: bool
	product_id: int | None
	purchased: bool
	abandoned: bool
	rejection_reason: str | None
	confidence: str
	language: str
	timestamp: str


def _as_intent_response(record: BuyerIntentRecord) -> BuyerIntentResponse:
	return BuyerIntentResponse(
		id=record.id,
		session_id=record.session_id,
		buyer_id=record.buyer_id,
		category=record.category,
		requirement=record.requirement,
		budget_max=record.budget_max,
		intent=record.intent,
		product_found=record.product_found,
		product_id=record.product_id,
		purchased=record.purchased,
		abandoned=record.abandoned,
		rejection_reason=record.rejection_reason,
		confidence=record.confidence,
		language=record.language,
		timestamp=record.timestamp.isoformat() if record.timestamp else "",
	)


@router.get("/buyer-intents", response_model=list[BuyerIntentResponse])
def get_buyer_intents(db: Session = Depends(get_db)) -> list[BuyerIntentResponse]:
	records = list(db.scalars(select(BuyerIntentRecord).order_by(BuyerIntentRecord.timestamp.desc())).all())
	return [_as_intent_response(record) for record in records]


@router.patch("/insights/{insight_id}/review", response_model=InsightResponse)
def mark_insight_for_review(insight_id: int, db: Session = Depends(get_db)) -> InsightResponse:
	insight = db.scalar(select(MerchantInsight).where(MerchantInsight.id == insight_id, MerchantInsight.merchant_id == MERCHANT_ID))
	if not insight:
		raise HTTPException(status_code=404, detail="Insight not found")
	insight.status = "active" if insight.status == "under_review" else "under_review"
	db.commit()
	return _as_response(insight)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
	insights = list(db.scalars(select(MerchantInsight).where(MerchantInsight.merchant_id == MERCHANT_ID, MerchantInsight.status == "active").order_by(MerchantInsight.id.desc())).all())
	order_count = db.scalar(select(func.count(Order.id)).where(Order.merchant_id == MERCHANT_ID)) or 0
	order_breakdown = {
		"confirmed": db.scalar(select(func.count(Order.id)).where(Order.merchant_id == MERCHANT_ID, Order.status == "confirmed")) or 0,
		"pending": db.scalar(select(func.count(Order.id)).where(Order.merchant_id == MERCHANT_ID, Order.status == "created")) or 0,
		"failed": db.scalar(select(func.count(Order.id)).where(Order.merchant_id == MERCHANT_ID, Order.status == "failed")) or 0,
	}
	revenue = db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.merchant_id == MERCHANT_ID, Order.status == "confirmed")) or Decimal("0")
	discount_buyers = set(db.scalars(select(AuditLog.actor_id).where(AuditLog.action_type == "discount_offered", AuditLog.actor_id.is_not(None))).all())
	ai_assisted_revenue = db.scalar(
		select(func.coalesce(func.sum(Order.total_amount), 0)).where(
			Order.merchant_id == MERCHANT_ID,
			Order.status == "confirmed",
			Order.buyer_id.in_(discount_buyers) if discount_buyers else False,
		)
	) or Decimal("0")
	ai_assisted_revenue = min(Decimal(str(ai_assisted_revenue)), Decimal(str(revenue)))
	estimated_opportunity_impact = sum((insight.revenue_impact_estimate for insight in insights), Decimal("0"))
	insight_groups = {
		"revenue_trends": sum(insight.insight_type == "revenue_trend" for insight in insights),
		"product_performance": sum(insight.insight_type == "top_performing_product" for insight in insights),
		"discount_impact": sum(insight.insight_type == "discount_effectiveness" for insight in insights),
		"category_performance": sum(insight.insight_type == "category_performance" for insight in insights),
		"cross_sell": sum(insight.insight_type == "cross_sell_pattern" for insight in insights),
	}
	return DashboardResponse(
		total_orders=order_count,
		order_breakdown=order_breakdown,
		total_revenue=Decimal(str(revenue)),
		ai_assisted_revenue=ai_assisted_revenue,
		estimated_opportunity_impact=estimated_opportunity_impact,
		active_insights=[_as_response(insight) for insight in insights],
		insight_groups=insight_groups,
		summary=f"StrideFit ne {order_count} qualifying orders analyze kiye aur confirmed revenue ₹{revenue} hai; insights grouped as revenue trends, product performance, discount impact, category performance, and cross-sell.",
	)


LOST_REVENUE_CONVERSION_RATE = Decimal("0.25")
MIN_CATEGORY_ORDERS_FOR_AOV = 3
OUT_OF_SCOPE_CATEGORIES = {None, "out_of_scope"}
_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


class LostRevenueEvidence(BaseModel):
	intent_count: int
	confidence: str
	aov_used: Decimal | None
	aov_source: str
	conversion_assumption: float


class LostRevenueOpportunity(BaseModel):
	type: str
	title: str
	description: str
	category: str | None
	requirement: str | None
	budget_range: str
	affected_buyers_count: int
	estimated_revenue: Decimal | None
	calculation_note: str
	evidence: LostRevenueEvidence


class LostRevenueSummary(BaseModel):
	total_opportunities: int
	total_estimated_revenue: Decimal


class LostRevenueRadarResponse(BaseModel):
	summary: LostRevenueSummary
	opportunities: list[LostRevenueOpportunity]


def _aggregate_confidence(confidences: list[str]) -> str:
	return min(confidences, key=lambda value: _CONFIDENCE_ORDER.get(value, 0))


def _budget_range_label(budgets: list[Decimal | None]) -> str:
	values = [budget for budget in budgets if budget is not None]
	if not values:
		return "Budget not specified"
	if len(values) < len(budgets):
		return f"≤ ₹{max(values):,.0f} (where specified)"
	low, high = min(values), max(values)
	if low == high:
		return f"≤ ₹{high:,.0f}"
	return f"₹{low:,.0f}–₹{high:,.0f}"


def _category_aov_map(db: Session) -> tuple[dict[str, Decimal], dict[str, int], Decimal | None]:
	confirmed_orders = list(db.scalars(select(Order).where(Order.merchant_id == MERCHANT_ID, Order.status == "confirmed")).all())
	if not confirmed_orders:
		return {}, {}, None
	overall_aov = sum((order.total_amount for order in confirmed_orders), Decimal("0")) / len(confirmed_orders)
	product_by_id = {product.id: product for product in db.scalars(select(Product)).all()}
	totals: dict[str, Decimal] = {}
	counts: dict[str, int] = {}
	for order in confirmed_orders:
		categories_in_order = {
			product_by_id[item.get("product_id")].category
			for item in (order.items or [])
			if product_by_id.get(item.get("product_id")) and product_by_id[item.get("product_id")].category
		}
		for category in categories_in_order:
			totals[category] = totals.get(category, Decimal("0")) + order.total_amount
			counts[category] = counts.get(category, 0) + 1
	category_aov = {category: totals[category] / counts[category] for category in totals}
	return category_aov, counts, overall_aov


def _resolve_aov(
	category: str | None,
	category_aov: dict[str, Decimal],
	category_counts: dict[str, int],
	overall_aov: Decimal | None,
) -> tuple[Decimal | None, str]:
	if category and category_counts.get(category, 0) >= MIN_CATEGORY_ORDERS_FOR_AOV:
		return category_aov[category], "category"
	if overall_aov is not None:
		return overall_aov, "overall"
	return None, "unavailable"


def _build_lost_revenue_opportunity(
	*,
	opportunity_type: str,
	category: str | None,
	requirement: str | None,
	records: list[BuyerIntentRecord],
	category_aov: dict[str, Decimal],
	category_counts: dict[str, int],
	overall_aov: Decimal | None,
) -> LostRevenueOpportunity:
	affected_buyers_count = len({record.session_id for record in records})
	budget_range = _budget_range_label([record.budget_max for record in records])
	confidence = _aggregate_confidence([record.confidence for record in records])
	aov, aov_source = _resolve_aov(category, category_aov, category_counts, overall_aov)
	category_label = category.title() if category else "This Category"

	if opportunity_type == "unmet_demand":
		title = f"{requirement.title()} {category_label}" if requirement else category_label
		description = f"{affected_buyers_count} buyer(s) looked for {title.lower()} but no suitable StrideFit product was found in the catalog."
	else:
		title = f"Price-sensitive {category_label} Demand"
		description = f"{affected_buyers_count} buyer(s) showed price-sensitive signals (budget constraints or cheap/discount language) while shopping for {category_label.lower()}."

	if aov is None:
		estimated_revenue = None
		calculation_note = "No confirmed StrideFit orders exist yet, so there is no defensible average order value — estimated revenue is intentionally left unavailable rather than guessed."
	else:
		estimated_revenue = (Decimal(affected_buyers_count) * LOST_REVENUE_CONVERSION_RATE * aov).quantize(Decimal("0.01"))
		aov_label = "category average order value" if aov_source == "category" else "overall average order value (not enough category-level confirmed orders yet)"
		calculation_note = f"{affected_buyers_count} affected buyer(s) × 25% assumed conversion rate × ₹{aov:,.2f} {aov_label}."

	return LostRevenueOpportunity(
		type=opportunity_type,
		title=title,
		description=description,
		category=category,
		requirement=requirement,
		budget_range=budget_range,
		affected_buyers_count=affected_buyers_count,
		estimated_revenue=estimated_revenue,
		calculation_note=calculation_note,
		evidence=LostRevenueEvidence(
			intent_count=len(records),
			confidence=confidence,
			aov_used=aov,
			aov_source=aov_source,
			conversion_assumption=float(LOST_REVENUE_CONVERSION_RATE),
		),
	)


@router.get("/lost-revenue-radar", response_model=LostRevenueRadarResponse)
def get_lost_revenue_radar(db: Session = Depends(get_db)) -> LostRevenueRadarResponse:
	records = list(db.scalars(select(BuyerIntentRecord)).all())
	category_aov, category_counts, overall_aov = _category_aov_map(db)

	unmet_groups: dict[tuple[str, str | None], list[BuyerIntentRecord]] = {}
	for record in records:
		if record.product_found or record.category in OUT_OF_SCOPE_CATEGORIES:
			continue
		unmet_groups.setdefault((record.category, record.requirement), []).append(record)

	price_groups: dict[str, list[BuyerIntentRecord]] = {}
	for record in records:
		if record.intent != "price_sensitive" or record.category in OUT_OF_SCOPE_CATEGORIES:
			continue
		price_groups.setdefault(record.category, []).append(record)

	opportunities = [
		_build_lost_revenue_opportunity(
			opportunity_type="unmet_demand",
			category=category,
			requirement=requirement,
			records=group_records,
			category_aov=category_aov,
			category_counts=category_counts,
			overall_aov=overall_aov,
		)
		for (category, requirement), group_records in unmet_groups.items()
	]
	opportunities += [
		_build_lost_revenue_opportunity(
			opportunity_type="price_sensitive",
			category=category,
			requirement=None,
			records=group_records,
			category_aov=category_aov,
			category_counts=category_counts,
			overall_aov=overall_aov,
		)
		for category, group_records in price_groups.items()
	]

	total_estimated_revenue = sum(
		(opportunity.estimated_revenue for opportunity in opportunities if opportunity.estimated_revenue is not None),
		Decimal("0"),
	)
	return LostRevenueRadarResponse(
		summary=LostRevenueSummary(total_opportunities=len(opportunities), total_estimated_revenue=total_estimated_revenue),
		opportunities=opportunities,
	)


COMMERCE_READINESS_COMPONENT_MAX = 20


class CommerceReadinessComponent(BaseModel):
	name: str
	score: int | None
	max: int
	explanation: str
	status: str


class CommerceReadinessResponse(BaseModel):
	overall_score: int | None
	overall_label: str
	components: list[CommerceReadinessComponent]


def _catalog_readability_component(db: Session) -> CommerceReadinessComponent:
	products = list(db.scalars(select(Product).where(Product.merchant_id == MERCHANT_ID)).all())
	if not products:
		return CommerceReadinessComponent(name="Catalog Readability", score=None, max=COMMERCE_READINESS_COMPONENT_MAX, explanation="No products exist in the catalog yet.", status="unavailable")
	complete = sum(1 for product in products if product.name and product.category and product.price is not None and product.description)
	score = round((complete / len(products)) * COMMERCE_READINESS_COMPONENT_MAX)
	return CommerceReadinessComponent(
		name="Catalog Readability",
		score=score,
		max=COMMERCE_READINESS_COMPONENT_MAX,
		explanation=f"{complete} of {len(products)} products have complete data (name, category, price, description).",
		status="available",
	)


def _product_discovery_component(db: Session) -> CommerceReadinessComponent:
	intents = list(db.scalars(select(BuyerIntentRecord)).all())
	in_scope = [intent for intent in intents if intent.category not in OUT_OF_SCOPE_CATEGORIES]
	out_of_scope_count = len(intents) - len(in_scope)
	if not in_scope:
		return CommerceReadinessComponent(name="Product Discovery", score=None, max=COMMERCE_READINESS_COMPONENT_MAX, explanation="No in-scope buyer intent data recorded yet.", status="unavailable")
	found = sum(1 for intent in in_scope if intent.product_found)
	score = round((found / len(in_scope)) * COMMERCE_READINESS_COMPONENT_MAX)
	return CommerceReadinessComponent(
		name="Product Discovery",
		score=score,
		max=COMMERCE_READINESS_COMPONENT_MAX,
		explanation=f"{found} of {len(in_scope)} in-scope buyer intents found a matching product ({out_of_scope_count} out-of-scope requests excluded).",
		status="available",
	)


def _confirmed_and_failed_order_counts(db: Session) -> tuple[int, int]:
	confirmed = db.scalar(select(func.count(Order.id)).where(Order.merchant_id == MERCHANT_ID, Order.status == "confirmed")) or 0
	failed = db.scalar(select(func.count(Order.id)).where(Order.merchant_id == MERCHANT_ID, Order.status == "failed")) or 0
	return confirmed, failed


def _conversational_checkout_component(db: Session) -> CommerceReadinessComponent:
	confirmed, failed = _confirmed_and_failed_order_counts(db)
	total = confirmed + failed
	if total == 0:
		return CommerceReadinessComponent(name="Conversational Checkout", score=None, max=COMMERCE_READINESS_COMPONENT_MAX, explanation="No checkout attempts have reached a final outcome (confirmed or failed) yet.", status="unavailable")
	score = round((confirmed / total) * COMMERCE_READINESS_COMPONENT_MAX)
	return CommerceReadinessComponent(
		name="Conversational Checkout",
		score=score,
		max=COMMERCE_READINESS_COMPONENT_MAX,
		explanation=f"{confirmed} of {total} checkout attempts that reached a final outcome were confirmed ({failed} failed).",
		status="available",
	)


def _payment_execution_component(db: Session) -> CommerceReadinessComponent:
	confirmed, failed = _confirmed_and_failed_order_counts(db)
	total = confirmed + failed
	if total == 0:
		return CommerceReadinessComponent(name="Payment Execution", score=None, max=COMMERCE_READINESS_COMPONENT_MAX, explanation="No confirm-order attempts have reached a final outcome yet.", status="unavailable")
	score = round((confirmed / total) * COMMERCE_READINESS_COMPONENT_MAX)
	return CommerceReadinessComponent(
		name="Payment Execution",
		score=score,
		max=COMMERCE_READINESS_COMPONENT_MAX,
		explanation=f"{confirmed} of {total} confirm-order attempts succeeded via Razorpay ({failed} failed).",
		status="available",
	)


def _transaction_reliability_component(db: Session) -> CommerceReadinessComponent:
	total = db.scalar(select(func.count(AuditLog.id))) or 0
	if total == 0:
		return CommerceReadinessComponent(name="Transaction Reliability", score=None, max=COMMERCE_READINESS_COMPONENT_MAX, explanation="No audit log entries recorded yet.", status="unavailable")
	passed = db.scalar(select(func.count(AuditLog.id)).where(AuditLog.limit_check_passed.is_(True))) or 0
	score = round((passed / total) * COMMERCE_READINESS_COMPONENT_MAX)
	return CommerceReadinessComponent(
		name="Transaction Reliability",
		score=score,
		max=COMMERCE_READINESS_COMPONENT_MAX,
		explanation=f"{passed} of {total} audit log entries passed the discount/limit check.",
		status="available",
	)


def _aggregate_overall_score(components: list[CommerceReadinessComponent]) -> tuple[int | None, str]:
	available = [component for component in components if component.status == "available" and component.score is not None]
	if not available:
		return None, "Insufficient data"
	overall_score = round(sum(component.score for component in available) / (COMMERCE_READINESS_COMPONENT_MAX * len(available)) * 100)
	if overall_score >= 80:
		overall_label = "Excellent readiness"
	elif overall_score >= 60:
		overall_label = "Good readiness"
	else:
		overall_label = "Needs improvement"
	return overall_score, overall_label


@router.get("/commerce-readiness", response_model=CommerceReadinessResponse)
def get_commerce_readiness(db: Session = Depends(get_db)) -> CommerceReadinessResponse:
	components = [
		_catalog_readability_component(db),
		_product_discovery_component(db),
		_conversational_checkout_component(db),
		_payment_execution_component(db),
		_transaction_reliability_component(db),
	]
	overall_score, overall_label = _aggregate_overall_score(components)
	return CommerceReadinessResponse(overall_score=overall_score, overall_label=overall_label, components=components)
