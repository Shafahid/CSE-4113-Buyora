"""Provider-neutral image contract; production dispatch lives in services.ai.jobs."""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.phase2 import AIMetadata, ExecutionBudget


class ImageFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment: Literal["good", "needs_improvement", "not_applicable", "uncertain"]
    feedback: str | None = Field(max_length=2000)
    severity: Literal["none", "minor", "major", "uncertain"] = "uncertain"
    observation: str | None = Field(default=None, max_length=2000)


class ImageAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    clarity: ImageFinding
    lighting: ImageFinding
    composition: ImageFinding
    background: ImageFinding
    text_readability: ImageFinding
    product_consistency: ImageFinding
    suggestions: list[str] = Field(max_length=20)
    metadata: AIMetadata | None = None


class ImageAnalysisInput(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    product_id: int
    image_id: int
    product_details: dict
    image_url: str
    language: Literal["en", "bn"]
    budget: ExecutionBudget = Field(default_factory=ExecutionBudget)


class ImageAnalyzer(Protocol):
    def analyze(self, data: ImageAnalysisInput) -> ImageAnalysisResult:
        """Analyze a private short-lived image URL, without persisting it."""
        ...


def process_image_analysis(
    session_factory, analysis_id: int, analyzer: ImageAnalyzer, storage
):
    """Legacy direct integration hook; never runs in API requests.

    Atomically claim once, then release the transaction before storage/provider calls.
    Production uses services.ai.jobs for leases, recovery and bounded calls.
    """
    from datetime import UTC, datetime

    from sqlalchemy import null, select, update

    from app.models.product import Product
    from app.models.product_image_analysis import ProductImageAnalysis

    now = datetime.now(UTC)
    with session_factory() as db:
        claimed = db.execute(
            update(ProductImageAnalysis)
            .where(
                ProductImageAnalysis.id == analysis_id,
                ProductImageAnalysis.status == "pending",
            )
            .values(status="processing", updated_at=now)
        ).rowcount
        db.commit()
        if not claimed:
            return False
    try:
        with session_factory() as db:
            row = db.execute(
                select(ProductImageAnalysis, Product)
                .join(Product, Product.id == ProductImageAnalysis.product_id)
                .where(
                    ProductImageAnalysis.id == analysis_id,
                    Product.seller_id == ProductImageAnalysis.seller_id,
                    Product.deleted_at.is_(None),
                )
            ).first()
            if row is None:
                raise ValueError("Missing product or image")
            analysis, product = row
            key = analysis.snapshot_storage_key
            if not key:
                raise ValueError("Image revision is unavailable")
            data = {
                "product_id": product.id,
                "image_id": analysis.original_image_id,
                "product_details": {
                    "name": product.name,
                    "category": product.category,
                    "description": product.description,
                    "features": product.features,
                },
                "language": analysis.language,
            }
            from app.services.ai_limits import request_budget

            data["budget"] = request_budget(db, "image_analysis", analysis_id)
        data["image_url"] = storage.signed_url(key)
        output = ImageAnalysisResult.model_validate(
            analyzer.analyze(ImageAnalysisInput(**data))
        )
        values = {
            "status": "completed",
            "analysis_result": output.model_dump(mode="json"),
            "error_message": None,
        }
    except Exception:
        values = {
            "status": "failed",
            "analysis_result": null(),
            "error_message": "Image analysis could not be completed.",
        }
    finished = datetime.now(UTC)
    with session_factory() as db:
        db.execute(
            update(ProductImageAnalysis)
            .where(
                ProductImageAnalysis.id == analysis_id,
                ProductImageAnalysis.status == "processing",
            )
            .values(**values, updated_at=finished, completed_at=finished)
        )
        db.commit()
    return True
