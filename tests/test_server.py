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
_PUT = "anjab_abk_mcp.server.backend_put"
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
    assert "dcs_instrumen" in names
    assert "wcp_instrumen" in names
    assert "daftar_ts_penugasan" in names
    assert "buat_ts_penugasan_banyak" in names
    assert "ti_tambah_responden_banyak" in names
    assert "opm_tambah_responden" in names
    assert "opm_tambah_responden_banyak" in names
    assert "buat_opm_sesi" in names
    assert "opm_submit_jawaban" in names
    assert "dcs_reset_instrumen" in names
    assert "partisipan_saya" in names
    assert "dcs_hapus_item" in names
    assert "wcp_hapus_item" in names


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
    payload = {"id": "uuid-ti-baru", "cabang": "Bandung", "status": "DRAFT"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_ti_sesi",
                {"jabatan_id": "jbt_a1b2", "cabang": "Bandung"},
            )
    assert result.data["id"] == "uuid-ti-baru"
    assert m.await_args.args[0] == "/api/v1/task-inventory/sesi"
    assert m.await_args.kwargs["body"] == {"jabatan_id": "jbt_a1b2", "cabang": "Bandung"}


@pytest.mark.asyncio
async def test_buat_ti_sesi_cabang_invalid_ditolak():
    """cabang di luar {Bandung, Semarang} ditolak validasi input (Literal) — tak
    pernah sampai ke backend; tool melempar error yang jelas, bukan crash."""
    with patch(_POST, new_callable=AsyncMock) as m:
        async with Client(mcp) as client:
            with pytest.raises(Exception):
                await client.call_tool(
                    "buat_ti_sesi",
                    {"jabatan_id": "jbt_a1b2", "cabang": "Jakarta"},
                )
    m.assert_not_awaited()


@pytest.mark.asyncio
async def test_perbarui_ti_sesi_cabang():
    """perbarui_ti_sesi kirim cabang (bukan periode/min/max yang sudah dibuang 037)."""
    payload = {"id": "tises-1", "cabang": "Semarang"}
    with patch(_PATCH, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "perbarui_ti_sesi", {"sesi_id": "tises-1", "cabang": "Semarang"}
            )
    assert result.data["cabang"] == "Semarang"
    assert m.await_args.args[0] == "/api/v1/task-inventory/sesi/tises-1"
    assert m.await_args.kwargs["body"] == {"cabang": "Semarang"}


@pytest.mark.asyncio
async def test_ti_tambah_responden_tanpa_arg_raise():
    """Wajib error bila tidak ada partisipan_id maupun nama."""
    async with Client(mcp) as client:
        with pytest.raises(Exception):
            await client.call_tool("ti_tambah_responden", {"sesi_id": "uuid-sesi"})


@pytest.mark.asyncio
async def test_ti_tambah_responden_banyak():
    payload = {"created": [{"id": "trsp-1"}, {"id": "trsp-2"}], "skipped": []}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "ti_tambah_responden_banyak",
                {"sesi_id": "uuid-sesi", "partisipan_ids": ["p1", "p2"]},
            )
    assert len(result.data["created"]) == 2
    assert m.await_args.args[0] == "/api/v1/task-inventory/sesi/uuid-sesi/responden/bulk"
    assert m.await_args.kwargs["body"] == {"partisipan_ids": ["p1", "p2"]}


@pytest.mark.asyncio
async def test_dcs_instrumen():
    """DCS instrumen singleton — dipanggil tanpa argumen apa pun."""
    payload = {"id": "dcs", "status": "OPEN", "min_responden": 5, "catatan": None}
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("dcs_instrumen", {})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/dcs/instrumen"


@pytest.mark.asyncio
async def test_wcp_instrumen():
    """WCP instrumen singleton — dipanggil tanpa argumen apa pun."""
    payload = {"id": "wcp", "status": "OPEN", "min_responden": 5, "catatan": None}
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_instrumen", {})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/wcp/instrumen"


