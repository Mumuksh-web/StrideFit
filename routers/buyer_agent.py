import re
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database import get_db
from models import AuditLog, BuyerIntentRecord, Conversation, Order, Product
from services.llm_service import OUT_OF_SCOPE_TERM_LABELS, BuyerIntent, extract_buyer_intent

router = APIRouter()

AVAILABLE_CATEGORIES = ("footwear", "sneakers", "sports socks", "sports accessories")
AVAILABLE_CATEGORIES_MESSAGE = "footwear (running shoes), sneakers/casual shoes, sports socks, aur sports accessories (laces/insoles)"
FOOTWEAR_PRODUCT_CATEGORIES = ("running shoes", "sneakers")
SUPPORTED_CATEGORY_ALIASES = AVAILABLE_CATEGORIES + ("running shoes",)
MAX_HISTORY_MESSAGES = 6

OUT_OF_SCOPE_TEMPLATES_WITH_TERM = [
	"Main sirf StrideFit ke {categories} mein help kar sakta hoon — {term} abhi catalog mein nahi hai.",
	"Us request ke liye main help nahi kar sakta; StrideFit ke paas {term} nahi hai, sirf {categories}.",
	"{term_title} StrideFit ke catalog mein nahi hai. Main {categories} mein zaroor help kar sakta hoon.",
]
OUT_OF_SCOPE_TEMPLATES_GENERIC = [
	"Main sirf StrideFit ke {categories} mein help kar sakta hoon — ye request uske bahar lag rahi hai.",
	"Ye StrideFit ke catalog se bahar hai. Main {categories} mein aapki help kar sakta hoon.",
	"Is par main help nahi kar paunga; mera scope sirf {categories} tak hai.",
]

INFORMATIONAL_QUESTION_PATTERNS = (
	"brand", "brands", "what all", "what do you have", "what do you sell",
	"what options", "what's available", "what categories",
	"kaunse options", "kaunsa options", "kya kya hai", "kya milta hai",
	"options available", "kya available hai", "kya hai aapke paas",
)

NAME_STOPWORDS = {
	"socks", "sock", "shoes", "shoe", "sneaker", "sneakers", "running", "footwear",
	"lace", "laces", "insole", "insoles", "accessories", "accessory",
	"cheap", "sasta", "sasti", "discount", "affordable", "budget",
	"buy", "purchase", "order", "kharido", "checkout", "under", "price",
	"brands", "options", "chahiye", "hai", "haan", "nahi", "kya", "batao",
}
NAME_PREFIXES = ("my name is ", "mera naam ", "naam hai ", "i am ", "i'm ", "call me ")


class ChatRequest(BaseModel):
	session_id: str = Field(min_length=1, max_length=100)
	message: str = Field(min_length=1, max_length=2000)
	buyer_id: str = "guest"


class ProductRecommendation(BaseModel):
	id: int
	name: str
	category: str | None
	price: Decimal
	description: str | None
	reasoning: str
	discount_percent: int = 0
	discount_amount: Decimal = Decimal("0.00")
	final_amount: Decimal
	checkout_hint: str


class ChatResponse(BaseModel):
	session_id: str
	extracted: BuyerIntent
	message: str
	recommendations: list[ProductRecommendation]
	needs_name: bool = False


class SetNameRequest(BaseModel):
	session_id: str = Field(min_length=1, max_length=100)
	name: str = Field(min_length=1, max_length=100)


class SetNameResponse(BaseModel):
	session_id: str
	name: str
	message: str


def _reason(product: Product, intent: BuyerIntent) -> str:
	if intent.budget is not None and float(product.price) <= intent.budget:
		return f"₹{product.price} budget ke andar hai aur {intent.category} category se match karta hai."
	if intent.budget is not None:
		over_budget = float(product.price) - intent.budget
		return f"Yeh aapke ₹{intent.budget:g} budget se ₹{over_budget:g} zyada hai; {intent.category} mein yeh ek available alternative hai."
	return f"{intent.category} category ka available catalog match: {product.description}"


def _find_mentioned_product(message: str, products: list[Product]) -> Product | None:
	def normalize(value: str) -> str:
		return "".join(character for character in value.lower() if character.isalnum())

	message_normalized = normalize(message)
	for product in products:
		name_without_brand = product.name.lower().replace("stridefit", "", 1)
		name_parts = [
			part
			for part in name_without_brand.replace("-", " ").split()
			if len(part) >= 5 and not part.replace(".", "").isdigit()
		]
		aliases = (product.sku, product.name, name_without_brand, *name_parts)
		if any(normalize(alias) in message_normalized for alias in aliases if alias.strip()):
			return product
	return None


def _record_buyer_intent(
	db: Session,
	*,
	session_id: str,
	buyer_id: str,
	intent: BuyerIntent,
	product_found: bool,
	rejection_reason: str | None,
) -> None:
	db.add(BuyerIntentRecord(
		session_id=session_id,
		buyer_id=buyer_id,
		category=None if intent.category == "unknown" else intent.category,
		requirement=intent.requirement,
		budget_max=Decimal(str(intent.budget)) if intent.budget is not None else None,
		intent=intent.shopping_intent,
		product_found=product_found,
		product_id=intent.product_id,
		rejection_reason=rejection_reason,
		confidence=intent.confidence,
		language=intent.language,
	))


