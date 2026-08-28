from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Product

router = APIRouter()


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
