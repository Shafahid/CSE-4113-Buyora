from urllib.parse import quote, urlsplit

import httpx
from fastapi import HTTPException, Request

from app.core.config import Settings


class StorageError(Exception):
    pass


class StorageClient:
    def __init__(self, settings: Settings):
        if (
            not settings.supabase_url
            or not settings.supabase_secret_key
            or not settings.supabase_storage_bucket
        ):
            raise HTTPException(status_code=503, detail="Storage is not configured")
        url = urlsplit(settings.supabase_url)
        if (
            url.scheme not in ("https", "http")
            or not url.netloc
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
        ):
            raise HTTPException(
                status_code=503, detail="Storage configuration is invalid"
            )
        if url.scheme != "https" and url.hostname not in (
            "localhost",
            "127.0.0.1",
            "::1",
        ):
            raise HTTPException(
                status_code=503, detail="Storage configuration is invalid"
            )
        self.base = settings.supabase_url.rstrip("/") + "/storage/v1"
        self.bucket = quote(settings.supabase_storage_bucket, safe="")
        self.headers = {"apikey": settings.supabase_secret_key.get_secret_value()}

    def call(self, method: str, path: str, **kwargs):
        try:
            with httpx.Client(timeout=15.0, follow_redirects=False) as client:
                response = client.request(
                    method, self.base + path, headers=self.headers, **kwargs
                )
                response.raise_for_status()
                return response
        except httpx.HTTPError:
            raise StorageError("Storage operation failed") from None

    def upload(self, key: str, data: bytes, content_type: str):
        try:
            with httpx.Client(timeout=15.0, follow_redirects=False) as client:
                response = client.post(
                    self.base + f"/object/{self.bucket}/{quote(key, safe='/')}",
                    headers={
                        **self.headers,
                        "Content-Type": content_type,
                        "x-upsert": "false",
                    },
                    content=data,
                )
                response.raise_for_status()
        except httpx.HTTPError:
            raise StorageError("Storage operation failed") from None

    def remove(self, key: str):
        self.call("DELETE", f"/object/{self.bucket}", json={"prefixes": [key]})

    def signed_url(self, key: str):
        response = self.call(
            "POST",
            f"/object/sign/{self.bucket}/{quote(key, safe='/')}",
            json={"expiresIn": 300},
        )
        try:
            path = response.json()["signedURL"]
            if not isinstance(path, str) or not path.startswith("/object/sign/"):
                raise ValueError()
            return self.base + path
        except (KeyError, ValueError, TypeError):
            raise StorageError("Invalid storage response") from None


def get_storage(request: Request) -> StorageClient:
    return StorageClient(request.app.state.settings)
