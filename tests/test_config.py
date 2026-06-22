"""Test parsing konfigurasi — fokus pada ``AUTHENTIK_ALLOWED_USERNAMES``.

Regresi yang dijaga: pydantic-settings mencoba ``json.loads()`` pada field
``list[str]`` di level source SEBELUM validator berjalan. Tanpa source kustom di
``config.py``, env plain string (``user1``) atau comma-separated (``user1,user2``)
melempar ``JSONDecodeError`` saat startup. Tiga format harus diterima: nilai tunggal,
comma-separated, dan JSON array.

``_env_file=None`` dipakai agar ``.env`` lokal developer tidak bocor ke test.
"""

import pytest

from anjab_abk_mcp.config import Settings


@pytest.fixture(autouse=True)
def _bersihkan_env(monkeypatch):
    monkeypatch.delenv("AUTHENTIK_ALLOWED_USERNAMES", raising=False)


def _settings(monkeypatch, value: str) -> Settings:
    monkeypatch.setenv("AUTHENTIK_ALLOWED_USERNAMES", value)
    return Settings(_env_file=None)


def test_username_tunggal(monkeypatch):
    assert _settings(monkeypatch, "akadmin").authentik_allowed_usernames == ["akadmin"]


def test_username_comma_separated(monkeypatch):
    assert _settings(monkeypatch, "akadmin,user2").authentik_allowed_usernames == [
        "akadmin",
        "user2",
    ]


def test_username_comma_dengan_spasi(monkeypatch):
    assert _settings(monkeypatch, "akadmin, user2 , user3").authentik_allowed_usernames == [
        "akadmin",
        "user2",
        "user3",
    ]


def test_username_json_array(monkeypatch):
    assert _settings(monkeypatch, '["alice","bob"]').authentik_allowed_usernames == [
        "alice",
        "bob",
    ]


def test_username_kosong_pakai_default(monkeypatch):
    # env_ignore_empty=True → string kosong diabaikan, jatuh ke default [].
    assert _settings(monkeypatch, "").authentik_allowed_usernames == []


def test_default_tanpa_env(monkeypatch):
    assert Settings(_env_file=None).authentik_allowed_usernames == []


# --- jalur FILE .env (DotEnvSettingsSource) — bukan hanya OS env. Ini alur baku
#     "salin .env.example menjadi .env"; sumber dotenv harus ikut dipatch atau
#     plain/comma value crash JSONDecodeError saat startup.
def _settings_from_dotenv(tmp_path, monkeypatch, value: str) -> Settings:
    monkeypatch.delenv("AUTHENTIK_ALLOWED_USERNAMES", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"AUTHENTIK_ALLOWED_USERNAMES={value}\n")
    return Settings(_env_file=str(env_file))


def test_dotenv_file_comma_separated(tmp_path, monkeypatch):
    s = _settings_from_dotenv(tmp_path, monkeypatch, "akadmin,user2")
    assert s.authentik_allowed_usernames == ["akadmin", "user2"]


def test_dotenv_file_tunggal(tmp_path, monkeypatch):
    s = _settings_from_dotenv(tmp_path, monkeypatch, "akadmin")
    assert s.authentik_allowed_usernames == ["akadmin"]


def test_dotenv_file_json_array(tmp_path, monkeypatch):
    s = _settings_from_dotenv(tmp_path, monkeypatch, '["alice","bob"]')
    assert s.authentik_allowed_usernames == ["alice", "bob"]
