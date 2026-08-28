# StrideFit AI — AI Merchant Growth & Shopping Agent

> Conversational commerce and merchant growth intelligence for a D2C footwear & sportswear brand, built on FastAPI + Razorpay.

## Overview

StrideFit AI is a two-sided agentic commerce system built for **Razorpay Buildathon — Track 01: AI Growth & Agentic Commerce**. On the buyer side, an AI shopping agent understands natural, mixed Hindi/English requests, recommends real catalog products, and walks the buyer through a safety-gated Razorpay checkout. On the merchant side, an AI growth agent turns raw orders and buyer intent signals into explainable insights — lost revenue opportunities, a commerce-readiness score, and a fully auditable trail of every money-related decision the system makes.

The goal: prove that a merchant's commerce stack can be both **conversational for buyers** and **transparent/safe for the business**, while staying discoverable to other AI agents via a machine-readable catalog endpoint.

## Key Features

**Buyer Agent**
- Conversational shopping in natural Hindi/English/mixed input
- Context-aware: remembers the last 3 exchanges, so "socks chahiye" → "under 500" is understood as one combined request
- Catalog-grounded — every recommendation is a real row from the `products` table; the agent never invents a product, price, or category
- Smart out-of-scope handling — politely (and non-repetitively) declines genuinely unrelated requests, while inferring indirect-but-relevant ones (e.g. "gym ke liye kuch chahiye" → footwear)
- Persistent chat history across page refreshes

**Merchant Agent**
- Growth insights generated from real order history: cross-sell patterns, revenue trends, top-performing products, discount effectiveness, category performance
- Insights can be marked / unmarked "under review" from the dashboard

**"The Bar" — financial safety controls**
| Principle | What it means here |
|---|---|
| **Bounded** | Discounts are capped at a fixed `MAX_DISCOUNT_PERCENT` (10%) via a deterministic formula — never LLM-decided |
| **Gated** | A Razorpay order is only created after the buyer gives an *explicit* confirmation (`"yes"` / `"confirm"`); nothing is auto-charged |
| **Explainable** | Every discount or order decision is written with a human-readable `reason` |
| **Audit Trail** | Every money-related action (discount offered, order confirmed, payment failed) is persisted to `audit_logs` with a pass/fail limit check |
| **Failure Handling** | Gateway failures are caught, the order is marked `failed`, and the buyer is told explicitly that no money was deducted |

**Buyer Intent Intelligence + Lost Revenue Radar**
- Every chat turn's extracted intent (category, budget, requirement, confidence, language) is logged to `buyer_intents`
- The Lost Revenue Radar mines that table for **unmet demand** and **price-sensitive** patterns and estimates recoverable revenue — using real average-order-value data, with an explicitly-labelled *assumed* conversion rate, and never a fabricated number when the data isn't there yet

**AI Commerce Readiness Score**
- A single 0–100 score computed live from catalog completeness, product-discovery success rate, checkout completion rate, payment success rate, and audit-log reliability — each component shows its own raw numbers, and any component without enough data is marked unavailable rather than guessed

**Agent-to-Agent Commerce endpoint**
- A read-only, machine-readable catalog endpoint so an external AI agent can discover what StrideFit sells and how to transact with it, without any custom integration work

**Mark for Review**
- Buyers can bookmark products into a local "saved for review" list
- Merchants can mark/unmark growth insights as "under review" and flag audit-log entries for follow-up

**Razorpay Test-Mode integration**
- Real Razorpay order creation in test mode, with simulated-failure support for demoing the failure-handling path safely

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2.0, Uvicorn |
| Database | MySQL (via PyMySQL) |
| Frontend | React 19, Vite, Tailwind CSS, React Router |
| LLM integration | OpenAI structured outputs when `LLM_API_KEY` is set; deterministic rule-based extraction fallback otherwise, so buyer-intent extraction never hard-depends on an external LLM |
| Payments | Razorpay Python SDK (test mode) |
| Config | pydantic-settings + `.env` |

## Architecture Overview