def _build_out_of_scope_reply(message: str, out_of_scope_term: str | None) -> str:
	pick = sum(ord(character) for character in message)
	label = OUT_OF_SCOPE_TERM_LABELS.get(out_of_scope_term, out_of_scope_term) if out_of_scope_term else None
	if label:
		template = OUT_OF_SCOPE_TEMPLATES_WITH_TERM[pick % len(OUT_OF_SCOPE_TEMPLATES_WITH_TERM)]
		return template.format(categories=AVAILABLE_CATEGORIES_MESSAGE, term=label, term_title=label.capitalize())
	template = OUT_OF_SCOPE_TEMPLATES_GENERIC[pick % len(OUT_OF_SCOPE_TEMPLATES_GENERIC)]
	return template.format(categories=AVAILABLE_CATEGORIES_MESSAGE)


def _looks_like_name(message: str) -> str | None:
	cleaned = message.strip()
	if not cleaned or len(cleaned) > 40 or any(character.isdigit() for character in cleaned):
		return None
	lowered = cleaned.lower()
	for prefix in NAME_PREFIXES:
		index = lowered.find(prefix)
		if index != -1:
			cleaned = cleaned[index + len(prefix):].strip()
			break
	words = cleaned.split()
	if not (1 <= len(words) <= 4):
		return None
	if not all(re.match(r"^[A-Za-z''-]+$", word) for word in words):
		return None
	if any(word.lower() in NAME_STOPWORDS for word in words):
		return None
	return " ".join(word.capitalize() for word in words)


def _is_informational_question(message: str, intent: BuyerIntent) -> bool:
	if intent.category != "unknown" or intent.budget is not None:
		return False
	text = message.lower()
	return any(pattern in text for pattern in INFORMATIONAL_QUESTION_PATTERNS)


