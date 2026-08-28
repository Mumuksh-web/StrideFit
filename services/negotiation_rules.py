
from decimal import Decimal, ROUND_HALF_UP


MAX_DISCOUNT_PERCENT = 10


def evaluate_discount(hesitation_signal: bool, product_price: Decimal) -> Decimal:
	"""Return a bounded discount amount; no LLM output is used for this decision."""
	if not hesitation_signal or product_price <= 0:
		return Decimal("0.00")

	discount = product_price * Decimal(MAX_DISCOUNT_PERCENT) / Decimal("100")
	return discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

