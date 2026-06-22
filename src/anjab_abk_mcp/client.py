"""HTTP client ke anjab-abk-backend dengan Bearer token forwarding (Pola B).

Pola B: token user Authentik disimpan saat OAuth exchange dan diteruskan apa
adanya ke backend pada setiap tool call. Backend memvalidasi token tersebut via
JWKS Authentik (konfigurasi identik dengan MCP server ini).

Untuk mode stdio/API key (tanpa OAuth), fallback ke BACKEND_API_TOKEN dari
config — token statis service account yang diperoleh dari Authentik secara
terpisah.
"""

from __future__ import annotations

import base64
import json
import logging

import httpx

from .auth_provider import get_upstream_token
from .config import settings

logger = logging.getLogger(__name__)


class BackendError(Exception):
    """Error dari anjab-abk-backend (HTTP error atau network error).

    Attributes:
        status_code: HTTP status code bila error berasal dari response backend.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _sub_from_jwt(token: str) -> str | None:
    """Decode payload JWT (tanpa verifikasi) untuk mengambil claim ``sub``.

    JWT sudah diverifikasi oleh FastMCP sebelum tool dipanggil, sehingga
    decode tanpa verifikasi aman di sini.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload.get("sub")
    except Exception:
        return None


def get_bearer_from_ctx(ctx: object | None) -> str | None:
    """Ambil Bearer token Authentik dari konteks FastMCP atau fallback ke config.

    Urutan prioritas:
    1. Token upstream Authentik dari cache (keyed by sub dari FastMCP JWT).
    2. ``BACKEND_API_TOKEN`` dari config (service account / stdio mode).

    Args:
        ctx: FastMCP ``Context`` dari tool call (bisa None di stdio tanpa auth).

    Returns:
        Bearer token string, atau None bila tidak ada token yang tersedia.
    """
    if ctx is not None:
        auth = getattr(ctx, "auth", None)
        if auth is not None:
            raw_token = getattr(auth, "token", None)
            if raw_token:
                sub = _sub_from_jwt(raw_token)
                if sub:
                    upstream = get_upstream_token(sub)
                    if upstream:
                        return upstream
    return settings.backend_api_token


async def backend_request(
    method: str,
    path: str,
    *,
    ctx: object | None = None,
    **kwargs: object,
) -> object:
    """Buat request ke anjab-abk-backend dan kembalikan JSON response.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE, dll.).
        path: Path endpoint, mis. ``/api/v1/sekolah``.
        ctx: FastMCP Context (opsional). Dipakai untuk mengambil Bearer token.
        **kwargs: Argumen tambahan untuk ``httpx.AsyncClient.request``
            (mis. ``json``, ``params``).

    Returns:
        Response JSON sebagai Python object (dict atau list).

    Raises:
        BackendError: Bila backend mengembalikan error atau tidak dapat dijangkau.
    """
    headers: dict[str, str] = {}
    token = get_bearer_from_ctx(ctx)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        logger.warning("Tidak ada Bearer token — request ke backend tanpa auth")

    url = f"{settings.backend_base_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
    except httpx.RequestError as exc:
        raise BackendError(f"Gagal menghubungi backend: {exc}") from exc

    if not response.is_success:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise BackendError(
            f"Backend error {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    return response.json()


async def backend_get(path: str, *, ctx: object | None = None, **params: object) -> object:
    """GET request ke backend. ``params`` diteruskan sebagai query parameters."""
    return await backend_request("GET", path, ctx=ctx, params=params or None)


async def backend_post(
    path: str,
    *,
    ctx: object | None = None,
    body: object = None,
    params: dict[str, object] | None = None,
) -> object:
    """POST request ke backend.

    Args:
        path: Path endpoint.
        ctx: FastMCP Context (opsional) untuk Bearer token.
        body: Dikirim sebagai JSON body (boleh None untuk action tanpa body).
        params: Query parameters opsional (mis. ``paksa``, ``wcp_sesi_id``).
    """
    return await backend_request("POST", path, ctx=ctx, json=body, params=params or None)


async def backend_patch(
    path: str,
    *,
    ctx: object | None = None,
    body: object,
    params: dict[str, object] | None = None,
) -> object:
    """PATCH request ke backend. ``body`` dikirim sebagai JSON."""
    return await backend_request("PATCH", path, ctx=ctx, json=body, params=params or None)


async def backend_delete(path: str, *, ctx: object | None = None) -> object:
    """DELETE request ke backend."""
    return await backend_request("DELETE", path, ctx=ctx)
