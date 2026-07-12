"""Test `client.py` tembus sampai layer httpx (via `respx`) — bukan mock `backend_*`.

Test lain (`test_server.py`) mem-mock `backend_get`/`backend_post`/dst langsung,
sehingga `backend_request` (tempat bug 204/304 & JSON-parsing berada) tidak pernah
benar-benar dieksekusi. Test di sini menembus sampai `httpx.AsyncClient` (di-mock
`respx`) agar regresi semacam itu benar-benar tertangkap.

Memakai `respx.mock(...)` sebagai context manager (bukan dekorator) — pola yang
sama dipakai di `budget-sekolah-mcp/tests/conftest.py`.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from anjab_abk_mcp.client import BackendError, backend_delete, backend_get
from anjab_abk_mcp.config import settings

_BASE = settings.backend_base_url.rstrip("/")


@pytest.mark.asyncio
async def test_backend_delete_204_tidak_raise_dan_kembalikan_dict_kosong():
    with respx.mock(assert_all_called=False) as mock:
        mock.delete(f"{_BASE}/api/v1/dcs/sesi/dses_x").mock(return_value=httpx.Response(204))
        result = await backend_delete("/api/v1/dcs/sesi/dses_x")
    assert result == {}


@pytest.mark.asyncio
async def test_backend_get_304_tidak_raise_dan_kembalikan_dict_kosong():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_BASE}/api/v1/sekolah/skl_x").mock(return_value=httpx.Response(304))
        result = await backend_get("/api/v1/sekolah/skl_x")
    assert result == {}


@pytest.mark.asyncio
async def test_body_non_json_pada_200_raise_backend_error_bukan_json_mentah():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_BASE}/api/v1/sekolah").mock(
            return_value=httpx.Response(
                200, content=b"bukan json", headers={"content-type": "text/plain"}
            )
        )
        with pytest.raises(BackendError, match="bukan JSON valid"):
            await backend_get("/api/v1/sekolah")


@pytest.mark.asyncio
async def test_response_200_json_list_dikembalikan_apa_adanya():
    payload = [{"id": "a"}, {"id": "b"}]
    with respx.mock(assert_all_called=False) as mock:
        mock.get(f"{_BASE}/api/v1/dcs/sesi/dses_x/responden").mock(
            return_value=httpx.Response(200, json=payload)
        )
        result = await backend_get("/api/v1/dcs/sesi/dses_x/responden")
    assert result == payload


@pytest.mark.asyncio
async def test_backend_delete_paksa_diteruskan_sebagai_query_param():
    with respx.mock(assert_all_called=False) as mock:
        route = mock.delete(f"{_BASE}/api/v1/dcs/sesi/dses_x", params={"paksa": "true"}).mock(
            return_value=httpx.Response(204)
        )
        result = await backend_delete("/api/v1/dcs/sesi/dses_x", params={"paksa": True})
        assert route.called
    assert result == {}


@pytest.mark.asyncio
async def test_error_status_tetap_raise_backend_error():
    with respx.mock(assert_all_called=False) as mock:
        mock.delete(f"{_BASE}/api/v1/dcs/sesi/dses_x").mock(
            return_value=httpx.Response(
                422, json={"message": "Sesi hanya dapat dihapus saat DRAFT."}
            )
        )
        with pytest.raises(BackendError) as exc_info:
            await backend_delete("/api/v1/dcs/sesi/dses_x")
    assert exc_info.value.status_code == 422
