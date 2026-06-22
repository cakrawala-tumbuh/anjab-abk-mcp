"""Login M2M headless ke Authentik untuk mode stdio (tanpa OAuth user).

Backend anjab-abk-backend hanya menerima JWT terbitan provider OAuth2 Authentik
(divalidasi via JWKS). Dalam mode stdio (mis. Claude Code lokal) tidak ada token
user dari alur OAuth, sehingga MCP perlu memperoleh token sendiri.

Modul ini menjalankan **Authorization Code flow + PKCE** sepenuhnya lewat HTTP
(tanpa browser) memakai *flow executor API* Authentik:

  GET  /application/o/authorize/        → membuat sesi + mengarahkan ke flow
  GET  /api/v3/flows/executor/<slug>/   → tahap identifikasi
  POST  (uid_field)                     → tahap password
  POST  (password)                      → selesai → redirect berisi ?code=
  POST /application/o/token/            → tukar code+verifier jadi access_token

Token di-cache di memori dan diperbarui otomatis sebelum kedaluwarsa. Kredensial
service user dibaca dari config (`backend_m2m_*`). Tidak ada browser, tidak ada
perubahan di sisi Authentik.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .config import settings

logger = logging.getLogger(__name__)

# Cache token sederhana di level proses.
_cache: dict[str, object] = {"access_token": None, "exp": 0.0}

# Margin (detik) sebelum exp dianggap perlu refresh.
_REFRESH_MARGIN = 60.0


class M2MError(Exception):
    """Gagal memperoleh token M2M dari Authentik."""


def m2m_configured() -> bool:
    """True bila kredensial M2M lengkap di config."""
    return bool(
        settings.backend_m2m_username
        and settings.backend_m2m_password
        and settings.backend_m2m_authentik_url
        and settings.backend_m2m_client_id
        and settings.backend_m2m_redirect_uri
    )


def invalidate() -> None:
    """Kosongkan cache token (mis. setelah backend membalas 401)."""
    _cache["access_token"] = None
    _cache["exp"] = 0.0


def _pkce_pair() -> tuple[str, str]:
    """Buat (code_verifier, code_challenge) PKCE S256."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


async def _login_flow(client: httpx.AsyncClient, base: str, flow_slug: str, query: str) -> None:
    """Autentikasi sesi (identifikasi → password) lewat flow executor API.

    Mengisi cookie sesi pada ``client`` sehingga permintaan authorize berikutnya
    langsung diizinkan. Tidak mengembalikan code — pengambilan code dilakukan
    terpisah dengan mengulang permintaan authorize.

    Raises:
        M2MError: Bila kredensial salah, ada MFA, atau tahap tak terduga.
    """
    flow_url = f"{base}/api/v3/flows/executor/{flow_slug}/"
    params = {"query": query}
    headers = {"Accept": "application/json"}

    def _is_done(d: dict) -> bool:
        return (
            d.get("component") in ("xak-flow-redirect", "ak-stage-redirect")
            or d.get("type") == "redirect"
        )

    resp = await client.get(flow_url, params=params, headers=headers, follow_redirects=False)
    if resp.status_code != 200:
        raise M2MError(f"Gagal memulai flow ({resp.status_code}).")
    data = resp.json()

    for _ in range(12):
        component = data.get("component", "")
        if _is_done(data):
            return  # login selesai
        if component == "ak-stage-identification":
            body: dict = {"component": component, "uid_field": settings.backend_m2m_username}
            # Beberapa konfigurasi menggabungkan password di tahap identifikasi.
            if any(f.get("name") == "password" for f in data.get("fields", []) or []):
                body["password"] = settings.backend_m2m_password
        elif component == "ak-stage-password":
            body = {"component": component, "password": settings.backend_m2m_password}
        elif component in (
            "ak-stage-authenticator-validate",
            "ak-stage-authenticator-totp",
            "ak-stage-authenticator-webauthn",
        ):
            raise M2MError("Akun M2M memiliki MFA aktif — tidak didukung untuk login headless.")
        else:
            msg = data.get("response_errors") or data.get("detail") or component
            raise M2MError(f"Tahap flow tak terduga atau gagal: {msg}")

        # Ikuti redirect agar penyelesaian stage benar-benar meng-commit sesi.
        resp = await client.post(
            flow_url, params=params, headers=headers, json=body, follow_redirects=True
        )
        if resp.status_code != 200:
            raise M2MError(f"Tahap flow gagal ({resp.status_code}): {resp.text[:200]}")
        ctype = resp.headers.get("content-type", "")
        if "application/json" not in ctype:
            return  # flow mengarah ke halaman non-flow → login selesai
        data = resp.json()

    raise M2MError("Flow autentikasi tidak selesai (terlalu banyak tahap).")


