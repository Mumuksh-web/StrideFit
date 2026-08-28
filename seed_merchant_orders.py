from decimal import Decimal

from sqlalchemy import select

from database import Base, SessionLocal, engine
from models import Order, Product


Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    products = {product.sku: product for product in db.scalars(select(Product)).all()}
    demo_orders = [
        ("stridefit-demo-001", ["STF-SNK-001", "STF-SCK-001"]),
        ("stridefit-demo-002", ["STF-SNK-001", "STF-SCK-001"]),
        ("stridefit-demo-003", ["STF-SNK-001", "STF-SCK-002"]),
        ("stridefit-demo-004", ["STF-SNK-001"]),
        ("stridefit-demo-005", ["STF-RUN-001", "STF-SCK-001"]),
        ("stridefit-demo-006", ["STF-RUN-001", "STF-SCK-001"]),
        ("stridefit-demo-007", ["STF-RUN-002", "STF-ACC-002"]),
        ("stridefit-demo-008", ["STF-SNK-002", "STF-SCK-003"]),
    ]

    existing = set(
        db.scalars(
            select(Order.buyer_id).where(Order.buyer_id.like("stridefit-demo-%"))
        ).all()
    )
    for buyer_id, skus in demo_orders:
        if buyer_id in existing:
            continue
        items = [{"product_id": products[sku].id, "sku": sku, "name": products[sku].name, "quantity": 1} for sku in skus]
        total = sum((products[sku].price for sku in skus), Decimal("0"))
        db.add(
            Order(
                buyer_id=buyer_id,
                merchant_id="stridefit",
                status="confirmed",
                currency="INR",
                subtotal=total,
                discount_amount=Decimal("0"),
                tax_amount=Decimal("0"),
                total_amount=total,
                items=items,
            )
        )
    db.commit()

print(f"Seeded {len(demo_orders) - len(existing)} demo orders")
