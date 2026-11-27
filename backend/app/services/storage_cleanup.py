"""Small, explicitly invoked retry mechanism for obsolete private objects."""

import logging

from sqlalchemy import select

from app.core.storage import StorageError
from app.models.product_image import ProductImage
from app.models.product_image_analysis import ProductImageAnalysis
from app.models.storage_cleanup import StorageCleanupTask

logger = logging.getLogger(__name__)


def cleanup_storage_task(db, task_id, storage):
    task = db.scalar(
        select(StorageCleanupTask)
        .where(StorageCleanupTask.id == task_id)
        .with_for_update()
    )
    if task is None:
        return False
    # Keys are unique and never reused. Analyses keep their original object for
    # as long as their historical record exists, including after image deletion.
    if db.scalar(
        select(ProductImage.id)
        .where(ProductImage.storage_key == task.storage_key)
        .limit(1)
    ) or db.scalar(
        select(ProductImageAnalysis.id)
        .where(ProductImageAnalysis.snapshot_storage_key == task.storage_key)
        .limit(1)
    ):
        db.rollback()
        return False
    # Legacy analyses have no immutable key. Their referenced object cannot be
    # identified reliably, so retain objects for that product until reconciled.
    # Unknown key layouts are guarded against legacy analyses across all products.
    legacy = select(ProductImageAnalysis.id).where(
        ProductImageAnalysis.snapshot_storage_key.is_(None)
    )
    parts = task.storage_key.split("/")
    if len(parts) >= 3 and parts[0] == "products" and parts[1].isdigit():
        legacy = legacy.where(ProductImageAnalysis.product_id == int(parts[1]))
    if db.scalar(legacy.limit(1)):
        db.rollback()
        return False
    try:
        storage.remove(task.storage_key)
    except StorageError:
        task.attempts += 1
        db.commit()
        logger.warning("Storage cleanup task %s failed; retry later", task_id)
        return False
    db.delete(task)
    db.commit()
    return True