def _build_catalog_summary_reply(db: Session) -> str:
	categories = list(
		db.scalars(
			select(Product.category)
			.where(Product.merchant_id == "stridefit", Product.is_active.is_(True))
			.distinct()
		).all()
	)
	category_list = ", ".join(sorted(category for category in categories if category))
	if not category_list:
		return "Abhi StrideFit catalog mein categories load nahi ho paayi — kripya thodi der baad try karein."
	return f"StrideFit ke paas abhi ye categories available hain: {category_list}. Kya kisi specific category ya product mein dekhna chahenge?"


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
	conversation = db.scalar(select(Conversation).where(Conversation.session_id == request.session_id))
	is_new_session = conversation is None
	if conversation is None:
		conversation = Conversation(session_id=request.session_id, buyer_id=request.buyer_id.strip() or "guest", context={"messages": []})
		db.add(conversation)
	context = conversation.context or {"messages": []}
	stored_messages = context.setdefault("messages", [])
	history = [{"role": entry.get("role"), "content": entry.get("content")} for entry in stored_messages[-MAX_HISTORY_MESSAGES:]]

	awaiting_name = not is_new_session and conversation.buyer_id == "guest"
	name_just_set = False
	if awaiting_name:
		provided_name = _looks_like_name(request.message)
		if provided_name is None:
			reply = "Pehle apna naam bata do, taaki main tumhe better help kar sakoon — aap kis naam se bulaye jaayen?"
			stored_messages.append({"role": "user", "content": request.message, "timestamp": datetime.utcnow().isoformat()})
			stored_messages.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
			conversation.context = context
			flag_modified(conversation, "context")
			db.commit()
			return ChatResponse(session_id=request.session_id, extracted=BuyerIntent(), message=reply, recommendations=[], needs_name=True)
		conversation.buyer_id = provided_name
		name_just_set = True

	intent = extract_buyer_intent(request.message, history=history)

	now = datetime.utcnow().isoformat()
	stored_messages.append({"role": "user", "content": request.message, "timestamp": now})
	conversation.context = context
	flag_modified(conversation, "context")

	needs_name = conversation.buyer_id == "guest"
	name_prefix = f"Thanks, {conversation.buyer_id}! " if name_just_set else ""

	if _is_informational_question(request.message, intent):
		reply = name_prefix + _build_catalog_summary_reply(db)
		stored_messages.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
		conversation.context = context
		flag_modified(conversation, "context")
		_record_buyer_intent(db, session_id=request.session_id, buyer_id=conversation.buyer_id, intent=intent, product_found=False, rejection_reason="informational_query")
		db.commit()
		return ChatResponse(session_id=request.session_id, extracted=intent, message=reply, recommendations=[], needs_name=needs_name)

	all_catalog_products = list(
		db.scalars(
			select(Product).where(
				Product.merchant_id == "stridefit",
				Product.is_active.is_(True),
				Product.inventory_count > 0,
			)
		).all()
	)
	selected_product = _find_mentioned_product(request.message, all_catalog_products)
	if selected_product is not None:
		intent = intent.model_copy(update={
			"category": selected_product.category,
			"product_id": selected_product.id,
			"product_name": selected_product.name,
		})

	if intent.category not in SUPPORTED_CATEGORY_ALIASES:
		reply = name_prefix + _build_out_of_scope_reply(request.message, intent.out_of_scope_term)
		stored_messages.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
		conversation.context = context
		flag_modified(conversation, "context")
		_record_buyer_intent(db, session_id=request.session_id, buyer_id=conversation.buyer_id, intent=intent, product_found=False, rejection_reason="out_of_scope")
		db.commit()
		return ChatResponse(session_id=request.session_id, extracted=intent, message=reply, recommendations=[], needs_name=needs_name)

	filters = [Product.merchant_id == "stridefit", Product.is_active.is_(True), Product.inventory_count > 0]
	if intent.category == "footwear":
		filters.append(Product.category.in_(FOOTWEAR_PRODUCT_CATEGORIES))
	else:
		filters.append(Product.category == intent.category)
	category_products = list(db.scalars(select(Product).where(*filters).order_by(Product.price)).all())
	if selected_product is not None:
		category_products = [selected_product]
	products = category_products
	budget_message = None
	if intent.budget is not None:
		within_budget = list(
			db.scalars(
				select(Product)
				.where(*filters, Product.price <= intent.budget)
				.order_by(Product.price.desc())
			)
			.all()
		)
		if within_budget:
			products = within_budget[:3]
		else:
			products = category_products[:3]
			if category_products:
				cheapest_price = category_products[0].price
				budget_message = f"₹{intent.budget:g} mein StrideFit ke paas {intent.category} available nahi hai. Sabse sasta option ₹{cheapest_price} ka hai — kya aap thoda budget badha sakte hain, ya kisi aur category mein dekhna chahenge?"
	else:
		products = products[:3]

	product_found = bool(products)
	rejection_reason = None if product_found else ("budget" if budget_message else "unavailable")
	_record_buyer_intent(db, session_id=request.session_id, buyer_id=conversation.buyer_id, intent=intent, product_found=product_found, rejection_reason=rejection_reason)

	recommendations = [
		ProductRecommendation(
			id=product.id,
			name=product.name,
			category=product.category,
			price=product.price,
			description=product.description,
			reasoning=_reason(product, intent),
			final_amount=product.price,
			checkout_hint="Checkout ke time special discount available ho sakta hai.",
		)
		for product in products
	]
	if budget_message:
		reply = budget_message
	elif recommendations:
		reply = f"StrideFit catalog mein {len(recommendations)} relevant options mile. Checkout ke time special discount available ho sakta hai."
	else:
		reply = f"Is request ke liye StrideFit catalog mein matching product nahi mila. Available categories: {AVAILABLE_CATEGORIES_MESSAGE}."
	if needs_name:
		reply += " Pehle apna naam bata do, taaki main tumhe better help kar sakoon."
	reply = name_prefix + reply
	stored_messages.append({"role": "assistant", "content": reply, "timestamp": datetime.utcnow().isoformat()})
	conversation.context = context
	flag_modified(conversation, "context")
	db.commit()
	return ChatResponse(session_id=request.session_id, extracted=intent, message=reply, recommendations=recommendations, needs_name=needs_name)


@router.post("/set-name", response_model=SetNameResponse)
def set_name(request: SetNameRequest, db: Session = Depends(get_db)) -> SetNameResponse:
	name = " ".join(request.name.split())
	conversation = db.scalar(select(Conversation).where(Conversation.session_id == request.session_id))
	if conversation is None:
		conversation = Conversation(session_id=request.session_id, buyer_id=name, context={"messages": []})
		db.add(conversation)
	else:
		conversation.buyer_id = name

	db.execute(update(Order).where(Order.buyer_id == request.session_id).values(buyer_id=name))
	db.execute(update(AuditLog).where(AuditLog.actor_id == request.session_id).values(actor_id=name))
	db.commit()
	return SetNameResponse(session_id=request.session_id, name=name, message=f"Thanks, {name}! Ab main aapko better help kar sakta hoon.")


class ChatHistoryMessage(BaseModel):
	role: str
	message: str
	timestamp: str | None = None


class ChatHistoryResponse(BaseModel):
	session_id: str
	messages: list[ChatHistoryMessage]


@router.get("/chat-history/{session_id}", response_model=ChatHistoryResponse)
def get_chat_history(session_id: str, db: Session = Depends(get_db)) -> ChatHistoryResponse:
	conversation = db.scalar(select(Conversation).where(Conversation.session_id == session_id))
	if conversation is None:
		return ChatHistoryResponse(session_id=session_id, messages=[])
	stored_messages = (conversation.context or {}).get("messages", [])
	return ChatHistoryResponse(
		session_id=session_id,
		messages=[
			ChatHistoryMessage(role=entry.get("role", "user"), message=entry.get("content", ""), timestamp=entry.get("timestamp"))
			for entry in stored_messages
		],
	)
