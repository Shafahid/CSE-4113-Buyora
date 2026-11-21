from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from app.api.routes.auth import check_origin, get_current_user
from app.db.session import DbSession
from app.models import Product, User

router = APIRouter(tags=["products"])
CurrentUser = Annotated[User, Depends(get_current_user)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Wireless headphones",
                    "category": "Electronics",
                    "price": "1250.00",
                    "description": "Wireless over-ear headphones",
                    "features": ["Bluetooth", "Rechargeable battery"],
                    "warranty": "One year",
                    "delivery_info": "Delivery available",
                    "return_policy": "Returns within seven days",
                }
            ]
        },
    )
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    description: str | None = None
    features: list[str] = Field(default_factory=list)
    warranty: str | None = None
    delivery_info: str | None = None
    return_policy: str | None = None

    @field_validator("name", "category", mode="before")
    @classmethod
    def trim_required(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProductResponse(ProductCreate):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "seller_id": 1,
                    "name": "Wireless headphones",
                    "category": "Electronics",
                    "price": "1250.00",
                    "description": "Wireless over-ear headphones",
                    "features": ["Bluetooth", "Rechargeable battery"],
                    "warranty": "One year",
                    "delivery_info": "Delivery available",
                    "return_policy": "Returns within seven days",
                    "currency": "BDT",
                    "status": "active",
                }
            ]
        },
    )
    id: int
    seller_id: int
    currency: str
    status: str


@router.post(
    "/products",
    status_code=201,
    response_model=ProductResponse,
    responses={
        201: {
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "seller_id": 1,
                        "name": "Wireless headphones",
                        "category": "Electronics",
                        "price": "1250.00",
                        "description": "Wireless over-ear headphones",
                        "features": ["Bluetooth", "Rechargeable battery"],
                        "warranty": "One year",
                        "delivery_info": "Delivery available",
                        "return_policy": "Returns within seven days",
                        "currency": "BDT",
                        "status": "active",
                    }
                }
            }
        }
    },
)
def create_product(
    data: ProductCreate,
    user: CurrentUser,
    db: DbSession,
    _: None = Depends(check_origin),
):
    product = Product(**data.model_dump(), seller_id=user.id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products", response_model=list[ProductResponse])
def list_products(user: CurrentUser, db: DbSession):
    return list(
        db.scalars(
            select(Product)
            .where(
                Product.seller_id == user.id,
                Product.status == "active",
                Product.deleted_at.is_(None),
            )
            .order_by(Product.id)
        )
    )
