from database import Base, engine
from models import BuyerIntentRecord  # noqa: F401 — import registers all models on Base.metadata

Base.metadata.create_all(bind=engine)
print("Ensured buyer_intents table exists (create_all only creates missing tables, existing tables are untouched).")