@pytest.mark.asyncio
async def test_dcs_tambah_responden_bulk():
    """dcs_tambah_responden menerima daftar partisipan_ids dan mengirimnya sebagai body."""
    payload = {
        "created": [{"id": "drsp-1"}, {"id": "drsp-2"}],
        "skipped": [{"partisipan_id": "p5", "alasan": "sudah_terdaftar"}],
    }
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dcs_tambah_responden", {"partisipan_ids": ["p1", "p2", "p3", "p4", "p5"]}
            )
    assert len(result.data["created"]) == 2
    assert len(result.data["skipped"]) == 1
    assert m.await_args.args[0] == "/api/v1/dcs/responden"
    assert m.await_args.kwargs["body"] == {"partisipan_ids": ["p1", "p2", "p3", "p4", "p5"]}


@pytest.mark.asyncio
async def test_wcp_tambah_responden_bulk():
    payload = {"created": [{"id": "wrsp-1"}], "skipped": []}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_tambah_responden", {"partisipan_ids": ["p1"]})
    assert len(result.data["created"]) == 1
    assert result.data["skipped"] == []
    assert m.await_args.args[0] == "/api/v1/wcp/responden"
    assert m.await_args.kwargs["body"] == {"partisipan_ids": ["p1"]}


@pytest.mark.asyncio
async def test_dcs_analisis_dan_hasil_tanpa_argumen():
    """dcs_analisis & dcs_hasil tidak lagi menerima sesi_id/wcp_sesi_id."""
    with patch(_POST, new_callable=AsyncMock, return_value={"k_index": 0.4}) as m_post:
        async with Client(mcp) as client:
            await client.call_tool("dcs_analisis", {})
    assert m_post.await_args.args[0] == "/api/v1/dcs/analisis"

    with patch(_GET, new_callable=AsyncMock, return_value={"k_index": 0.4}) as m_get:
        async with Client(mcp) as client:
            await client.call_tool("dcs_hasil", {})
    assert m_get.await_args.args[0] == "/api/v1/dcs/hasil"


@pytest.mark.asyncio
async def test_wcp_analisis_dan_hasil_tanpa_argumen():
    with patch(_POST, new_callable=AsyncMock, return_value={"n_responden": 3}) as m_post:
        async with Client(mcp) as client:
            await client.call_tool("wcp_analisis", {})
    assert m_post.await_args.args[0] == "/api/v1/wcp/analisis"

    with patch(_GET, new_callable=AsyncMock, return_value={"n_responden": 3}) as m_get:
        async with Client(mcp) as client:
            await client.call_tool("wcp_hasil", {})
    assert m_get.await_args.args[0] == "/api/v1/wcp/hasil"


@pytest.mark.asyncio
async def test_dcs_perbarui_instrumen_hanya_field_terisi():
    with patch(_PATCH, new_callable=AsyncMock, return_value={"id": "dcs"}) as m:
        async with Client(mcp) as client:
            await client.call_tool("dcs_perbarui_instrumen", {"catatan": "Studi 2026"})
    assert m.await_args.args[0] == "/api/v1/dcs/instrumen"
    assert m.await_args.kwargs["body"] == {"catatan": "Studi 2026"}


