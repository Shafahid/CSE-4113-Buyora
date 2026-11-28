"""Resolve optional completed analyses once; reports never join mutable records."""

from fastapi import HTTPException
from sqlalchemy import select

from app.api.routes.products import image_revision
from app.models import MarketAnalysis, ProductImageAnalysis
from app.schemas.phase2 import AnalysisAttachment, OptionalAnalyses
from app.services.image_analysis import ImageAnalysisResult
from app.services.market_analysis import MarketInput, MarketResult


def snapshot_analyses(db, seller_id, product_id, image_ids, market_ids):
    result = OptionalAnalyses()
    for ids, model, field in (
        (image_ids, ProductImageAnalysis, "image_insights"),
        (market_ids, MarketAnalysis, "market_comparisons"),
    ):
        if not ids:
            continue
        rows = db.scalars(
            select(model).where(
                model.id.in_(ids),
                model.seller_id == seller_id,
                model.product_id == product_id,
                model.status == "completed",
            )
        ).all()
        by_id = {row.id: row for row in rows}
        if len(by_id) != len(ids):
            raise HTTPException(404, "Completed analysis not found for this product")
        for analysis_id in ids:
            row = by_id[analysis_id]
            if row.completed_at is None:
                raise HTTPException(409, "Analysis has no completion timestamp")
            if model is ProductImageAnalysis:
                entry = AnalysisAttachment(
                    id=row.id,
                    completed_at=row.completed_at,
                    result=ImageAnalysisResult.model_validate(
                        row.analysis_result
                    ).model_dump(mode="json"),
                    image_revision=image_revision(row.snapshot_storage_key)
                    if row.snapshot_storage_key
                    else None,
                )
            else:
                entry = AnalysisAttachment(
                    id=row.id,
                    completed_at=row.completed_at,
                    result=MarketResult.model_validate(row.analysis_result).model_dump(
                        mode="json"
                    ),
                    input_snapshot=MarketInput.model_validate(
                        row.input_snapshot
                    ).model_dump(mode="json"),
                )
            getattr(result, field).append(entry)
    return result.model_dump(mode="json")
