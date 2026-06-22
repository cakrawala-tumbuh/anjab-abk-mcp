"""Auth provider pintu depan MCP: Authentik OAuth Pola B + API key statis.

Pola B: backend anjab-abk-backend sudah memakai Authentik sebagai IdP.
MCP memverifikasi token menggunakan JWKS Authentik yang SAMA dengan backend,
lalu meneruskan token user asli ke backend pada setiap tool call.

  AuthentikProvider   — subclass OAuthProxy yang memakai Authentik sebagai IdP
      via OAuth 2.0 Authorization Code + PKCE. Endpoint di-derive dari
      AUTHENTIK_ISSUER_URL. Token diverifikasi via JWKS. Upstream access token
      disimpan dalam cache untuk diteruskan ke backend.

  BearerApiKeyVerifier — TokenVerifier sederhana untuk static Bearer token.
      Dipakai klien non-OAuth (VS Code/CLI).

  get_upstream_token(sub) — ambil token Authentik user dari cache, dipanggil
      oleh client.py saat memanggil backend atas nama user yang sudah login.

WAJIB: ``TokenError`` hanya boleh memakai error_code valid OAuth/MCP:
  ``invalid_request``, ``invalid_client``, ``invalid_grant``,
  ``unauthorized_client``, ``unsupported_grant_type``, ``invalid_scope``.
Kode lain memicu Pydantic ValidationError → token exchange crash.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.oauth_proxy.proxy import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from mcp.server.auth.provider import TokenError

logger = logging.getLogger(__name__)

# Cache upstream Authentik token: {authentik_sub -> access_token}
# Diisi oleh AuthentikProvider._extract_upstream_claims saat OAuth exchange.
_token_cache: dict[str, str] = {}


def get_upstream_token(sub: str) -> str | None:
    """Ambil upstream Authentik access token dari cache berdasarkan Authentik sub.

    Args:
        sub: Claim ``sub`` dari JWT FastMCP (= Authentik sub user).

    Returns:
        Authentik access token bila ada di cache, else None.
    """
    return _token_cache.get(sub)


class AuthentikProvider(OAuthProxy):
    """OAuthProxy Pola B — memakai Authentik sebagai IdP, endpoint di-derive dari issuer URL.

    Semua endpoint Authentik (authorize, token, JWKS, revoke, userinfo) di-derive
    dari ``authentik_issuer_url`` berbentuk
    ``https://auth.example.com/application/o/<slug>/``.

    Args:
        authentik_issuer_url: Issuer URL Authentik, format
            ``https://auth.example.com/application/o/<slug>/``.
        client_id: Client ID dari Authentik OAuth2 Provider MCP.
        client_secret: Client Secret dari Authentik OAuth2 Provider MCP.
        base_url: URL publik MCP server (untuk redirect OAuth).
        allowed_usernames: Daftar ``preferred_username`` yang diizinkan
            (case-insensitive). Kosong/None = semua user yang login diizinkan.
        **kwargs: Diteruskan ke ``OAuthProxy.__init__``.
    """

    def __init__(
        self,
        *,
        authentik_issuer_url: str,
        client_id: str,
        client_secret: str,
        base_url: str,
        allowed_usernames: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        issuer = authentik_issuer_url.rstrip("/")
        # Derive base Authentik URL and slug from issuer URL.
        # issuer = https://auth.example.com/application/o/slug
        parts = issuer.rsplit("/application/o/", 1)
        auth_base = parts[0]  # https://auth.example.com
        slug = parts[1].strip("/") if len(parts) > 1 else ""

        authorize_url = f"{auth_base}/application/o/authorize/"
        token_url = f"{auth_base}/application/o/token/"
        jwks_url = f"{issuer}/jwks/"
        revoke_url = f"{issuer}/end-session/"
        self._userinfo_url = f"{auth_base}/application/o/userinfo/"

        token_verifier = JWTVerifier(jwks_uri=jwks_url, issuer=issuer)

        super().__init__(
            upstream_authorization_endpoint=authorize_url,
            upstream_token_endpoint=token_url,
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            upstream_revocation_endpoint=revoke_url,
            token_verifier=token_verifier,
            base_url=base_url,
            valid_scopes=["openid", "profile", "email"],
            **kwargs,
        )

        self._allowed_usernames: frozenset[str] = frozenset(
            u.lower().strip() for u in (allowed_usernames or []) if u.strip()
        )
        logger.debug(
            "AuthentikProvider (Pola B) siap — issuer: %s | slug: %s | allowed: %s",
            issuer,
            slug,
            list(self._allowed_usernames) or "(semua diizinkan)",
        )

    async def _extract_upstream_claims(self, idp_tokens: dict[str, Any]) -> dict[str, Any] | None:
        """Ambil klaim user dari Authentik userinfo, validasi akses, cache upstream token.

        Dipanggil sekali saat pertukaran authorization code. Upstream access token
        disimpan dalam ``_token_cache`` (keyed by Authentik sub) agar dapat diteruskan
        ke backend pada tool call berikutnya.

        Raises:
            TokenError: access_token kosong, userinfo tak terjangkau/invalid,
                atau username tidak diizinkan. ``error_code`` HARUS salah satu nilai
                valid: ``invalid_request``, ``invalid_client``, ``invalid_grant``,
                ``unauthorized_client``, ``unsupported_grant_type``, ``invalid_scope``.
        """
        access_token = idp_tokens.get("access_token", "")
        if not access_token:
            raise TokenError("invalid_grant", "Upstream access token tidak tersedia")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self._userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.RequestError as exc:
            logger.warning("Gagal menghubungi Authentik userinfo: %s", exc)
            raise TokenError(
                "invalid_request", "Tidak dapat memverifikasi identitas dari Authentik"
            ) from exc

        if response.status_code != 200:
            logger.warning("Authentik userinfo menolak token (status=%d)", response.status_code)
            raise TokenError("invalid_grant", "Token Authentik tidak valid atau kedaluwarsa")

        userinfo = response.json()
        sub: str = userinfo.get("sub", "").strip()
        if not sub:
            raise TokenError("invalid_grant", "Tidak dapat mengambil sub dari Authentik userinfo")

        username: str = (
            (userinfo.get("preferred_username") or userinfo.get("email", "")).lower().strip()
        )

        if self._allowed_usernames and username not in self._allowed_usernames:
            logger.warning("Akses ditolak untuk user Authentik '%s'", username)
            raise TokenError("unauthorized_client", f"User '{username}' tidak diizinkan")

        # Simpan upstream token agar dapat diteruskan ke backend di tool calls.
        _token_cache[sub] = access_token
        logger.info("User Authentik '%s' (sub=%s) berhasil diautentikasi", username, sub)

        return {
            "sub": sub,
            "username": username,
            "email": userinfo.get("email"),
            "name": userinfo.get("name"),
            "groups": userinfo.get("groups", []),
        }


class BearerApiKeyVerifier(TokenVerifier):
    """TokenVerifier yang memvalidasi static Bearer token (API key).

    Untuk klien tanpa OAuth (VS Code/CLI/otomasi). Token valid = nilai persis
    ``MCP_API_KEY``.

    Args:
        api_key: API key statis (wajib non-kosong).

    Raises:
        ValueError: bila ``api_key`` kosong/spasi.
    """

    def __init__(self, *, api_key: str) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key tidak boleh kosong")
        self._api_key = api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        """Kembalikan AccessToken bila token cocok dengan API key, else None."""
        if token == self._api_key:
            return AccessToken(token=token, client_id="api-key-client", scopes=[])
        return None