@pytest.mark.asyncio
async def test_dcs_tutup_dan_buka_ulang_instrumen():
    with patch(_POST, new_callable=AsyncMock, return_value={"status": "CLOSED"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("dcs_tutup_instrumen", {})
    assert result.data["status"] == "CLOSED"
    assert m.await_args.args[0] == "/api/v1/dcs/instrumen/tutup"

    with patch(_POST, new_callable=AsyncMock, return_value={"status": "OPEN"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("dcs_buka_ulang_instrumen", {})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/dcs/instrumen/buka-ulang"


@pytest.mark.asyncio
async def test_wcp_tutup_dan_buka_ulang_instrumen():
    with patch(_POST, new_callable=AsyncMock, return_value={"status": "CLOSED"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_tutup_instrumen", {})
    assert result.data["status"] == "CLOSED"
    assert m.await_args.args[0] == "/api/v1/wcp/instrumen/tutup"

    with patch(_POST, new_callable=AsyncMock, return_value={"status": "OPEN"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_buka_ulang_instrumen", {})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/wcp/instrumen/buka-ulang"


@pytest.mark.asyncio
async def test_dcs_reset_instrumen():
    """Reset destruktif DCS: hapus semua responden, status → OPEN."""
    with patch(_POST, new_callable=AsyncMock, return_value={"status": "OPEN"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("dcs_reset_instrumen", {})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/dcs/instrumen/reset"


@pytest.mark.asyncio
async def test_wcp_reset_instrumen():
    """Reset destruktif WCP: hapus semua responden, status → OPEN."""
    with patch(_POST, new_callable=AsyncMock, return_value={"status": "OPEN"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_reset_instrumen", {})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/wcp/instrumen/reset"


@pytest.mark.asyncio
async def test_dcs_daftar_responden_tanpa_argumen():
    payload = [{"id": "drsp-1"}]
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("dcs_daftar_responden", {})
    assert len(result.data) == 1
    assert m.await_args.args[0] == "/api/v1/dcs/responden"


@pytest.mark.asyncio
async def test_wcp_daftar_responden_tanpa_argumen():
    payload = [{"id": "wrsp-1"}]
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_daftar_responden", {})
    assert len(result.data) == 1
    assert m.await_args.args[0] == "/api/v1/wcp/responden"


@pytest.mark.asyncio
async def test_dcs_hasil_responden_path():
    with patch(_GET, new_callable=AsyncMock, return_value={"responden_id": "r1"}) as m:
        async with Client(mcp) as client:
            await client.call_tool("dcs_hasil_responden", {"responden_id": "r1"})
    assert m.await_args.args[0] == "/api/v1/dcs/hasil-responden/r1"


@pytest.mark.asyncio
async def test_wcp_hasil_responden_path():
    with patch(_GET, new_callable=AsyncMock, return_value={"responden_id": "r1"}) as m:
        async with Client(mcp) as client:
            await client.call_tool("wcp_hasil_responden", {"responden_id": "r1"})
    assert m.await_args.args[0] == "/api/v1/wcp/hasil-responden/r1"


@pytest.mark.asyncio
async def test_tidak_ada_tool_sesi_dcs_wcp():
    """Guard: tool sesi DCS/WCP (dihapus) tidak boleh muncul kembali."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    for nm in [
        "daftar_dcs_sesi",
        "buat_dcs_sesi",
        "dcs_buka_sesi",
        "dcs_tutup_sesi",
        "detail_dcs_sesi",
        "cari_dcs_sesi",
        "perbarui_dcs_sesi",
        "hapus_dcs_sesi",
        "daftar_wcp_sesi",
        "buat_wcp_sesi",
        "wcp_buka_sesi",
        "wcp_tutup_sesi",
        "detail_wcp_sesi",
        "cari_wcp_sesi",
        "perbarui_wcp_sesi",
        "hapus_wcp_sesi",
    ]:
        assert nm not in names, f"tool sesi {nm} seharusnya sudah dihapus"


@pytest.mark.asyncio
async def test_daftar_ts_penugasan():
    payload = {"items": [], "total": 0}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_ts_penugasan", {})
    assert result.data["total"] == 0


@pytest.mark.asyncio
async def test_buat_ts_penugasan():
    payload = {"id": "tpn-baru", "partisipan_id": "par-1", "aktif": True}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("buat_ts_penugasan", {"partisipan_id": "par-1"})
    assert result.data["id"] == "tpn-baru"
    assert "/api/v1/time-study/penugasan" in m.await_args.args[0]
    assert m.await_args.kwargs["body"] == {"partisipan_id": "par-1", "aktif": True}


@pytest.mark.asyncio
async def test_buat_ts_penugasan_banyak():
    payload = {"created": [{"id": "tpn-1"}, {"id": "tpn-2"}], "skipped": []}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_ts_penugasan_banyak", {"partisipan_ids": ["par-1", "par-2"]}
            )
    assert len(result.data["created"]) == 2
    assert m.await_args.args[0] == "/api/v1/time-study/penugasan/bulk"
    assert m.await_args.kwargs["body"] == {
        "partisipan_ids": ["par-1", "par-2"],
        "aktif": True,
    }


@pytest.mark.asyncio
async def test_hapus_ts_penugasan():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("hapus_ts_penugasan", {"penugasan_id": "tpn-1"})
    assert result.data["ok"] is True
    assert "/api/v1/time-study/penugasan/tpn-1" in m.await_args.args[0]


@pytest.mark.asyncio
async def test_ts_buat_log_path_penugasan():
    payload = {"id": "log-1"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "ts_buat_log",
                {
                    "penugasan_id": "tpn-1",
                    "tanggal": "2026-07-01",
                    "waktu_masuk": "07:00",
                    "waktu_keluar": "16:00",
                    "day_color": "green",
                    "menit_core": 100,
                    "menit_character": 10,
                    "menit_improve": 10,
                    "menit_strategic": 10,
                    "menit_admin": 10,
                    "menit_recovery": 10,
                },
            )
    assert result.data["id"] == "log-1"
    assert "/api/v1/time-study/penugasan/tpn-1/log" in m.await_args.args[0]


@pytest.mark.asyncio
async def test_hapus_opm_sesi():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("hapus_opm_sesi", {"sesi_id": "opm-1"})
    assert result.data["ok"] is True
    assert "/api/v1/opm/sesi/opm-1" in m.await_args.args[0]
    assert m.await_args.kwargs["params"] == {"paksa": False}


@pytest.mark.asyncio
async def test_dcs_hapus_responden_tanpa_sesi():
    """dcs_hapus_responden (instrumen singleton) tidak lagi butuh sesi_id."""
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("dcs_hapus_responden", {"responden_id": "r1"})
    assert result.data["ok"] is True
    assert m.await_args.args[0] == "/api/v1/dcs/responden/r1"


@pytest.mark.asyncio
async def test_wcp_hapus_responden_tanpa_sesi():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_hapus_responden", {"responden_id": "r1"})
    assert result.data["ok"] is True
    assert m.await_args.args[0] == "/api/v1/wcp/responden/r1"


@pytest.mark.asyncio
async def test_dcs_hapus_item_path():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("dcs_hapus_item", {"item_id": "D5b"})
    assert result.data["ok"] is True
    assert m.await_args.args[0] == "/api/v1/dcs/sub-skala/items/D5b"


@pytest.mark.asyncio
async def test_wcp_hapus_item_path():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("wcp_hapus_item", {"item_id": "SC1a"})
    assert result.data["ok"] is True
    assert m.await_args.args[0] == "/api/v1/wcp/dimensi/items/SC1a"


@pytest.mark.asyncio
async def test_opm_tambah_responden():
    payload = {"id": "oprs-1", "partisipan_id": "par-1", "jabatan_label": "Guru"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "opm_tambah_responden",
                {"sesi_id": "opm-1", "partisipan_id": "par-1", "jabatan_label": "Guru"},
            )
    assert result.data["id"] == "oprs-1"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/responden"
    assert m.await_args.kwargs["body"] == {
        "partisipan_id": "par-1",
        "jabatan_label": "Guru",
    }


@pytest.mark.asyncio
async def test_opm_tambah_responden_banyak():
    payload = {"created": [{"id": "oprs-1"}], "skipped": []}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "opm_tambah_responden_banyak",
                {"sesi_id": "opm-1", "partisipan_ids": ["par-1"]},
            )
    assert len(result.data["created"]) == 1
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/responden/bulk"
    assert m.await_args.kwargs["body"] == {"partisipan_ids": ["par-1"]}


@pytest.mark.asyncio
async def test_opm_hapus_responden():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_hapus_responden", {"responden_id": "r1"})
    assert result.data["ok"] is True
    assert "/api/v1/opm/sesi/responden/r1" in m.await_args.args[0]


@pytest.mark.asyncio
async def test_daftar_opm_sesi():
    payload = {"items": [{"id": "opm-1", "status": "DRAFT"}], "total": 1}
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_opm_sesi", {})
    assert result.data["items"][0]["status"] == "DRAFT"
    assert m.await_args.args[0] == "/api/v1/opm/sesi"


@pytest.mark.asyncio
async def test_buat_opm_sesi():
    payload = {"id": "opm-baru", "status": "DRAFT"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_opm_sesi",
                {
                    "jabatan_id": "jbt_1",
                    "ti_sesi_id": "tises_1",
                    "periode": "2026-06",
                    "min_responden": 3,
                },
            )
    assert result.data["id"] == "opm-baru"
    assert m.await_args.args[0] == "/api/v1/opm/sesi"
    assert m.await_args.kwargs["body"] == {
        "jabatan_id": "jbt_1",
        "ti_sesi_id": "tises_1",
        "periode": "2026-06",
        "min_responden": 3,
    }


@pytest.mark.asyncio
async def test_cari_opm_sesi():
    payload = {"items": [{"id": "opm-1"}], "total": 1}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("cari_opm_sesi", {"domain": [["status", "=", "OPEN"]]})
    assert result.data["total"] == 1
    assert m.await_args.args[0] == "/api/v1/opm/sesi/search"
    assert m.await_args.kwargs["body"]["domain"] == [["status", "=", "OPEN"]]


@pytest.mark.asyncio
async def test_detail_opm_sesi():
    payload = {"id": "opm-1", "status": "OPEN"}
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("detail_opm_sesi", {"sesi_id": "opm-1"})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1"


@pytest.mark.asyncio
async def test_perbarui_opm_sesi():
    payload = {"id": "opm-1", "catatan": "baru"}
    with patch(_PATCH, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "perbarui_opm_sesi", {"sesi_id": "opm-1", "catatan": "baru"}
            )
    assert result.data["catatan"] == "baru"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1"
    assert m.await_args.kwargs["body"] == {"catatan": "baru"}


@pytest.mark.asyncio
async def test_opm_buka_sesi():
    with patch(_POST, new_callable=AsyncMock, return_value={"status": "OPEN"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_buka_sesi", {"sesi_id": "opm-1"})
    assert result.data["status"] == "OPEN"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/buka"


@pytest.mark.asyncio
async def test_opm_tutup_sesi():
    with patch(_POST, new_callable=AsyncMock, return_value={"status": "CLOSED"}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_tutup_sesi", {"sesi_id": "opm-1"})
    assert result.data["status"] == "CLOSED"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/tutup"


@pytest.mark.asyncio
async def test_opm_daftar_task():
    payload = [{"task_kode": "K001"}]
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_daftar_task", {"sesi_id": "opm-1"})
    assert result.data[0]["task_kode"] == "K001"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/task"


@pytest.mark.asyncio
async def test_opm_daftar_responden():
    payload = [{"id": "oprs-1"}]
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_daftar_responden", {"sesi_id": "opm-1"})
    assert len(result.data) == 1
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/responden"


@pytest.mark.asyncio
async def test_opm_detail_responden():
    payload = {"id": "oprs-1"}
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_detail_responden", {"responden_id": "oprs-1"})
    assert result.data["id"] == "oprs-1"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/responden/oprs-1"


@pytest.mark.asyncio
async def test_opm_submit_jawaban_put_lalu_post():
    """opm_submit_jawaban WAJIB memanggil PUT .../jawaban lalu POST .../jawaban/submit."""
    with (
        patch(_PUT, new_callable=AsyncMock, return_value=[]) as mp,
        patch(_POST, new_callable=AsyncMock, return_value=[{"id": "j1"}]) as mpost,
    ):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "opm_submit_jawaban",
                {
                    "responden_id": "oprs-1",
                    "jawaban": [
                        {
                            "task_kode": "K001",
                            "importance": 4,
                            "frequency": 3,
                            "criticality": 5,
                        }
                    ],
                },
            )
    assert result.data[0]["id"] == "j1"
    assert mp.await_args.args[0] == "/api/v1/opm/sesi/responden/oprs-1/jawaban"
    assert mp.await_args.kwargs["body"] == {
        "jawaban": [{"task_kode": "K001", "importance": 4, "frequency": 3, "criticality": 5}]
    }
    assert mpost.await_args.args[0] == "/api/v1/opm/sesi/responden/oprs-1/jawaban/submit"


@pytest.mark.asyncio
async def test_opm_daftar_jawaban():
    payload = [{"id": "j1", "task_kode": "K001"}]
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_daftar_jawaban", {"responden_id": "oprs-1"})
    assert result.data[0]["task_kode"] == "K001"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/responden/oprs-1/jawaban"


@pytest.mark.asyncio
async def test_opm_analisis():
    payload = {"sesi_id": "opm-1", "status": "ANALYZED"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_analisis", {"sesi_id": "opm-1"})
    assert result.data["status"] == "ANALYZED"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/analisis"


@pytest.mark.asyncio
async def test_opm_hasil():
    payload = {"sesi_id": "opm-1", "tasks": []}
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_hasil", {"sesi_id": "opm-1"})
    assert result.data["sesi_id"] == "opm-1"
    assert m.await_args.args[0] == "/api/v1/opm/sesi/opm-1/hasil"


@pytest.mark.asyncio
async def test_opm_kuesioner_saya():
    payload = [{"sesi_id": "opm-1"}]
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("opm_kuesioner_saya", {})
    assert len(result.data) == 1
    assert m.await_args.args[0] == "/api/v1/opm/kuesioner/saya"


@pytest.mark.asyncio
async def test_partisipan_saya():
    payload = {"id": "par-1", "nama": "Budi"}
    with patch(_GET, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("partisipan_saya", {})
    assert result.data["id"] == "par-1"
    assert m.await_args.args[0] == "/api/v1/partisipan/saya"


@pytest.mark.asyncio
async def test_ti_catalog_purge():
    payload = {"deleted": {"uraian_tugas": 10, "detil_tugas": 3, "tugas_pokok": 2}}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("ti_catalog_purge", {})
    assert result.data == payload
    assert "/api/v1/task-inventory/catalog/purge" in m.await_args.args[0]


@pytest.mark.asyncio
async def test_ti_catalog_reseed():
    payload = {"created": {"jabatan": 5, "tugas_pokok": 2, "detil_tugas": 3, "uraian_tugas": 10}}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("ti_catalog_reseed", {})
    assert result.data == payload
    assert "/api/v1/task-inventory/catalog/reseed" in m.await_args.args[0]


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
        # DCS/WCP — instrumen singleton (tanpa sesi)
        "dcs_instrumen",
        "dcs_perbarui_instrumen",
        "dcs_tutup_instrumen",
        "dcs_buka_ulang_instrumen",
        "dcs_reset_instrumen",
        "dcs_daftar_responden",
        "dcs_tambah_responden",
        "dcs_analisis",
        "dcs_hasil",
        "dcs_submit_jawaban",
        "wcp_instrumen",
        "wcp_perbarui_instrumen",
        "wcp_tutup_instrumen",
        "wcp_buka_ulang_instrumen",
        "wcp_reset_instrumen",
        "wcp_daftar_responden",
        "wcp_tambah_responden",
        "wcp_analisis",
        "wcp_hasil",
        "wcp_submit_jawaban",
        "ts_buat_log",
        "info_saya",
        # Katalog Task Inventory baru
        "daftar_tugas_pokok",
        "buat_tugas_pokok",
        "cari_tugas_pokok",
        "detail_tugas_pokok",
        "perbarui_tugas_pokok",
        "hapus_tugas_pokok",
        "daftar_detil_tugas",
        "buat_detil_tugas",
        "cari_detil_tugas",
        "detail_detil_tugas",
        "perbarui_detil_tugas",
        "hapus_detil_tugas",
        "daftar_uraian_tugas",
        "buat_uraian_tugas",
        "cari_uraian_tugas",
        "detail_uraian_tugas",
        "perbarui_uraian_tugas",
        "hapus_uraian_tugas",
        "ti_catalog_purge",
        "ti_catalog_reseed",
        # OPM (CRUD sesi + alur pengisian lengkap)
        "daftar_opm_sesi",
        "buat_opm_sesi",
        "cari_opm_sesi",
        "detail_opm_sesi",
        "perbarui_opm_sesi",
        "hapus_opm_sesi",
        "opm_buka_sesi",
        "opm_tutup_sesi",
        "opm_daftar_task",
        "opm_daftar_responden",
        "opm_detail_responden",
        "opm_tambah_responden",
        "opm_tambah_responden_banyak",
        "opm_hapus_responden",
        "opm_submit_jawaban",
        "opm_daftar_jawaban",
        "opm_analisis",
        "opm_hasil",
        "opm_kuesioner_saya",
        "partisipan_saya",
        # Time Study (penugasan per partisipan, bukan sesi)
        "daftar_ts_penugasan",
        "buat_ts_penugasan",
        "detail_ts_penugasan",
        "perbarui_ts_penugasan",
        "hapus_ts_penugasan",
        "ts_kuesioner_saya",
    ]:
        assert nm in names, f"tool {nm} tidak terdaftar"
    assert len(names) >= 158


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
    """PUT (draft-save) lalu POST .../submit — dua panggilan backend, bukan satu."""
    jawaban_final = [{"item_id": "D1a", "skor_raw": 4}]
    with (
        patch(_PUT, new_callable=AsyncMock, return_value=jawaban_final) as m_put,
        patch(_POST, new_callable=AsyncMock, return_value=jawaban_final) as m_post,
    ):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "dcs_submit_jawaban",
                {"responden_id": "r1", "jawaban": jawaban_final},
            )
    assert m_put.await_args.kwargs["body"]["jawaban"][0]["item_id"] == "D1a"
    assert m_put.await_args.args[0] == "/api/v1/dcs/responden/r1/jawaban"
    assert m_post.await_args.args[0] == "/api/v1/dcs/responden/r1/jawaban/submit"
    assert result.data == jawaban_final


@pytest.mark.asyncio
async def test_wcp_submit_jawaban():
    jawaban_final = [{"item_id": "SC1a", "skor_raw": 3}]
    with (
        patch(_PUT, new_callable=AsyncMock, return_value=jawaban_final) as m_put,
        patch(_POST, new_callable=AsyncMock, return_value=jawaban_final) as m_post,
    ):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "wcp_submit_jawaban",
                {"responden_id": "r1", "jawaban": jawaban_final},
            )
    assert m_put.await_args.args[0] == "/api/v1/wcp/responden/r1/jawaban"
    assert m_post.await_args.args[0] == "/api/v1/wcp/responden/r1/jawaban/submit"
    assert result.data == jawaban_final


@pytest.mark.asyncio
async def test_ti_submit_detail():
    detail_final = [{"task_kode": "TI001", "sumber_bukti": "Formal"}]
    with (
        patch(_PUT, new_callable=AsyncMock, return_value=detail_final) as m_put,
        patch(_POST, new_callable=AsyncMock, return_value=detail_final) as m_post,
    ):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "ti_submit_detail",
                {"responden_id": "r1", "detail": detail_final},
            )
    assert m_put.await_args.args[0] == "/api/v1/task-inventory/sesi/responden/r1/detail"
    assert m_post.await_args.args[0] == "/api/v1/task-inventory/sesi/responden/r1/detail/submit"
    assert result.data == detail_final


# ── Katalog Task Inventory (TugasPokok, DetilTugas, UraianTugas) ──────────────


@pytest.mark.asyncio
async def test_daftar_tugas_pokok():
    payload = {"items": [{"id": "tp-1", "jabatan_id": "jbt_1", "nama": "Mengajar"}], "total": 1}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_tugas_pokok", {})
    assert result.data["total"] == 1
    assert result.data["items"][0]["nama"] == "Mengajar"


@pytest.mark.asyncio
async def test_buat_tugas_pokok():
    payload = {"id": "tp-baru", "jabatan_ids": ["jbt_1"], "nama": "Mengajar Matematika"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_tugas_pokok",
                {"jabatan_ids": ["jbt_1"], "nama": "Mengajar Matematika"},
            )
    assert result.data["id"] == "tp-baru"
    assert m.await_args.kwargs["body"]["jabatan_ids"] == ["jbt_1"]


@pytest.mark.asyncio
async def test_hapus_tugas_pokok():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("hapus_tugas_pokok", {"tp_id": "tp-1"})
    assert result.data["ok"] is True
    assert "/api/v1/task-inventory/tugas-pokok/tp-1" in m.await_args.args[0]


@pytest.mark.asyncio
async def test_daftar_detil_tugas():
    payload = {"items": [{"id": "dt-1", "kode": "DT-001", "nama": "Menyiapkan RPP"}], "total": 1}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_detil_tugas", {})
    assert result.data["items"][0]["kode"] == "DT-001"


@pytest.mark.asyncio
async def test_buat_detil_tugas():
    payload = {"id": "dt-baru", "nama": "Menyiapkan Silabus", "jabatan_ids": ["jbt_1"]}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_detil_tugas",
                {"nama": "Menyiapkan Silabus", "tugas_pokok_id": "tp-1", "jabatan_ids": ["jbt_1"]},
            )
    assert result.data["id"] == "dt-baru"
    assert m.await_args.kwargs["body"]["tugas_pokok_id"] == "tp-1"
    assert m.await_args.kwargs["body"]["jabatan_ids"] == ["jbt_1"]


@pytest.mark.asyncio
async def test_perbarui_detil_tugas_hanya_field_terisi():
    """Body PATCH hanya memuat field non-None."""
    with patch(_PATCH, new_callable=AsyncMock, return_value={"id": "dt-1"}) as m:
        async with Client(mcp) as client:
            await client.call_tool("perbarui_detil_tugas", {"dt_id": "dt-1", "nama": "Baru"})
    body = m.await_args.kwargs["body"]
    assert body == {"nama": "Baru"}


@pytest.mark.asyncio
async def test_daftar_uraian_tugas():
    payload = {"items": [{"id": "ut-1", "kode": "UT-001", "nama": "Menulis RPP"}], "total": 1}
    with patch(_GET, new_callable=AsyncMock, return_value=payload):
        async with Client(mcp) as client:
            result = await client.call_tool("daftar_uraian_tugas", {})
    assert result.data["items"][0]["kode"] == "UT-001"


@pytest.mark.asyncio
async def test_buat_uraian_tugas():
    payload = {"id": "ut-baru", "kode": "UT-002", "uraian": "Menyusun KD"}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "buat_uraian_tugas",
                {
                    "kode": "UT-002",
                    "uraian": "Menyusun KD",
                    "unit": "SMP",
                    "urutan": 1,
                    "tugas_pokok_id": "tp-1",
                    "jabatan_id": "jbt_1",
                    "detil_tugas_id": "dt-1",
                },
            )
    assert result.data["id"] == "ut-baru"
    assert m.await_args.kwargs["body"]["tugas_pokok_id"] == "tp-1"
    assert m.await_args.kwargs["body"]["jabatan_id"] == "jbt_1"


@pytest.mark.asyncio
async def test_cari_uraian_tugas():
    payload = {"items": [], "total": 0}
    with patch(_POST, new_callable=AsyncMock, return_value=payload) as m:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "cari_uraian_tugas",
                {"domain": [["detil_tugas_id", "=", "dt-1"]]},
            )
    assert result.data["total"] == 0
    assert m.await_args.kwargs["body"]["domain"] == [["detil_tugas_id", "=", "dt-1"]]


@pytest.mark.asyncio
async def test_hapus_uraian_tugas():
    with patch(_DELETE, new_callable=AsyncMock, return_value={"ok": True}) as m:
        async with Client(mcp) as client:
            result = await client.call_tool("hapus_uraian_tugas", {"ut_id": "ut-1"})
    assert result.data["ok"] is True
    assert "/api/v1/task-inventory/uraian-tugas/ut-1" in m.await_args.args[0]
