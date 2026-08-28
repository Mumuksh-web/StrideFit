
from decimal import Decimal
from uuid import uuid4

import razorpay

from config import settings


client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def create_order(amount: Decimal, currency: str = "INR") -> dict:
	amount_in_paise = int((amount * 100).quantize(Decimal("1")))
	if amount_in_paise <= 0:
		raise ValueError("Order amount must be greater than zero")

	return client.order.create(
		{
			"amount": amount_in_paise,
			"currency": currency,
			"receipt": f"stridefit_{uuid4().hex}",
			"payment_capture": 1,
		},
		timeout=20,
	)

