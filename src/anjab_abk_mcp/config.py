"""Konfigurasi runtime via pydantic-settings.

Semua nilai dibaca dari environment / file `.env`. Diinstansiasi sekali sebagai
singleton `settings` dan diimpor dari modul lain.

Pola B: backend anjab-abk-backend sudah memakai Authentik sebagai IdP.
MCP memakai AUTHENTIK_ISSUER_URL yang sama dengan backend — token user Authentik
diverifikasi dengan JWKS yang sama, lalu diteruskan ke backend apa adanya.
"""

from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasi ANJAB-ABK MCP server.

    Attributes:
        mcp_server_name: Nama server yang ditampilkan ke MCP client.
        mcp_log_level: Level logging (DEBUG, INFO, WARNING, ERROR).
        mcp_transport: Transport saat dijalankan via `python -m anjab_abk_mcp`
            (`stdio` default, atau `http`/`sse`).
        mcp_host: Host bind saat transport http/sse.
        mcp_port: Port saat transport http/sse.
        mcp_base_url: URL publik MCP server. WAJIB diisi agar OAuth Authentik
            (Claude.ai) berfungsi. Contoh: ``https://mcp.anjab.example.com``.
        backend_base_url: URL base anjab-abk-backend.
            Contoh: ``https://api.anjab.example.com``.
        backend_api_token: Token Authentik statis untuk mode stdio/API key
            (service account). Kosong = backend tidak dapat diakses tanpa OAuth.
        authentik_issuer_url: Issuer URL Authentik, SAMA dengan konfigurasi
            anjab-abk-backend. Format: ``https://auth.example.com/application/o/<slug>/``.
        authentik_client_id: Client ID dari Authentik OAuth2 Provider MCP.
        authentik_client_secret: Client Secret dari Authentik OAuth2 Provider MCP.
        authentik_allowed_usernames: Daftar ``preferred_username`` yang diizinkan
            (kosong = semua user yang lolos policy Authentik diizinkan). Diterima
            dari environment dalam tiga format: JSON array (``["alice","bob"]``),
            comma-separated (``alice,bob``), atau nilai tunggal (``alice``).
        mcp_api_key: API key statis untuk klien non-OAuth (VS Code/CLI). Request
            wajib menyertakan ``Authorization: Bearer <key>`` atau ``X-API-Key``.
    """

    mcp_server_name: str = "ANJAB-ABK MCP"
    mcp_log_level: str = "INFO"

    # Transport (untuk `python -m anjab_abk_mcp`)
    mcp_transport: str = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000

    # Backend
    backend_base_url: str = "http://localhost:8001"
    backend_api_token: str | None = None

    # OAuth Authentik Pola B (pintu depan — untuk Claude.ai)
    mcp_base_url: str | None = None
    authentik_issuer_url: str | None = None
    authentik_client_id: str | None = None
    authentik_client_secret: str | None = None
    authentik_allowed_usernames: list[str] = []

    # API key (untuk VS Code / CLI / tools non-OAuth)
    mcp_api_key: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple:
        """Terima ``authentik_allowed_usernames`` sebagai JSON / comma-separated / tunggal.

        pydantic-settings memperlakukan field ``list[str]`` sebagai nilai kompleks dan
        mencoba ``json.loads()`` di level source SEBELUM validator berjalan. Tanpa patch
        ini, plain string seperti ``user1`` atau ``user1,user2`` melempar
        ``JSONDecodeError`` saat startup.

        PENTING: patch WAJIB dikenakan ke DUA source — ``env_settings`` (OS environment)
        DAN ``dotenv_settings`` (file ``.env``). Kalau hanya OS env yang dipatch, nilai
        plain/comma di ``.env`` tetap crash lewat ``DotEnvSettingsSource`` — padahal alur
        baku project ini adalah "salin .env.example menjadi .env".
        """

        def _lenient(source: Any) -> Any:
            original = source.decode_complex_value

            def decode(field_name: str, field: Any, value: Any) -> Any:
                if field_name == "authentik_allowed_usernames" and isinstance(value, str):
                    v = value.strip()
                    if not v:
                        return []
                    if not v.startswith("["):
                        return [u.strip() for u in v.split(",") if u.strip()]
                return original(field_name, field, value)

            source.decode_complex_value = decode
            return source

        return (
            init_settings,
            _lenient(env_settings),
            _lenient(dotenv_settings),
            file_secret_settings,
        )

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
