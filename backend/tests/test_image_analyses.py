from sqlalchemy.orm import sessionmaker
from test_product_images import ORIGIN, image_bytes, login, make_product
from test_product_images import setup as image_setup

from app.services.image_analysis import ImageAnalysisResult, process_image_analysis

setup = image_setup


def example():
    finding = {"assessment": "good", "feedback": "Clearly visible."}
    return {
        key: finding
        for key in (
            "clarity",
            "lighting",
            "composition",
            "background",
            "text_readability",
            "product_consistency",
        )
    } | {"suggestions": ["Use natural light."]}


class Analyzer:
    def analyze(self, data):
        assert data.image_url.startswith("https://storage.example/signed/")
        return example()


def test_request_completion_isolation_and_pagination(setup):
    client, engine, storage = setup
    login(client, "one@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("test.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    path = f"/products/{product}/images/{image}/analyses"
    first = client.post(path, json={}, headers=ORIGIN)
    assert first.status_code == 202
    analysis = first.json()
    assert analysis["status"] == "pending" and analysis["processing_available"]
    assert analysis["analysis_result"] is None
    assert client.get(f"{path}/{analysis['id']}").json()["status"] == "pending"
    second = client.post(path, json={"language": "bn"}, headers=ORIGIN).json()
    result = client.get(path, params={"limit": 1}).json()
    assert result["total"] == 2 and result["items"][0]["id"] == second["id"]
    assert process_image_analysis(
        sessionmaker(bind=engine, expire_on_commit=False),
        analysis["id"],
        Analyzer(),
        storage,
    )
    assert not process_image_analysis(
        sessionmaker(bind=engine), analysis["id"], Analyzer(), storage
    )
    done = client.get(f"{path}/{analysis['id']}").json()
    assert (
        done["status"] == "completed"
        and done["analysis_result"]["clarity"]["assessment"] == "good"
    )
    assert "storage_key" not in str(done)
    login(client, "two@example.com")
    assert client.get(path).status_code == 404
    assert client.get(f"{path}/{analysis['id']}").status_code == 404
    assert client.post(path, json={}, headers=ORIGIN).status_code == 404


def test_failed_service_and_invalid_output(setup):
    client, engine, storage = setup
    login(client, "one@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("test.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    path = f"/products/{product}/images/{image}/analyses"
    result = client.post(path, json={}, headers=ORIGIN).json()

    class BadAnalyzer:
        def analyze(self, data):
            return {"secret": "bad output"}

    process_image_analysis(
        sessionmaker(bind=engine), result["id"], BadAnalyzer(), storage
    )
    failed = client.get(f"{path}/{result['id']}").json()
    assert failed["status"] == "failed" and failed["analysis_result"] is None
    assert "secret" not in str(failed)
    assert failed["error_message"] == "Image analysis could not be completed."


def test_missing_image_and_unconfigured_service(setup):
    client, _, _ = setup
    assert client.get("/products/1/images/1/analyses").status_code == 401
    login(client, "one@example.com")
    product = make_product(client)
    assert (
        client.post(
            f"/products/{product}/images/999/analyses", json={}, headers=ORIGIN
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/products/{product}/images/999/analyses",
            json={},
            headers={"Origin": "https://bad.example"},
        ).status_code
        == 403
    )
    assert ImageAnalysisResult.model_validate(example()).clarity.assessment == "good"


def test_storage_failure_and_invalid_image_relationship(setup):
    client, engine, storage = setup
    login(client, "seller@example.com")
    product = make_product(client)
    other = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("test.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    assert (
        client.post(
            f"/products/{other}/images/{image}/analyses", json={}, headers=ORIGIN
        ).status_code
        == 404
    )
    path = f"/products/{product}/images/{image}/analyses"
    job = client.post(path, json={}, headers=ORIGIN).json()

    def fail(_):
        raise RuntimeError("private storage details")

    storage.signed_url = fail
    process_image_analysis(sessionmaker(bind=engine), job["id"], Analyzer(), storage)
    result = client.get(f"{path}/{job['id']}").json()
    assert result["status"] == "failed"
    assert "private storage details" not in str(result)
    assert (
        client.delete(f"/products/{product}/images/{image}", headers=ORIGIN).status_code
        == 204
    )
    assert client.get(path).status_code == 200
    assert client.get(path).json()["items"][0]["is_current_image"] is False
    assert client.post(path, json={}, headers=ORIGIN).status_code == 404


def test_deleted_product_cannot_be_analyzed(setup):
    client, _, _ = setup
    login(client, "seller@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("test.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    assert client.delete(f"/products/{product}", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            f"/products/{product}/images/{image}/analyses", json={}, headers=ORIGIN
        ).status_code
        == 404
    )


def test_replacement_and_deletion_preserve_analysis_image(setup):
    client, engine, storage = setup
    login(client, "seller@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("test.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    path = f"/products/{product}/images/{image}/analyses"
    job = client.post(path, json={}, headers=ORIGIN).json()
    old_key = next(iter(storage.objects))
    assert job["is_current_image"] is True
    replacement = client.put(
        f"/products/{product}/images/{image}",
        files={"file": ("new.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    )
    assert replacement.status_code == 200
    assert replacement.json()["image_revision"] != job["image_revision"]
    assert old_key in storage.objects
    old = client.get(f"{path}/{job['id']}").json()
    assert old["is_current_image"] is False
    assert old["image_revision"] == job["image_revision"]

    class InspectAnalyzer:
        def analyze(self, data):
            assert data.image_url.endswith(old_key)
            return example()

    assert process_image_analysis(
        sessionmaker(bind=engine), job["id"], InspectAnalyzer(), storage
    )
    assert client.get(f"{path}/{job['id']}").json()["status"] == "completed"
    assert (
        client.delete(f"/products/{product}/images/{image}", headers=ORIGIN).status_code
        == 204
    )
    assert old_key in storage.objects
    assert client.get(f"{path}/{job['id']}").json()["is_current_image"] is False
    assert client.post(path, json={}, headers=ORIGIN).status_code == 404
    login(client, "other@example.com")
    assert client.get(f"{path}/{job['id']}").status_code == 404


def test_legacy_analysis_without_snapshot_fails_safely(setup):
    from sqlalchemy import update

    from app.models.product_image_analysis import ProductImageAnalysis

    client, engine, storage = setup
    login(client, "seller@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    path = f"/products/{product}/images/{image}/analyses"
    job = client.post(path, json={}, headers=ORIGIN).json()
    with engine.begin() as conn:
        conn.execute(
            update(ProductImageAnalysis)
            .where(ProductImageAnalysis.id == job["id"])
            .values(snapshot_storage_key=None)
        )
    process_image_analysis(sessionmaker(bind=engine), job["id"], Analyzer(), storage)
    result = client.get(f"{path}/{job['id']}").json()
    assert result["status"] == "failed" and result["image_revision"] is None
    assert result["is_current_image"] is None


def test_unavailable_image_service_creates_no_record_and_history_is_readable(setup):
    from sqlalchemy import func, select

    from app.models.product_image_analysis import ProductImageAnalysis
    from app.services.processing_admission import get_processing_admission

    client, engine, storage = setup
    login(client, "seller@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    path = f"/products/{product}/images/{image}/analyses"
    existing = client.post(path, json={}, headers=ORIGIN).json()
    process_image_analysis(
        sessionmaker(bind=engine), existing["id"], Analyzer(), storage
    )
    client.app.dependency_overrides.pop(get_processing_admission)
    client.app.state.image_processing_available = True
    result = client.post(path, json={}, headers=ORIGIN)
    assert result.status_code == 503
    assert result.json()["detail"] == "Image analysis service is not configured"
    # A callable alone cannot serve as a durable processing admission.
    client.app.dependency_overrides[get_processing_admission] = lambda: lambda: None
    assert client.post(path, json={}, headers=ORIGIN).status_code == 503
    client.app.dependency_overrides.pop(get_processing_admission)
    assert client.get(f"{path}/{existing['id']}").json()["status"] == "completed"
    with engine.connect() as conn:
        assert (
            conn.execute(
                select(func.count()).select_from(ProductImageAnalysis)
            ).scalar_one()
            == 1
        )


def test_image_dispatch_failure_rolls_back_request(setup):
    from processing_fakes import FakeProcessingAdmission
    from sqlalchemy import func, select

    from app.models.product_image_analysis import ProductImageAnalysis
    from app.services.processing_admission import get_processing_admission

    client, engine, _ = setup
    login(client, "seller@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    path = f"/products/{product}/images/{image}/analyses"
    for admission in (
        FakeProcessingAdmission(ready=False),
        FakeProcessingAdmission(fail_enqueue=True),
    ):
        client.app.dependency_overrides[get_processing_admission] = lambda: admission  # noqa: B023
        assert client.post(path, json={}, headers=ORIGIN).status_code == 503
    with engine.connect() as conn:
        assert (
            conn.execute(
                select(func.count()).select_from(ProductImageAnalysis)
            ).scalar_one()
            == 0
        )


def test_configured_image_admission_enqueues_and_processes(setup):
    from processing_fakes import FakeProcessingAdmission

    from app.services.processing_admission import get_processing_admission

    client, engine, storage = setup
    admission = FakeProcessingAdmission()
    client.app.dependency_overrides[get_processing_admission] = lambda: admission
    login(client, "seller@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    path = f"/products/{product}/images/{image}/analyses"
    created = client.post(path, json={}, headers=ORIGIN)
    assert created.status_code == 202
    assert created.json()["processing_available"] is True
    analysis_id = created.json()["id"]
    assert admission.accepted == [("image_analysis", analysis_id)]
    assert process_image_analysis(
        sessionmaker(bind=engine), analysis_id, Analyzer(), storage
    )
    retrieved = client.get(f"{path}/{analysis_id}").json()
    assert retrieved["status"] == "completed"
    assert retrieved["processing_available"] is True
