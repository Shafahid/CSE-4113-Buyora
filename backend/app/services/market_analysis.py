"""Provider-independent market analysis contracts and future worker hook.

Interpretations require human review; schema validation cannot prove factual accuracy.
No provider or worker is configured by this module.
"""

from datetime import date
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProductSnapshot(BaseModel):
    id: int
    name: str
    category: str
    price: Decimal
    currency: str
    description: str | None
    features: list[str]


class EvidenceSnapshot(BaseModel):
    id: int
    product_id: int | None
    competitor_name: str
    product_name: str
    competitor_description: str | None
    category: str | None
    price: Decimal | None
    currency: str | None
    offer: str | None
    platform: str | None
    observed_at: date
    notes: str | None


class MarketInput(BaseModel):
    product: ProductSnapshot
    competitors: list[EvidenceSnapshot] = Field(min_length=1, max_length=20)
    language: Literal["en", "bn"]


class MarketResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # These fields are AI interpretations, not verified facts.
    feature_comparison: str = Field(min_length=1, max_length=3000)
    offer_comparison: str = Field(min_length=1, max_length=3000)
    competitive_strengths: list[str] = Field(max_length=20)
    competitive_weaknesses: list[str] = Field(max_length=20)
    marketing_recommendations: list[str] = Field(max_length=20)
    limitations: list[str] = Field(min_length=1, max_length=20)


class MarketAnalyzer(Protocol):
    def analyze(self, data: MarketInput) -> MarketResult:
        """Return interpretations for review, based on provided observations."""
        ...


def price_observations(data: MarketInput):
    """Only compare prices sharing the product currency; no conversions."""
    return [
        {
            "evidence_id": c.id,
            "price": str(c.price) if c.price is not None else None,
            "currency": c.currency,
            "observed_at": c.observed_at.isoformat(),
            "comparison": (
                "lower"
                if c.price < data.product.price
                else "higher"
                if c.price > data.product.price
                else "equal"
            )
            if c.price is not None and c.currency == data.product.currency
            else "not_comparable",
        }
        for c in data.competitors
    ]


def process_market_analysis(
    session_factory, analysis_id: int, analyzer: MarketAnalyzer, verify_grounding
):
    """Worker integration hook. Grounding verifier must reject unsupported claims.

    Lease recovery, reliable scheduling, quotas and a real verifier are required
    before enabling request acceptance. Never invoke from an HTTP request.
    """
    from datetime import UTC, datetime

    from sqlalchemy import null, select, update

    from app.models.market_analysis import MarketAnalysis

    with session_factory() as db:
        claimed = db.execute(
            update(MarketAnalysis)
            .where(MarketAnalysis.id == analysis_id, MarketAnalysis.status == "pending")
            .values(status="processing", updated_at=datetime.now(UTC))
        ).rowcount
        db.commit()
        if not claimed:
            return False
    try:
        with session_factory() as db:
            snapshot = db.scalar(
                select(MarketAnalysis.input_snapshot).where(
                    MarketAnalysis.id == analysis_id
                )
            )
        inputs = MarketInput.model_validate(snapshot)
        output = MarketResult.model_validate(analyzer.analyze(inputs))
        if not verify_grounding(inputs, output):
            raise ValueError("Output did not pass grounding review")
        values = {
            "status": "completed",
            "analysis_result": output.model_dump(mode="json"),
            "error_message": None,
        }
    except Exception:
        values = {
            "status": "failed",
            "analysis_result": null(),
            "error_message": "Market analysis could not be completed.",
        }
    now = datetime.now(UTC)
    with session_factory() as db:
        db.execute(
            update(MarketAnalysis)
            .where(
                MarketAnalysis.id == analysis_id, MarketAnalysis.status == "processing"
            )
            .values(**values, completed_at=now, updated_at=now)
        )
        db.commit()
    return True