async def _extract_code(client: httpx.AsyncClient, base: str, to: str, redirect_uri: str) -> str:
    """Ikuti rantai redirect internal sampai menemukan ``redirect_uri?code=``.

    Tidak pernah benar-benar memuat ``redirect_uri`` (callback aplikasi) — code
    diambil dari string URL begitu Location menunjuk ke sana.
    """
    url = to if to.startswith("http") else f"{base}{to}"
    for _ in range(12):
        if url.startswith(redirect_uri):
            qs = parse_qs(urlparse(url).query)
            if "code" in qs:
                return qs["code"][0]
            raise M2MError(f"Redirect ke callback tanpa 'code': {qs}")
        resp = await client.get(url, follow_redirects=False)
        loc = resp.headers.get("location")
        if not loc:
            raise M2MError(f"Tidak ada redirect lanjutan dari {url} (status {resp.status_code}).")
        url = loc if loc.startswith("http") else f"{base}{loc}"
    raise M2MError("Tidak menemukan authorization code dalam rantai redirect.")


async def get_m2m_access_token() -> str:
    """Ambil access_token M2M (dari cache atau login baru ke Authentik).

    Returns:
        Access token (JWT) yang valid untuk backend.

    Raises:
        M2MError: Bila login/tukar token gagal.
    """
    now = time.time()
    token = _cache.get("access_token")
    if token and float(_cache.get("exp", 0.0)) - _REFRESH_MARGIN > now:
        return str(token)

    if not m2m_configured():
        raise M2MError("Kredensial M2M belum lengkap (backend_m2m_*).")

    base = str(settings.backend_m2m_authentik_url).rstrip("/")
    client_id = str(settings.backend_m2m_client_id)
    redirect_uri = str(settings.backend_m2m_redirect_uri)
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    authorize_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": settings.backend_m2m_scope,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    query = urlencode(authorize_params)

    authorize_url = f"{base}/application/o/authorize/"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Inisiasi authorize → membuat pending request + mengarahkan ke flow.
        await client.get(authorize_url, params=authorize_params)
        # Autentikasi sesi (identifikasi + password) via flow executor.
        await _login_flow(client, base, settings.backend_m2m_flow_slug, query)
        # Sesi kini terautentikasi → ulangi authorize untuk mendapat code (tanpa
        # mengikuti redirect agar bisa membaca Location ke redirect_uri).
        resp = await client.get(authorize_url, params=authorize_params, follow_redirects=False)
        loc = resp.headers.get("location")
        if not loc:
            raise M2MError(
                f"Authorize ulang tidak menghasilkan redirect (status {resp.status_code}) — "
                "kemungkinan login gagal."
            )
        code = await _extract_code(client, base, loc, redirect_uri)
        # Tukar code + verifier jadi token (public client → tanpa client_secret).
        resp = await client.post(
            f"{base}/application/o/token/",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        )
    if resp.status_code != 200:
        raise M2MError(f"Tukar token gagal ({resp.status_code}): {resp.text[:200]}")
    payload = resp.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise M2MError(f"Respons token tanpa access_token: {payload}")

    _cache["access_token"] = access_token
    _cache["exp"] = now + float(payload.get("expires_in", 3600))
    logger.info("Token M2M Authentik diperoleh (berlaku %ss).", payload.get("expires_in", 3600))
    return str(access_token)
