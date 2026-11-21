import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.db.session import DbSession
from app.models.auth import AuthSession, User, UserProfile

router = APIRouter(tags=["authentication"])
hasher = PasswordHasher()
dummy_hash = hasher.hash("not-a-real-user-password")


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class Registration(Credentials):
    password: str = Field(min_length=8, max_length=1024)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class PublicUser(BaseModel):
    id: int
    email: str
    display_name: str


def public_user(user: User) -> PublicUser:
    return PublicUser(
        id=user.id, email=user.email, display_name=user.profile.display_name
    )


def check_origin(request: Request):
    # Browser requests must explicitly identify an allowed origin. Non-browser clients
    # must supply one too, preventing simple cross-origin form requests.
    origin = request.headers.get("origin")
    # Swagger UI is served by the API itself. Permit its exact local origin
    # without broadening the frontend CORS allowlist.
    local_docs_origins = {"http://localhost:8000", "http://127.0.0.1:8000"}
    is_local_same_origin = origin in local_docs_origins and origin == str(
        request.base_url
    ).rstrip("/")
    if (
        origin not in request.app.state.settings.cors_origins
        and not is_local_same_origin
    ):
        raise HTTPException(status_code=403, detail="Invalid origin")


def digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_for(request: Request, db: DbSession):
    token = request.cookies.get(request.app.state.settings.session_cookie_name)
    if not token or len(token) > 256:
        return None
    return db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == digest(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        )
    )


@router.post(
    "/auth/register",
    status_code=201,
    response_model=PublicUser,
    dependencies=[Depends(check_origin)],
)
def register(data: Registration, db: DbSession):
    user = User(email=str(data.email).lower(), password_hash=hasher.hash(data.password))
    user.profile = UserProfile(display_name=data.display_name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Only the email unique constraint represents a duplicate registration.
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint in {"uq_users_email_lower", "users_email_unique"} or (
            db.bind.dialect.name == "sqlite" and "uq_users_email_lower" in str(exc.orig)
        ):
            raise HTTPException(
                status_code=409, detail="Email already registered"
            ) from None
        raise
    db.refresh(user)
    return public_user(user)


@router.post(
    "/auth/login", response_model=PublicUser, dependencies=[Depends(check_origin)]
)
def login(data: Credentials, request: Request, response: Response, db: DbSession):
    user = db.scalar(
        select(User)
        .options(selectinload(User.profile))
        .where(func.lower(User.email) == str(data.email).lower())
    )
    try:
        verified = hasher.verify(
            user.password_hash if user else dummy_hash, data.password
        )
    except (VerificationError, InvalidHashError):
        verified = False
    if user is None or not verified:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    settings = request.app.state.settings
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=digest(token),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=settings.session_lifetime_seconds),
        )
    )
    db.commit()
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_lifetime_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    return public_user(user)


@router.get("/me", response_model=PublicUser)
def me(request: Request, db: DbSession):
    session = session_for(request, db)
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.scalar(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == session.user_id)
    )
    if user is None or user.profile is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return public_user(user)


@router.post("/auth/logout", status_code=204, dependencies=[Depends(check_origin)])
def logout(request: Request, db: DbSession):
    session = session_for(request, db)
    if session is not None:
        session.revoked_at = datetime.now(UTC)
        db.commit()
    settings = request.app.state.settings
    response = Response(status_code=204)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    return response
