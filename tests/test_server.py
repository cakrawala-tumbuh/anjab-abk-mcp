"""Test tools MCP ANJAB-ABK menggunakan FastMCP Client in-memory.

Client menunjuk langsung ke objek ``mcp`` (tanpa proses/port terpisah) sehingga
cepat dan deterministik. Backend di-mock agar test tidak membutuhkan server nyata.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from anjab_abk_mcp.server import mcp

# Path modul yang di-mock (helper client di server.py)
_GET = "anjab_abk_mcp.server.backend_get"
_POST = "anjab_abk_mcp.server.backend_post"
_PATCH = "anjab_abk_mcp.server.backend_patch"
_DELETE = "anjab_abk_mcp.server.backend_delete"


@pytest.mark.asyncio
async def test_tools_terdaftar():
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    # Periksa representasi dari tiap domain
    assert "daftar_jenjang_pendidikan" in names
    assert "daftar_sekolah" in names
    assert "daftar_jabatan" in names
    assert "daftar_partisipan" in names
    assert "daftar_sme_panel" in names
    assert "daftar_ti_sesi" in names
    assert "daftar_dcs_sesi" in names
    assert "daftar_wcp_sesi" in names
    assert "daftar_ts_sesi" in names


@pytest.mark.asyncio
async def test_daftar_jenjang_pendidikan():
    payload = {"items": [{"id": "uuid-1", "kode": "SD", "nama": "Sekolah Dasar"}], "total": 1}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_jenjang_pendidikan", {})
    assert result.data["total"] == 1
    assert result.data["items"][0]["kode"] == "SD"


@pytest.mark.asyncio
async def test_daftar_sekolah():
    payload = {"items": [{"id": "uuid-s", "nama": "SDN 01 Contoh"}], "total": 1}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_sekolah", {})
    assert result.data["items"][0]["nama"] == "SDN 01 Contoh"


@pytest.mark.asyncio
async def test_buat_sekolah():
    payload = {"id": "uuid-baru", "nama": "SMP Teladan", "jenjang_pendidikan_id": "uuid-smp"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_sekolah",
                {"nama": "SMP Teladan", "jenjang_pendidikan_id": "uuid-smp"},
            )
    assert result.data["id"] == "uuid-baru"


@pytest.mark.asyncio
async def test_daftar_ti_sesi():
    payload = {"items": [{"id": "uuid-ti", "unit": "SD", "status": "DRAFT"}], "total": 1}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_ti_sesi", {})
    assert result.data["items"][0]["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_buat_ti_sesi():
    payload = {"id": "uuid-ti-baru", "unit": "SMP", "status": "DRAFT"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_ti_sesi",
                {"unit": "SMP", "kategori_jabatan": "guru", "periode": "2025/2026"},
            )
    assert result.data["id"] == "uuid-ti-baru"


@pytest.mark.asyncio
async def test_ti_tambah_responden_tanpa_arg_raise():
    """Wajib error bila tidak ada partisipan_id maupun nama."""
    async with Client(mcp) as client:
        with pytest.raises(Exception):
            await client.call_tool("ti_tambah_responden", {"sesi_id": "uuid-sesi"})


@pytest.mark.asyncio
async def test_daftar_dcs_sesi():
    payload = {"items": [], "total": 0}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_dcs_sesi", {})
    assert result.data["total"] == 0


@pytest.mark.asyncio
async def test_daftar_wcp_sesi():
    payload = {"items": [], "total": 0}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_wcp_sesi", {})
    assert result.data["total"] == 0


@pytest.mark.asyncio
async def test_daftar_ts_sesi():
    payload = {"items": [], "total": 0}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_ts_sesi", {})
    assert result.data["total"] == 0


# ── Kelengkapan tool baru ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_semua_endpoint_punya_tool():
    """Memastikan jumlah tool besar (kelengkapan CRUD per domain) terdaftar."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    # Representasi kelengkapan per domain
    for nm in [
        "buat_jenjang_pendidikan",
        "perbarui_jenjang_pendidikan",
        "hapus_jenjang_pendidikan",
        "cari_sekolah",
        "detail_sekolah",
        "daftar_mata_pelajaran",
        "buat_mata_pelajaran",
        "buat_sme_panel",
        "hapus_anggota_sme_panel",
        "ti_submit_seleksi",
        "ti_submit_tahap2",
        "ti_tutup_sesi",
        "dcs_submit_jawaban",
        "wcp_submit_jawaban",
        "ts_buat_log",
        "info_saya",
    ]:
        assert nm in names, f"tool {nm} tidak terdaftar"
    assert len(names) >= 120


@pytest.mark.asyncio
async def test_buat_jenjang_pendidikan():
    payload = {"id": "uuid-jp", "kode": "SD", "nama": "SD"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("buat_jenjang_pendidikan", {"kode": "SD", "nama": "SD"})
    assert result.data["id"] == "uuid-jp"
    assert m.await_args.kwargs["body"]["kode"] == "SD"


@pytest.mark.asyncio
async def test_buat_mata_pelajaran():
    payload = {"id": "mp_1", "kode": "MTK", "nama": "Matematika"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_mata_pelajaran",
                {"kode": "MTK", "nama": "Matematika", "kelompok": "umum"},
            )
    assert result.data["kode"] == "MTK"


@pytest.mark.asyncio
async def test_perbarui_sekolah_hanya_field_terisi():
    """Body PATCH hanya memuat field non-None."""
    with patch(_PATCH, new_callable=AsyncMock, return_value={"id": "s1"}) as m:
        async with Client(mcp) as client:
            await client.call_tool("perbarui_sekolah", {"sekolah_id": "s1", "kota": "Semarang"})
    body = m.await_args.kwargs["body"]
    assert body == {"kota": "Semarang"}


@pytest.mark.asyncio
async def test_hapus_jabatan():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("hapus_jabatan", {"jabatan_id": "j1"})
    assert result.data["ok"] is True
    assert "/api/v1/jabatan/j1" in m.await_args.args[0]


@pytest.mark.asyncio
async def test_dcs_submit_jawaban():
    with patch(_POST, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            await client.call_tool(
                "dcs_submit_jawaban",
                {"responden_id": "r1", "jawaban": [{"item_id": "D1a", "skor_raw": 4}]},
            )
    assert m.await_args.kwargs["body"]["jawaban"][0]["item_id"] == "D1a"
