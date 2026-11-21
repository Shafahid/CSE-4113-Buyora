import httpx

from app.core.config import Settings
from app.core.storage import StorageClient


def test_storage_requests_and_signed_url(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        if "/object/sign/" in request.url.path:
            return httpx.Response(
                200, json={"signedURL": "/object/sign/private/a.png?token=short"}
            )
        return httpx.Response(200, json={})

    real_client = httpx.Client
    monkeypatch.setattr(
        "app.core.storage.httpx.Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:password@localhost/db",
        supabase_url="https://project.supabase.co",
        supabase_secret_key="test-secret",
        supabase_storage_bucket="private",
    )
    client = StorageClient(settings)
    client.upload("a.png", b"contents", "image/png")
    assert (
        client.signed_url("a.png")
        == "https://project.supabase.co/storage/v1/object/sign/private/a.png?token=short"
    )
    client.remove("a.png")
    assert [request.method for request in requests] == ["POST", "POST", "DELETE"]
    assert requests[0].headers["apikey"] == "test-secret"
    assert requests[0].headers["content-type"] == "image/png"
    assert requests[0].headers["x-upsert"] == "false"
    assert requests[1].read() == b'{"expiresIn":300}'
    assert requests[2].read() == b'{"prefixes":["a.png"]}'
