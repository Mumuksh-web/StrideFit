from sqlalchemy import select

from database import Base, engine, SessionLocal
from models import Product


PRODUCTS = [
    ("STF-RUN-001", "StrideFit AeroRun 2.0", "Lightweight daily running shoes with breathable mesh and cushioned foam for everyday road runs.", "running shoes", 2499, ["running", "daily training", "road running", "breathable", "cushion"]),
    ("STF-RUN-002", "StrideFit SprintEdge", "Responsive running shoes with a stable heel and grippy outsole for tempo runs and gym sessions.", "running shoes", 3299, ["running", "tempo", "gym", "stability", "grip"]),
    ("STF-RUN-003", "StrideFit Marathon Pro", "High-cushion performance shoes designed for long-distance training with a supportive midsole.", "running shoes", 4499, ["running", "marathon", "long distance", "performance", "high cushion"]),
    ("STF-RUN-004", "StrideFit TrailRush", "Rugged trail runners with textured traction and reinforced toe protection for outdoor routes.", "running shoes", 3899, ["running", "trail", "outdoor", "traction", "durable"]),
    ("STF-SNK-001", "StrideFit StreetFlex", "Clean everyday sneakers with flexible cushioning and a versatile low-profile silhouette.", "sneakers", 1999, ["sneakers", "casual", "everyday", "streetwear", "flexible"]),
    ("STF-SNK-002", "StrideFit Court Classic", "Retro-inspired casual sneakers with a padded collar and durable rubber cupsole.", "sneakers", 2799, ["sneakers", "casual", "retro", "court", "rubber sole"]),
    ("STF-SNK-003", "StrideFit Urban Knit", "Breathable knit sneakers with a lightweight sole for commuting, travel, and daily wear.", "sneakers", 3499, ["sneakers", "casual", "knit", "travel", "lightweight"]),
    ("STF-SCK-001", "StrideFit Active Crew Socks", "Moisture-wicking crew socks with arch support and cushioned zones for training.", "sports socks", 299, ["socks", "crew", "moisture wicking", "arch support", "training"]),
    ("STF-SCK-002", "StrideFit RunLite Ankle Socks", "Low-cut running socks with breathable mesh panels and a smooth anti-blister toe seam.", "sports socks", 249, ["socks", "ankle", "running", "breathable", "anti blister"]),
    ("STF-SCK-003", "StrideFit Performance Socks 3-Pack", "Three pairs of quick-dry performance socks with compression arch bands for active days.", "sports socks", 499, ["socks", "3 pack", "quick dry", "compression", "sports"]),
    ("STF-ACC-001", "StrideFit LockLace Reflective", "Reflective no-tie replacement laces that keep your fit secure for low-light runs.", "sports accessories", 199, ["laces", "reflective", "no tie", "running", "replacement"]),
    ("STF-ACC-002", "StrideFit ComfortStep Insoles", "Dual-density comfort insoles with heel cushioning for walking, commuting, and everyday shoes.", "sports accessories", 399, ["insoles", "heel cushion", "comfort", "walking", "support"]),
    ("STF-ACC-003", "StrideFit FreshStep Insoles", "Breathable everyday insoles with lightweight foam and odor-control lining.", "sports accessories", 299, ["insoles", "breathable", "foam", "odor control", "everyday"]),
    ("STF-ACC-004", "StrideFit SpeedLace Basic", "Durable elastic replacement laces for quick fit adjustments across sports and casual shoes.", "sports accessories", 159, ["laces", "elastic", "replacement", "sports", "casual"]),
]


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    existing_skus = set(db.scalars(select(Product.sku)).all())
    for sku, name, description, category, price, tags in PRODUCTS:
        if sku not in existing_skus:
            db.add(Product(merchant_id="stridefit", sku=sku, name=name, description=description, category=category, price=price, currency="INR", inventory_count=100, search_tags=tags, product_metadata={"brand": "StrideFit"}))
    db.commit()

print(f"Seeded {len(PRODUCTS) - len(existing_skus.intersection({item[0] for item in PRODUCTS}))} new StrideFit products")
