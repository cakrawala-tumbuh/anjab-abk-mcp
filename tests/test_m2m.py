"""Test util login M2M (tanpa jaringan)."""

from anjab_abk_mcp import m2m


def test_pkce_pair_valid():
    verifier, challenge = m2m._pkce_pair()
    assert 43 <= len(verifier) <= 128
    assert challenge and "=" not in challenge and "+" not in challenge and "/" not in challenge


def test_m2m_configured_false_by_default(monkeypatch):
    for attr in (
        "backend_m2m_username",
        "backend_m2m_password",
        "backend_m2m_authentik_url",
        "backend_m2m_client_id",
        "backend_m2m_redirect_uri",
    ):
        monkeypatch.setattr(m2m.settings, attr, None, raising=False)
    assert m2m.m2m_configured() is False


def test_m2m_configured_true_when_complete(monkeypatch):
    monkeypatch.setattr(m2m.settings, "backend_m2m_username", "svc", raising=False)
    monkeypatch.setattr(m2m.settings, "backend_m2m_password", "x", raising=False)
    monkeypatch.setattr(m2m.settings, "backend_m2m_authentik_url", "https://a", raising=False)
    monkeypatch.setattr(m2m.settings, "backend_m2m_client_id", "cid", raising=False)
    monkeypatch.setattr(m2m.settings, "backend_m2m_redirect_uri", "https://cb", raising=False)
    assert m2m.m2m_configured() is True


def test_invalidate_clears_cache():
    m2m._cache["access_token"] = "x"
    m2m._cache["exp"] = 9e9
    m2m.invalidate()
    assert m2m._cache["access_token"] is None
