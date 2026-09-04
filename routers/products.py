import logging
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import MerchantInsight, Order, Product

router = APIRouter()

logger = logging.getLogger(__name__)

MERCHANT_ID = "stridefit"
CROSS_SELL_MAX = 3


class ProductResponse(BaseModel):
    id: int
    name: str
    category: str | None
    price: float
    description: str | None
    stock: int
    search_tags: list | None = None


@router.get("/products", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)) -> list[ProductResponse]:
    products = db.scalars(
        select(Product)
        .where(Product.merchant_id == "stridefit", Product.is_active.is_(True))
        .order_by(Product.id)
    ).all()
    return [
        ProductResponse(
            id=product.id,
            name=product.name,
            category=product.category,
            price=float(product.price),
            description=product.description,
            stock=product.inventory_count,
            search_tags=product.search_tags,
        )
        for product in products
    ]


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductResponse:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.merchant_id == "stridefit",
            Product.is_active.is_(True),
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse(
        id=product.id,
        name=product.name,
        category=product.category,
        price=float(product.price),
        description=product.description,
        stock=product.inventory_count,
        search_tags=product.search_tags,
    )


class CrossSellSuggestion(BaseModel):
    id: int
    name: str
    price: float
    category: str | None
    reason: str


def _suggestion(product: Product, reason: str) -> CrossSellSuggestion:
    return CrossSellSuggestion(
        id=product.id,
        name=product.name,
        price=float(product.price),
        category=product.category,
        reason=reason,
    )


def _active_products(db: Session) -> list[Product]:
    """In-stock, active StrideFit catalog — same filters checkout's create-order uses."""
    return list(
        db.scalars(
            select(Product).where(
                Product.merchant_id == MERCHANT_ID,
                Product.is_active.is_(True),
                Product.inventory_count > 0,
            )
        ).all()
    )


def _cross_sell_from_insights(db: Session, product: Product, catalog: list[Product]) -> list[CrossSellSuggestion]:
    """STEP 1 — reuse the merchant's own observed cross-sell patterns.

    ``generate_insights()`` in the merchant agent stores each observed pair as a
    ``cross_sell_pattern`` insight whose ``title`` is ``"<name A> + <name B>"``
    (the two product names, alphabetically sorted). If the selected product is one
    side of such a pair, the other side is a real, merchant-evidenced complement.
    """
    insights = db.scalars(
        select(MerchantInsight).where(
            MerchantInsight.merchant_id == MERCHANT_ID,
            MerchantInsight.insight_type == "cross_sell_pattern",
            MerchantInsight.status.in_(("active", "under_review")),
        )
    ).all()
    if not insights:
        return []

    products_by_name = {item.name: item for item in catalog}
    seen: set[int] = {product.id}
    results: list[CrossSellSuggestion] = []
    for insight in insights:
        parts = [part.strip() for part in (insight.title or "").split(" + ")]
        if len(parts) != 2 or product.name not in parts:
            continue
        partner_name = parts[1] if parts[0] == product.name else parts[0]
        partner = products_by_name.get(partner_name)  # verified to exist in the catalog
        if partner is None or partner.id in seen:
            continue
        seen.add(partner.id)
        results.append(_suggestion(partner, f"Often purchased with {product.name}"))
        if len(results) >= CROSS_SELL_MAX:
            break
    return results


def _cross_sell_fallback(db: Session, product: Product, catalog: list[Product]) -> list[CrossSellSuggestion]:
    """STEP 2 — database-driven fallback when no matching insight exists.

    2a. Mine confirmed order history for products co-purchased with the selected
        product (or its category), keeping only *different*-category items so the
        suggestion is complementary rather than a near-duplicate.
    2b. If there is no co-purchase signal yet, surface the cheapest in-stock item
        from each of the other catalog categories (discovered dynamically) — an
        add-on-style pick that lifts average order value without a hardcoded list.
    """
    by_id = {item.id: item for item in catalog}
    selected_category = product.category

    confirmed_orders = db.scalars(
        select(Order).where(Order.merchant_id == MERCHANT_ID, Order.status == "confirmed")
    ).all()

    co_counts: Counter[int] = Counter()
    for order in confirmed_orders:
        item_ids = [item.get("product_id") for item in (order.items or []) if item.get("product_id")]
        order_categories = {by_id[pid].category for pid in item_ids if pid in by_id}
        touches_selection = product.id in item_ids or (
            selected_category is not None and selected_category in order_categories
        )
        if not touches_selection:
            continue
        for pid in item_ids:
            partner = by_id.get(pid)
            if partner is None or partner.id == product.id:
                continue
            if selected_category is not None and partner.category == selected_category:
                continue
            co_counts[pid] += 1

    if co_counts:
        ranked = sorted(co_counts.items(), key=lambda pair: (-pair[1], float(by_id[pair[0]].price)))
        reason = f"Frequently bought with {selected_category}" if selected_category else "Frequently bought together"
        return [_suggestion(by_id[pid], reason) for pid, _ in ranked[:CROSS_SELL_MAX]]

    cheapest_by_category: dict[str, Product] = {}
    for candidate in sorted(catalog, key=lambda item: float(item.price)):
        category = candidate.category
        if not category or category == selected_category or candidate.id == product.id:
            continue
        cheapest_by_category.setdefault(category, candidate)

    picks = sorted(cheapest_by_category.values(), key=lambda item: float(item.price))[:CROSS_SELL_MAX]
    reason = f"Pairs well with {selected_category}" if selected_category else "Popular StrideFit add-on"
    return [_suggestion(pick, reason) for pick in picks]


@router.get("/products/{product_id}/cross-sell", response_model=list[CrossSellSuggestion])
def get_cross_sell(product_id: int, db: Session = Depends(get_db)) -> list[CrossSellSuggestion]:
    """Complementary product suggestions for the checkout panel.

    This is a non-critical enhancement: any internal failure returns an empty list
    (HTTP 200) rather than an error, so the checkout / Razorpay flow is never
    blocked or made dependent on cross-sell.
    """
    try:
        product = db.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.merchant_id == MERCHANT_ID,
                Product.is_active.is_(True),
            )
        )
        if product is None:
            return []

        catalog = [item for item in _active_products(db) if item.id != product.id]
        suggestions = _cross_sell_from_insights(db, product, catalog)
        if not suggestions:
            suggestions = _cross_sell_fallback(db, product, catalog)
        return suggestions[:CROSS_SELL_MAX]
    except Exception:  # noqa: BLE001 - cross-sell must never break checkout
        logger.exception("cross-sell generation failed for product %s", product_id)
        return []
