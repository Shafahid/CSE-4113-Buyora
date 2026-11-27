import hashlib
import io
import logging
import uuid
import warnings
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, update

from app.api.routes.auth import check_origin, get_current_user
from app.core.storage import StorageClient, StorageError, get_storage
from app.db.session import DbSession
from app.models import (
    Product,
    ProductImage,
    StorageCleanupTask,
    User,
)
from app.services.storage_cleanup import cleanup_storage_task

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
def list_products(
    user: CurrentUser, db: DbSession, status: Literal["active", "archived"] = "active"
):
    return list(
        db.scalars(
            select(Product)
            .where(
                Product.seller_id == user.id,
                Product.status == status,
                Product.deleted_at.is_(None),
            )
            .order_by(Product.id)
        )
    )


MAX_IMAGE_BYTES = 5 * 1024 * 1024
FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}
logger = logging.getLogger(__name__)
Storage = Annotated[StorageClient, Depends(get_storage)]


class ImageCreated(BaseModel):
    id: int
    product_id: int
    sort_order: int


class ImageResponse(BaseModel):
    id: int
    sort_order: int
    url: str
    image_revision: str


class ProductDetail(ProductResponse):
    images: list[ImageResponse]


def owned_product(product_id: int, user: User, db: DbSession) -> Product:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.seller_id == user.id,
            Product.deleted_at.is_(None),
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def validate_image(data: bytes):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=list(FORMATS)) as image:
                image_format = image.format
                image.verify()
            with Image.open(io.BytesIO(data), formats=list(FORMATS)) as image:
                image.load()
        if image_format not in FORMATS:
            raise ValueError("Unsupported image format")
        return FORMATS[image_format]
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise HTTPException(
            status_code=422, detail="Invalid or unsupported image"
        ) from None


@router.post(
    "/products/{product_id}/images", status_code=201, response_model=ImageCreated
)
def upload_product_image(
    product_id: int,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, Depends(check_origin)],
    file: Annotated[UploadFile, File()],
    storage: Storage,
):
    product = owned_product(product_id, user, db)
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB")
    extension, content_type = validate_image(data)
    key = f"products/{product.id}/{uuid.uuid4().hex}.{extension}"
    try:
        storage.upload(key, data, content_type)
    except StorageError:
        raise HTTPException(
            status_code=502, detail="Image storage unavailable"
        ) from None
    image = ProductImage(product_id=product.id, storage_key=key)
    commit_attempted = False
    try:
        db.add(image)
        db.flush()
        result = ImageCreated(
            id=image.id, product_id=image.product_id, sort_order=image.sort_order
        )
        commit_attempted = True
        db.commit()
    except Exception:
        rollback_succeeded = False
        try:
            db.rollback()
            rollback_succeeded = True
        except Exception:
            logger.error("Could not roll back image upload transaction")
        if commit_attempted or not rollback_succeeded:
            # A failed commit acknowledgement does not prove the row is absent.
            # Do not queue or remove this object while the outcome is unknown.
            logger.error(
                "Image upload outcome uncertain; reconcile product %s revision %s",
                product_id,
                image_revision(key),
            )
        else:
            # Commit was never attempted and rollback succeeded. Queue cleanup
            # separately, then use the shared reference-checked cleanup service.
            try:
                task = StorageCleanupTask(storage_key=key)
                db.add(task)
                db.flush()
                task_id = task.id
                db.commit()
                cleanup_storage_task(db, task_id, storage)
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    logger.error("Could not roll back image cleanup transaction")
                logger.error(
                    "Could not run image cleanup for product %s revision %s",
                    product_id,
                    image_revision(key),
                )
        raise
    return result