```
┌────────────────────┐        ┌──────────────────────┐        ┌────────────────────┐
│   Buyer (browser)   │        │   Merchant (browser)  │        │  External AI Agent  │
│  Shop / Catalog /    │        │   Merchant Dashboard   │        │                      │
│  Product Detail      │        │                        │        │                      │
└─────────┬────────────┘        └───────────┬────────────┘        └──────────┬───────────┘
          │ /buyer/*, /payments/*           │ /merchant/*, /audit-logs        │ /api/agent-commerce/*
          ▼                                 ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                  FastAPI application (main.py)                           │
│                                                                                           │
│   routers/buyer_agent.py        routers/merchant_agent.py        routers/agent_commerce.py │
│   routers/payments.py           routers/audit.py                 routers/products.py       │
│                                                                                           │
│   services/llm_service.py  (intent extraction: OpenAI or local rule-based fallback)      │
│   services/negotiation_rules.py  ("The Bar" — bounded discount logic)                     │
│   services/razorpay_service.py   (Razorpay order creation)                                │
└──────────────────────────────────────┬────────────────────────────────────────────────────┘
                                        │ SQLAlchemy
                                        ▼
                    ┌────────────────────────────────────────────┐
                    │  MySQL: products, conversations, orders,    │
                    │  audit_logs, merchant_insights,              │
                    │  buyer_intents                               │
                    └────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │  Razorpay (test)    │
                              └───────────────────┘
```

The Buyer Agent and Merchant Agent are independent FastAPI routers sharing the same database — the Buyer Agent writes orders and buyer intent records; the Merchant Agent reads them back to generate insights, the readiness score, and the revenue radar. No component ever talks to Razorpay except `services/razorpay_service.py`, and no component ever applies a discount except `services/negotiation_rules.py`.

## Setup Instructions

### Backend

```bash
# from the repo root
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=razorpay_buildathon

RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx

# Optional — omit to run entirely on the local rule-based fallback
LLM_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

Create the MySQL database, then seed it:

```bash
mysql -u root -p -e "CREATE DATABASE razorpay_buildathon"

python seed_products.py              # StrideFit catalog
python seed_merchant_orders.py        # sample historical orders (for insights)
python create_buyer_intents_table.py  # buyer_intents table
python migrate_add_flagged_for_review.py  # audit_logs.flagged_for_review column
```

Run the API:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Swagger docs: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite will start on `http://localhost:5173` (falls forward to 5174, etc. if the port is busy). CORS in `main.py` already allows both.

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/buyer/chat` | Main conversational shopping endpoint — extracts intent, recommends real catalog products |
| POST | `/buyer/set-name` | Set the buyer's display name for a session |
| GET | `/buyer/chat-history/{session_id}` | Read-only chat history for persisting a session across refreshes |
| POST | `/payments/create-order` | Create a pending Razorpay order for a product (bounded discount applied) |
| POST | `/payments/confirm-order` | Confirm a pending order after explicit buyer confirmation ("The Bar" gate) |
| GET | `/products` / `/products/{id}` | Public catalog listing |
| GET | `/merchant/dashboard` | Merchant KPIs — revenue, orders, AI-assisted revenue, active insights |
| GET | `/merchant/insights` | Growth insights (cross-sell, revenue trend, top product, discount, category) |
| PATCH | `/merchant/insights/{id}/review` | Toggle an insight between `active` and `under_review` |
| GET | `/merchant/buyer-intents` | Raw buyer intent records (Buyer Intent Intelligence) |
| GET | `/merchant/lost-revenue-radar` | Unmet-demand / price-sensitive revenue opportunities |
| GET | `/merchant/commerce-readiness` | 0–100 AI Commerce Readiness Score with per-component breakdown |
| GET | `/audit-logs` | Audit trail of every money-related decision |
| PATCH | `/audit-logs/{id}/flag` | Flag an audit log entry for review |
| GET | `/api/agent-commerce/catalog` | Machine-readable catalog + transaction capabilities for external AI agents |
| GET | `/health` | Liveness check |

## Screenshots

<img width="1437" height="575" alt="image" src="https://github.com/user-attachments/assets/36ccbf20-cc2a-48c5-9df6-d52298aad6aa" />

<img width="1897" height="888" alt="image" src="https://github.com/user-attachments/assets/a35930d0-50e3-4ab2-9fbe-5d55ed09c65d" />

<img width="1893" height="892" alt="image" src="https://github.com/user-attachments/assets/97888086-8bf9-44a7-b519-0f707cba6a3c" />

<img width="1903" height="897" alt="image" src="https://github.com/user-attachments/assets/de427386-44f7-48d4-a7f3-ba7f1412e70e" />

<img width="1903" height="890" alt="image" src="https://github.com/user-attachments/assets/7f42d256-a17c-4d26-9b89-1b969b6f3a64" />

<img width="1903" height="887" alt="image" src="https://github.com/user-attachments/assets/01d27b1d-e1fe-4634-b4ef-78b1f4ed48e5" />

## Team / Author

**Mumuksh Mohan Agrawal**

## License

MIT
