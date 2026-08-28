from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import agent_commerce, audit, buyer_agent, merchant_agent, payments, products

app = FastAPI(
    title="AI Merchant Growth & Shopping Agent",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(buyer_agent.router, prefix="/buyer", tags=["buyer-agent"])
app.include_router(merchant_agent.router, prefix="/merchant", tags=["merchant-agent"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(audit.router, tags=["audit"])
app.include_router(products.router, tags=["products"])
app.include_router(agent_commerce.router, prefix="/api/agent-commerce", tags=["agent-commerce"])


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