@router.put("/products/{product_id}/images/{image_id}", response_model=ImageResponse)
def replace_product_image(
    product_id: int,
    image_id: int,
    user: CurrentUser,
    db: DbSession,
    response: Response,
    _: Annotated[None, Depends(check_origin)],
    file: Annotated[UploadFile, File()],
    storage: Storage,
):
    product = owned_product(product_id, user, db)
    image = db.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product.id
        )
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    old_key = image.storage_key
    sort_order = image.sort_order
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 5 MB")
    extension, content_type = validate_image(data)
    new_key = f"products/{product.id}/{uuid.uuid4().hex}.{extension}"
    try:
        storage.upload(new_key, data, content_type)
    except StorageError:
        raise HTTPException(
            status_code=502, detail="Image storage unavailable"
        ) from None
    commit_attempted = False
    try:
        # Sign before committing, so a signing error leaves the original active.
        url = storage.signed_url(new_key)
        result = db.execute(
            update(ProductImage)
            .where(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id,
                ProductImage.storage_key == old_key,
            )
            .values(storage_key=new_key)
        )
        if result.rowcount != 1:
            raise HTTPException(
                status_code=409, detail="Image changed; retry replacement"
            )
        task = StorageCleanupTask(storage_key=old_key)
        db.add(task)
        db.flush()
        task_id = task.id
        commit_attempted = True
        db.commit()
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            logger.error("Could not roll back replacement transaction")
        if commit_attempted:
            # A lost commit acknowledgement leaves the database outcome unknown.
            # Deleting new_key could delete the image that actually became active.
            logger.error("Replacement commit outcome unknown; reconcile storage")
        else:
            try:
                storage.remove(new_key)
            except Exception:
                logger.error("Could not remove an orphaned replacement image")
        if isinstance(exc, StorageError):
            raise HTTPException(
                status_code=502, detail="Image storage unavailable"
            ) from None
        raise
    try:
        cleanup_storage_task(db, task_id, storage)
    except Exception:
        db.rollback()
        logger.error("Storage cleanup task %s could not run", task_id)
    response.headers["Cache-Control"] = "private, no-store"
    return ImageResponse(
        id=image_id,
        sort_order=sort_order,
        url=url,
        image_revision=image_revision(new_key),
    )


def image_revision(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@router.get("/products/{product_id}", response_model=ProductDetail)
def get_product(
    product_id: int,
    user: CurrentUser,
    db: DbSession,
    response: Response,
    request: Request,
):
    product = owned_product(product_id, user, db)
    images = list(
        db.scalars(
            select(ProductImage)
            .where(ProductImage.product_id == product.id)
            .order_by(ProductImage.sort_order, ProductImage.id)
        )
    )
    signed_images = []
    if images:
        storage = get_storage(request)
        try:
            signed_images = [
                ImageResponse(
                    id=image.id,
                    sort_order=image.sort_order,
                    url=storage.signed_url(image.storage_key),
                    image_revision=image_revision(image.storage_key),
                )
                for image in images
            ]
        except StorageError:
            raise HTTPException(
                status_code=502, detail="Image storage unavailable"
            ) from None
    response.headers["Cache-Control"] = "private, no-store"
    return ProductDetail(
        **ProductResponse.model_validate(product).model_dump(), images=signed_images
    )


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1)
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False
    )
    description: str | None = None
    features: list[str] | None = None
    warranty: str | None = None
    delivery_info: str | None = None
    return_policy: str | None = None
    status: Literal["active", "archived"] | None = None

    @field_validator("name", "category", mode="before")
    @classmethod
    def trim_required(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self):
        for name in ("name", "category", "price", "features", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    data: ProductUpdate,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, Depends(check_origin)],
):
    product = owned_product(product_id, user, db)
    updates = data.model_dump(exclude_unset=True)
    for name, value in updates.items():
        setattr(product, name, value)
    if updates:
        product.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(product)
    return product


@router.post(
    "/products/{product_id}/duplicate", status_code=201, response_model=ProductResponse
)
def duplicate_product(
    product_id: int,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, Depends(check_origin)],
):
    source = owned_product(product_id, user, db)
    product = Product(
        seller_id=user.id,
        name=source.name,
        category=source.category,
        price=source.price,
        currency=source.currency,
        description=source.description,
        features=list(source.features),
        warranty=source.warranty,
        delivery_info=source.delivery_info,
        return_policy=source.return_policy,
        status="active",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, Depends(check_origin)],
):
    product = owned_product(product_id, user, db)
    product.deleted_at = datetime.now(UTC)
    product.updated_at = product.deleted_at
    db.commit()
    return Response(status_code=204)


@router.delete("/products/{product_id}/images/{image_id}", status_code=204)
def delete_product_image(
    product_id: int,
    image_id: int,
    user: CurrentUser,
    db: DbSession,
    request: Request,
    _: Annotated[None, Depends(check_origin)],
):
    product = owned_product(product_id, user, db)
    image = db.scalar(
        select(ProductImage)
        .where(ProductImage.id == image_id, ProductImage.product_id == product.id)
        .with_for_update()
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    # Serialize with replacement and analysis creation using the image row lock.
    # Record cleanup in the same transaction as the row deletion. No Storage
    # operation is attempted until the database commit succeeds.
    task = db.scalar(
        select(StorageCleanupTask).where(
            StorageCleanupTask.storage_key == image.storage_key
        )
    )
    if task is None:
        task = StorageCleanupTask(storage_key=image.storage_key)
        db.add(task)
        db.flush()
    task_id = task.id
    db.delete(image)
    db.commit()
    try:
        cleanup_storage_task(db, task_id, get_storage(request))
    except Exception:
        db.rollback()
        logger.error("Storage cleanup task %s could not run", task_id)
    return Response(status_code=204)
