"""API Gateway — JWT auth, RBAC, rate limiting, reverse proxy."""

from __future__ import annotations

import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError

from app.auth import (
    authenticate_user,
    check_role_permission,
    create_access_token,
    decode_access_token,
)
from app.rate_limit import RateLimiter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INGEST_URL = os.getenv("INGEST_URL", "http://localhost:8001")
DETECTION_URL = os.getenv("DETECTION_URL", "http://localhost:8002")

app = FastAPI(title="SIEM API Gateway", version="0.1.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# Rate-limit middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def require_role(*allowed_roles: str):
    """Return a dependency that checks the user has one of *allowed_roles*."""

    async def _check(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api-gateway"}


# ---------------------------------------------------------------------------
# Proxy helpers
# ---------------------------------------------------------------------------


async def _proxy(
    method: str,
    upstream_url: str,
    path: str,
    request: Request,
    current_user: dict,
):
    """Forward a request to an upstream service and return its response."""
    if not check_role_permission(current_user.get("role", ""), method):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not permit this action",
        )

    url = f"{upstream_url}{path}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "authorization")
    }
    headers["X-User"] = current_user.get("sub", "")
    headers["X-Role"] = current_user.get("role", "")

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream_resp = await client.request(
                method,
                url,
                headers=headers,
                content=body,
                params=request.query_params,
            )
    except httpx.RequestError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": f"Upstream service unavailable: {exc}"},
        )

    return JSONResponse(
        status_code=upstream_resp.status_code,
        content=upstream_resp.json() if upstream_resp.content else None,
    )


# ---------------------------------------------------------------------------
# Ingest-service proxy
# ---------------------------------------------------------------------------


@app.api_route(
    "/api/ingest/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_ingest(
    path: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return await _proxy(request.method, INGEST_URL, f"/{path}", request, current_user)


# ---------------------------------------------------------------------------
# Detection-service proxy
# ---------------------------------------------------------------------------


@app.api_route(
    "/api/detection/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_detection(
    path: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return await _proxy(
        request.method, DETECTION_URL, f"/{path}", request, current_user
    )
