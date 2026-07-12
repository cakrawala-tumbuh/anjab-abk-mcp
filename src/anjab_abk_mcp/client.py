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
from .m2m import M2MError, get_m2m_access_token, m2m_configured
from .m2m import invalidate as invalidate_m2m

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


def _user_token_from_ctx(ctx: object | None) -> str | None:
    """Ambil token user Authentik dari konteks FastMCP (alur OAuth Pola B)."""
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
    return None


async def resolve_bearer(ctx: object | None) -> str | None:
    """Tentukan Bearer token untuk request ke backend.

    Urutan prioritas:
    1. Token user Authentik dari konteks OAuth (Claude Web / Pola B).
    2. Token M2M headless (mode stdio): MCP login sendiri ke Authentik bila
       ``backend_m2m_*`` dikonfigurasi.
    3. ``BACKEND_API_TOKEN`` statis dari config.

    Args:
        ctx: FastMCP ``Context`` dari tool call (bisa None di stdio tanpa auth).

    Returns:
        Bearer token string, atau None bila tidak ada yang tersedia.
    """
    user_token = _user_token_from_ctx(ctx)
    if user_token:
        return user_token
    if m2m_configured():
        try:
            return await get_m2m_access_token()
        except M2MError as exc:
            logger.warning("Login M2M gagal, fallback ke BACKEND_API_TOKEN: %s", exc)
    return settings.backend_api_token


def get_bearer_from_ctx(ctx: object | None) -> str | None:
    """Versi sinkron: token user OAuth atau ``BACKEND_API_TOKEN`` (tanpa M2M).

    Dipertahankan untuk kompatibilitas; alur utama memakai ``resolve_bearer``.
    """
    return _user_token_from_ctx(ctx) or settings.backend_api_token


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
    url = f"{settings.backend_base_url.rstrip('/')}{path}"
    token = await resolve_bearer(ctx)
    if not token:
        logger.warning("Tidak ada Bearer token — request ke backend tanpa auth")

    async def _send(bearer: str | None) -> httpx.Response:
        headers: dict[str, str] = {}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await client.request(method, url, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            raise BackendError(f"Gagal menghubungi backend: {exc}") from exc

    response = await _send(token)

    # Bila token M2M kedaluwarsa/dicabut, backend balas 401 — refresh sekali lalu ulang.
    if response.status_code == 401 and m2m_configured() and _user_token_from_ctx(ctx) is None:
        invalidate_m2m()
        try:
            token = await get_m2m_access_token()
        except M2MError as exc:
            logger.warning("Refresh token M2M gagal: %s", exc)
        else:
            response = await _send(token)

    # 204/304 tidak membawa body (dan httpx menganggap 304 BUKAN is_success karena
    # di luar rentang 2xx) — tangani dulu sebelum pengecekan error di bawah.
    if response.status_code in (204, 304) or not response.content:
        if not response.is_success and response.status_code != 304:
            raise BackendError(
                f"Backend error {response.status_code}: (tanpa body)",
                status_code=response.status_code,
            )
        return {}

    if not response.is_success:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise BackendError(
            f"Backend error {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    try:
        return response.json()
    except ValueError as exc:
        raise BackendError(
            f"Response backend bukan JSON valid (HTTP {response.status_code})."
        ) from exc


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


async def backend_put(
    path: str,
    *,
    ctx: object | None = None,
    body: object,
    params: dict[str, object] | None = None,
) -> object:
    """PUT request ke backend (simpan draft parsial). ``body`` dikirim sebagai JSON."""
    return await backend_request("PUT", path, ctx=ctx, json=body, params=params or None)


async def backend_delete(
    path: str,
    *,
    ctx: object | None = None,
    params: dict[str, object] | None = None,
) -> object:
    """DELETE request ke backend.

    Args:
        path: Path endpoint.
        ctx: FastMCP Context (opsional) untuk Bearer token.
        params: Query parameters opsional (mis. ``paksa``).
    """
    return await backend_request("DELETE", path, ctx=ctx, params=params or None)
