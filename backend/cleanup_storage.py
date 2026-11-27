"""Retry queued private storage cleanup. Run only on the intended environment."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.storage import StorageClient
from app.db.session import create_db_engine
from app.models.product_image import ProductImage
from app.models.product_image_analysis import ProductImageAnalysis
from app.models.storage_cleanup import StorageCleanupTask
from app.services.storage_cleanup import cleanup_storage_task


def main():
    settings = Settings()
    engine = create_db_engine(settings)
    try:
        storage = StorageClient(settings)
        with Session(engine) as db:
            ids = list(
                db.scalars(
                    select(StorageCleanupTask.id)
                    .where(
                        ~select(ProductImage.id)
                        .where(
                            ProductImage.storage_key == StorageCleanupTask.storage_key
                        )
                        .exists(),
                        ~select(ProductImageAnalysis.id)
                        .where(
                            ProductImageAnalysis.snapshot_storage_key
                            == StorageCleanupTask.storage_key
                        )
                        .exists(),
                    )
                    .order_by(StorageCleanupTask.id)
                    .limit(100)
                )
            )
            for task_id in ids:
                cleanup_storage_task(db, task_id, storage)
            print(
                f"Checked {len(ids)} cleanup tasks; referenced objects remain retained."
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
