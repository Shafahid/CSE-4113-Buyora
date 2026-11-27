"""Test double for the future verified transactional dispatch integration."""

from app.services.processing_admission import DurableProcessingAdmission


class FakeProcessingAdmission(DurableProcessingAdmission):
    def __init__(self, *, ready=True, fail_enqueue=False):
        self.ready = ready
        self.fail_enqueue = fail_enqueue
        self.accepted = []

    def verify_ready(self, db, kind):
        if not self.ready:
            raise RuntimeError("worker unavailable")

    def enqueue(self, db, kind, resource_id):
        if self.fail_enqueue:
            raise RuntimeError("queue unavailable")
        self.accepted.append((kind, resource_id))
