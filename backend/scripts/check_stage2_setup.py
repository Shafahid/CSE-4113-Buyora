"""Check optional-AI schema/worker readiness; optional unbilled provider probes."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.db.session import create_db_engine  # noqa: E402
from app.services.ai import gemini  # noqa: E402
from app.services.ai.jobs import MODELS, DatabaseAdmission  # noqa: E402
from app.services.ai.provider import Gateway, configured  # noqa: E402
from app.services.llm import ModelFailure  # noqa: E402
from app.services.simulation_worker import worker_failure_hint  # noqa: E402
from scripts.check_simulation_setup import check_worker_schema  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        action="store_true",
        help="Probe model catalog and token counting only; never generate paid content",
    )
    args = parser.parse_args()
    engine = None
    try:
        settings = Settings()
        engine = create_db_engine(settings)
        ready = check_worker_schema(engine)
        print("Stage 2 schema:", "ready" if ready else "outdated")
        if not ready:
            return 1
        admission = DatabaseAdmission(settings)
        with sessionmaker(bind=engine)() as db:
            for kind in MODELS:
                try:
                    admission.verify_ready(db, kind)
                    print(f"{kind}: healthy matching worker")
                except ModelFailure:
                    print(f"{kind}: unavailable (no fresh capable matching worker)")
        if args.provider:
            gateway = Gateway(settings)
            print("Provider configured:", configured(settings))
            print("Verified image capability:", gateway.supports_vision())
            print("Vision processing ready:", gateway.vision_ready())
            print(
                "Vision budget strategy:",
                "conservative_gemini"
                if gateway.model(vision=True) == gemini.MODEL
                else "native_count",
            )
            print("Paid generation calls: 0")
        return 0
    except Exception as error:
        print(
            f"Stage 2 check failed ({type(error).__name__}). "
            f"{worker_failure_hint(error)}"
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
