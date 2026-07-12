"""Definisi MCP Server (FastMCP) ANJAB-ABK + tools per domain.

Auth pintu depan dipilih berdasarkan konfigurasi (lihat config.py):
  - Authentik OAuth Pola B (Claude.ai): aktif bila AUTHENTIK_ISSUER_URL +
    AUTHENTIK_CLIENT_* + MCP_BASE_URL diisi. Token user Authentik diteruskan
    ke backend (lihat client.py).
  - API Key (VS Code/CLI): aktif bila MCP_API_KEY diisi. Backend diakses via
    BACKEND_API_TOKEN dari config (service account).
  - Tanpa konfigurasi: tanpa auth (hanya untuk stdio / jaringan lokal).

Tools dikelompokkan per domain:
  - core:           jenjang pendidikan, sekolah, jabatan, partisipan, SME panel
  - task_inventory: sesi TI (3 tahap), responden, hasil
  - dcs:            sesi DCS, responden, hasil
  - wcp:            sesi WCP, responden, hasil
  - opm:            sesi OPM (delete-only; sisa domain — lihat rencana-opm.md)
  - time_study:     penugasan TS per partisipan, log harian, kuesioner
"""

from __future__ import annotations

import logging

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from . import __version__
from .client import (
    BackendError,
    backend_delete,
    backend_get,
    backend_patch,
    backend_post,
    backend_put,
)
from .config import settings

logger = logging.getLogger(__name__)

# ── Pemilihan auth pintu depan ────────────────────────────────────────────────
_auth = None
_authentik_aktif = bool(
    settings.authentik_issuer_url
    and settings.authentik_client_id
    and settings.authentik_client_secret
    and settings.mcp_base_url
)

if _authentik_aktif:
    from fastmcp.server.auth import MultiAuth

    from .auth_provider import AuthentikProvider, BearerApiKeyVerifier

    logger.info("OAuth Authentik Pola B AKTIF — issuer: %s", settings.authentik_issuer_url)
    _provider = AuthentikProvider(
        authentik_issuer_url=settings.authentik_issuer_url,
        client_id=settings.authentik_client_id,
        client_secret=settings.authentik_client_secret,
        base_url=settings.mcp_base_url,
        allowed_usernames=settings.authentik_allowed_usernames,
        require_authorization_consent="external",
    )
    if settings.mcp_api_key:
        logger.info("API Key AKTIF (MultiAuth: Authentik Pola B + API Key)")
        _auth = MultiAuth(
            server=_provider,
            verifiers=[BearerApiKeyVerifier(api_key=settings.mcp_api_key)],
        )
    else:
        _auth = _provider

elif settings.mcp_api_key:
    from fastmcp.server.auth import MultiAuth

    from .auth_provider import BearerApiKeyVerifier

    logger.info("API Key AKTIF (tanpa OAuth)")
    _auth = MultiAuth(verifiers=[BearerApiKeyVerifier(api_key=settings.mcp_api_key)])

else:
    logger.warning(
        "Tidak ada auth dikonfigurasi — server terbuka. Isi AUTHENTIK_ISSUER_URL + "
        "AUTHENTIK_CLIENT_* + MCP_BASE_URL untuk deployment Claude Web."
    )

mcp = FastMCP(name=settings.mcp_server_name, auth=_auth)


# ── Helper ────────────────────────────────────────────────────────────────────
def _raise_tool_error(exc: BackendError) -> None:
    """Konversi BackendError menjadi ToolError dengan pesan yang aman ditampilkan."""
    raise ToolError(str(exc)) from exc


# ── Resource: versi server ────────────────────────────────────────────────────
@mcp.resource("config://version")
def versi_server() -> str:
    """Versi MCP server yang sedang berjalan."""
    return __version__


# ════════════════════════════════════════════════════════════════════════════════
# DOMAIN: CORE — jenjang pendidikan, sekolah, jabatan, partisipan, SME panel
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def daftar_jenjang_pendidikan(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar jenjang pendidikan (PAUD, TK, SD, SMP, SMA, SMK, dll.).

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list jenjang) dan ``total`` (total record).
    """
    try:
        return await backend_get("/api/v1/jenjang-pendidikan", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def daftar_sekolah(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar sekolah (satuan pendidikan) yang terdaftar dalam sistem.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list sekolah) dan ``total`` (total record).
    """
    try:
        return await backend_get("/api/v1/sekolah", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_sekolah(
    ctx: Context,
    nama: str,
    jenjang_pendidikan_id: str,
    npsn: str | None = None,
    kota: str | None = None,
    provinsi: str | None = None,
) -> dict:
    """Buat data sekolah (satuan pendidikan) baru.

    Args:
        nama: Nama lengkap sekolah.
        jenjang_pendidikan_id: UUID jenjang pendidikan (dari ``daftar_jenjang_pendidikan``).
        npsn: Nomor Pokok Sekolah Nasional (opsional).
        kota: Nama kota lokasi sekolah (opsional).
        provinsi: Nama provinsi lokasi sekolah (opsional).

    Returns:
        Data sekolah yang baru dibuat termasuk ``id`` (UUID).
    """
    body = {
        "nama": nama,
        "jenjang_pendidikan_id": jenjang_pendidikan_id,
    }
    if npsn is not None:
        body["npsn"] = npsn
    if kota is not None:
        body["kota"] = kota
    if provinsi is not None:
        body["provinsi"] = provinsi
    try:
        return await backend_post("/api/v1/sekolah", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def daftar_jabatan(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar jabatan yang terdaftar dalam sistem ANJAB.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list jabatan) dan ``total`` (total record).
        Tiap jabatan memuat ``id``, ``kode``, ``nama``, ``jenis``, dan
        ``unit_kerja_id`` (bila terikat ke unit kerja/sekolah).
    """
    try:
        return await backend_get("/api/v1/jabatan", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_jabatan(
    ctx: Context,
    kode: str,
    nama: str,
    jenis: str,
    unit_kerja_id: str | None = None,
    deskripsi: str | None = None,
) -> dict:
    """Buat data jabatan baru untuk keperluan ANJAB.

    Args:
        kode: Kode unik jabatan (mis. ``KS-001`` untuk Kepala Sekolah).
        nama: Nama lengkap jabatan.
        jenis: Jenis jabatan, mis. ``struktural``, ``fungsional``, atau ``pendukung``.
        unit_kerja_id: UUID unit kerja/sekolah tempat jabatan ini bernaung (opsional).
        deskripsi: Deskripsi singkat jabatan (opsional).

    Returns:
        Data jabatan yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"kode": kode, "nama": nama, "jenis": jenis}
    if unit_kerja_id is not None:
        body["unit_kerja_id"] = unit_kerja_id
    if deskripsi is not None:
        body["deskripsi"] = deskripsi
    try:
        return await backend_post("/api/v1/jabatan", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def daftar_partisipan(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar partisipan (pegawai) yang terdaftar dalam sistem.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list partisipan) dan ``total`` (total record).
    """
    try:
        return await backend_get("/api/v1/partisipan", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_partisipan(
    ctx: Context,
    nama: str,
    email: str,
    sekolah_id: str,
    jabatan_utama_id: str,
    masa_kerja_tahun: int,
    masa_kerja_bulan: int = 0,
) -> dict:
    """Daftarkan partisipan (pegawai) baru ke dalam sistem.

    Args:
        nama: Nama lengkap partisipan.
        email: Alamat email partisipan (dipakai untuk akun Authentik).
        sekolah_id: UUID sekolah tempat partisipan bertugas.
        jabatan_utama_id: UUID jabatan utama partisipan.
        masa_kerja_tahun: Masa kerja dalam tahun.
        masa_kerja_bulan: Masa kerja tambahan dalam bulan (0-11, default 0).

    Returns:
        Data partisipan yang baru dibuat termasuk ``id`` (UUID) dan akun
        Authentik yang otomatis dibuat bila konfigurasi Authentik Admin API aktif.
    """
    body: dict = {
        "nama": nama,
        "email": email,
        "sekolah_id": sekolah_id,
        "jabatan_utama_id": jabatan_utama_id,
        "masa_kerja_tahun": masa_kerja_tahun,
        "masa_kerja_bulan": masa_kerja_bulan,
    }
    try:
        return await backend_post("/api/v1/partisipan", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def daftar_sme_panel(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar SME Panel (Subject Matter Expert Panel) yang terdaftar.

    SME Panel adalah kelompok ahli yang memvalidasi Task Inventory. Setiap panel
    terikat ke satu jabatan dan memiliki sejumlah anggota (partisipan).

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list SME panel) dan ``total`` (total record).
    """
    try:
        return await backend_get("/api/v1/sme-panel", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_sme_panel(ctx: Context, panel_id: str) -> dict:
    """Ambil detail SME Panel beserta daftar anggotanya.

    Args:
        panel_id: UUID SME Panel (dari ``daftar_sme_panel``).

    Returns:
        Dict berisi data panel dan key ``anggota`` (list partisipan anggota).
    """
    try:
        panel = await backend_get(f"/api/v1/sme-panel/{panel_id}", ctx=ctx)
        anggota = await backend_get(f"/api/v1/sme-panel/{panel_id}/anggota", ctx=ctx)
        return {**panel, "anggota": anggota}
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def tambah_anggota_sme_panel(
    ctx: Context,
    panel_id: str,
    partisipan_id: str,
) -> dict:
    """Tambahkan partisipan sebagai anggota SME Panel.

    Partisipan dapat ditambahkan ke panel mana pun tanpa harus memiliki jabatan
    yang cocok dengan panel tersebut. Satu-satunya batasan adalah partisipan
    belum menjadi anggota panel yang sama.

    Args:
        panel_id: UUID SME Panel.
        partisipan_id: UUID partisipan yang akan ditambahkan.

    Returns:
        Konfirmasi penambahan anggota.
    """
    try:
        return await backend_post(
            f"/api/v1/sme-panel/{panel_id}/anggota",
            ctx=ctx,
            body={"partisipan_id": partisipan_id},
        )
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# DOMAIN: TASK INVENTORY (TI) — alat ukur berbasis task selection 3 tahap
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def daftar_ti_sesi(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar sesi Task Inventory (TI) yang ada dalam sistem.

    Sesi TI memiliki alur 3 tahap: DRAFT → TAHAP1 → TAHAP2 → TAHAP3 →
    CLOSED → ANALYZED. Setiap sesi mencakup kategori jabatan dan periode studi.
    Field ``unit`` bersifat opsional — sesi lintas-unit tidak memiliki unit kerja
    spesifik.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list sesi TI) dan ``total`` (total record).
    """
    try:
        return await backend_get("/api/v1/task-inventory/sesi", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_ti_sesi(ctx: Context, sesi_id: str) -> dict:
    """Ambil detail sesi Task Inventory termasuk status, unit, kategori, dan koordinator.

    Args:
        sesi_id: UUID sesi TI (dari ``daftar_ti_sesi``).

    Returns:
        Detail sesi TI termasuk status saat ini dan metadata studi.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/sesi/{sesi_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_ti_sesi(
    ctx: Context,
    jabatan_id: str,
    periode: str,
    unit: str | None = None,
    koordinator_id: str | None = None,
    catatan: str | None = None,
) -> dict:
    """Buat sesi Task Inventory baru (status awal: DRAFT).

    Args:
        jabatan_id: ID jabatan yang dikaji (FK ke Jabatan). Gunakan
            ``ti_catalog_kombinasi`` untuk melihat jabatan_id yang tersedia.
        periode: Periode kajian format ``YYYY-MM``, mis. ``2026-06``.
        unit: Unit/jenjang yang dikaji (TK/SD/SMP/SMA). Opsional —
            bila tidak diisi, sesi berlaku lintas unit.
        koordinator_id: UUID partisipan yang menjadi koordinator SME panel
            (reviewer Tahap 2). Opsional saat buat, wajib saat mulai Tahap 2.
        catatan: Catatan tambahan untuk sesi ini (opsional).

    Returns:
        Data sesi TI yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"jabatan_id": jabatan_id, "periode": periode}
    if unit is not None:
        body["unit"] = unit
    if koordinator_id is not None:
        body["koordinator_id"] = koordinator_id
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_post("/api/v1/task-inventory/sesi", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_tambah_responden(
    ctx: Context,
    sesi_id: str,
    partisipan_id: str | None = None,
    nama: str | None = None,
) -> dict:
    """Tambahkan responden (anggota SME panel) ke sesi Task Inventory.

    Minimal satu dari ``partisipan_id`` atau ``nama`` harus diisi.

    Catatan: bila sesi memiliki ``jabatan_id`` dan ``partisipan_id`` diisi,
    partisipan tersebut wajib menjadi anggota SME panel untuk jabatan yang
    dikaitkan ke sesi. Backend akan menolak permintaan bila syarat ini tidak
    terpenuhi.

    Args:
        sesi_id: UUID sesi TI.
        partisipan_id: UUID partisipan terdaftar (opsional bila ``nama`` diisi).
        nama: Nama responden eksternal (bila belum terdaftar sebagai partisipan).

    Returns:
        Data responden yang ditambahkan termasuk ``id`` (UUID responden).
    """
    body: dict = {}
    if partisipan_id is not None:
        body["partisipan_id"] = partisipan_id
    if nama is not None:
        body["nama"] = nama
    if not body:
        raise ToolError("Minimal isi 'partisipan_id' atau 'nama'")
    try:
        return await backend_post(
            f"/api/v1/task-inventory/sesi/{sesi_id}/responden", ctx=ctx, body=body
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_mulai_tahap1(ctx: Context, sesi_id: str) -> dict:
    """Mulai Tahap 1 sesi TI: anggota SME panel mulai memilih task relevan.

    Transisi status: DRAFT → TAHAP1. Setelah ini, responden dapat mengakses
    kuesioner Tahap 1 via ``GET /api/v1/task-inventory/kuesioner/saya``.

    Args:
        sesi_id: UUID sesi TI yang akan dimulai Tahap 1-nya.

    Returns:
        Data sesi TI yang sudah diperbarui dengan status ``TAHAP1``.
    """
    try:
        return await backend_post(
            f"/api/v1/task-inventory/sesi/{sesi_id}/mulai-tahap1", ctx=ctx, body={}
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_mulai_tahap2(ctx: Context, sesi_id: str, paksa: bool = False) -> dict:
    """Mulai Tahap 2 sesi TI: koordinator mereview task yang tidak dipilih unanimously.

    Transisi status: TAHAP1 → TAHAP2. Koordinator mengakses review via
    ``GET /api/v1/task-inventory/sesi/{sesi_id}/tahap2``.

    Args:
        sesi_id: UUID sesi TI.
        paksa: Bila True, paksa transisi meski jumlah responden belum memenuhi minimal.

    Returns:
        Data sesi TI yang sudah diperbarui dengan status ``TAHAP2``.
    """
    try:
        return await backend_post(
            f"/api/v1/task-inventory/sesi/{sesi_id}/mulai-tahap2",
            ctx=ctx,
            params={"paksa": paksa},
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_mulai_tahap3(ctx: Context, sesi_id: str, paksa: bool = False) -> dict:
    """Mulai Tahap 3 sesi TI: anggota mengisi detail CalHR per task terpilih.

    Transisi status: TAHAP2 → TAHAP3. Task final di-freeze:
    ``final = unanimous ∪ disetujui koordinator``.

    Args:
        sesi_id: UUID sesi TI.
        paksa: Bila True, paksa transisi meski review koordinator belum lengkap.

    Returns:
        Data sesi TI yang sudah diperbarui dengan status ``TAHAP3``.
    """
    try:
        return await backend_post(
            f"/api/v1/task-inventory/sesi/{sesi_id}/mulai-tahap3",
            ctx=ctx,
            params={"paksa": paksa},
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_task_terpilih(ctx: Context, sesi_id: str) -> list:
    """Ambil daftar task yang terpilih (final) untuk sesi TI.

    Task final = unanimous (semua anggota pilih) ∪ disetujui koordinator Tahap 2.
    Tersedia setelah transisi ke TAHAP3 atau CLOSED.

    Args:
        sesi_id: UUID sesi TI.

    Returns:
        Dict berisi list task yang terpilih beserta detail CalHR (bila sudah diisi).
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/sesi/{sesi_id}/task-terpilih", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_analisis(ctx: Context, sesi_id: str) -> dict:
    """Ambil hasil analisis Task Inventory untuk sesi yang sudah selesai.

    Menjalankan agregasi CalHR per task dan menghitung metrik ABK.
    Tersedia setelah sesi berstatus CLOSED.

    Args:
        sesi_id: UUID sesi TI.

    Returns:
        Hasil analisis termasuk frekuensi, waktu per task, dan total beban kerja.
    """
    try:
        return await backend_post(f"/api/v1/task-inventory/sesi/{sesi_id}/analisis", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_tutup_sesi(ctx: Context, sesi_id: str) -> dict:
    """Tutup sesi Task Inventory (transisi ke CLOSED).

    Menutup pengisian; setelah ini sesi siap dianalisis (``ti_analisis``).

    Args:
        sesi_id: UUID sesi TI.

    Returns:
        Data sesi TI dengan status ``CLOSED``.
    """
    try:
        return await backend_post(f"/api/v1/task-inventory/sesi/{sesi_id}/tutup", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_hasil(ctx: Context, sesi_id: str) -> dict:
    """Ambil hasil final Task Inventory sesi yang sudah dianalisis.

    Args:
        sesi_id: UUID sesi TI.

    Returns:
        Hasil final TI termasuk daftar task, agregasi CalHR, dan interpretasi ABK.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/sesi/{sesi_id}/hasil", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# DOMAIN: DCS (Dimension Classification Survey)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def daftar_dcs_sesi(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar sesi DCS (Dimension Classification Survey).

    DCS mengukur persepsi pegawai terhadap dimensi kompetensi jabatan.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list sesi DCS) dan ``total`` (total record).
    """
    try:
        return await backend_get("/api/v1/dcs/sesi", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_dcs_sesi(
    ctx: Context,
    periode: str,
    catatan: str | None = None,
) -> dict:
    """Buat sesi DCS baru (status awal: DRAFT).

    Args:
        periode: Periode studi, mis. ``2025/2026``.
        catatan: Catatan tambahan (opsional).

    Returns:
        Data sesi DCS yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"periode": periode}
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_post("/api/v1/dcs/sesi", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_buka_sesi(ctx: Context, sesi_id: str) -> dict:
    """Buka sesi DCS agar partisipan dapat mengisi kuesioner.

    Transisi status: DRAFT → OPEN.

    Args:
        sesi_id: UUID sesi DCS.

    Returns:
        Data sesi DCS yang sudah diperbarui dengan status ``OPEN``.
    """
    try:
        return await backend_post(f"/api/v1/dcs/sesi/{sesi_id}/buka", ctx=ctx, body={})
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_tutup_sesi(ctx: Context, sesi_id: str) -> dict:
    """Tutup sesi DCS (tidak ada pengisian baru setelah ini).

    Transisi status: OPEN → CLOSED.

    Args:
        sesi_id: UUID sesi DCS.

    Returns:
        Data sesi DCS yang sudah diperbarui dengan status ``CLOSED``.
    """
    try:
        return await backend_post(f"/api/v1/dcs/sesi/{sesi_id}/tutup", ctx=ctx, body={})
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_tambah_responden(
    ctx: Context,
    sesi_id: str,
    jabatan_label: str,
    partisipan_id: str | None = None,
    nama: str | None = None,
) -> dict:
    """Assign partisipan sebagai responden sesi DCS.

    Args:
        sesi_id: UUID sesi DCS.
        jabatan_label: Label jabatan responden untuk keperluan display kuesioner.
        partisipan_id: UUID partisipan terdaftar (opsional).
        nama: Nama responden eksternal (opsional bila ``partisipan_id`` diisi).

    Returns:
        Data responden DCS yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"jabatan_label": jabatan_label}
    if partisipan_id is not None:
        body["partisipan_id"] = partisipan_id
    if nama is not None:
        body["nama"] = nama
    try:
        return await backend_post(f"/api/v1/dcs/sesi/{sesi_id}/responden", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_analisis(ctx: Context, sesi_id: str, wcp_sesi_id: str | None = None) -> dict:
    """Jalankan dan ambil hasil analisis sesi DCS.

    Tersedia setelah sesi berstatus CLOSED.

    Args:
        sesi_id: UUID sesi DCS.
        wcp_sesi_id: UUID sesi WCP pendamping (opsional) untuk analisis gabungan
            kompleksitas–beban.

    Returns:
        Hasil analisis DCS per sub-skala dan agregasi keseluruhan.
    """
    params = {"wcp_sesi_id": wcp_sesi_id} if wcp_sesi_id is not None else None
    try:
        return await backend_post(f"/api/v1/dcs/sesi/{sesi_id}/analisis", ctx=ctx, params=params)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_hasil(ctx: Context, sesi_id: str, wcp_sesi_id: str | None = None) -> dict:
    """Ambil hasil final DCS sesi yang sudah dianalisis.

    Args:
        sesi_id: UUID sesi DCS.
        wcp_sesi_id: UUID sesi WCP pendamping (opsional) untuk hasil gabungan.

    Returns:
        Hasil final DCS termasuk skor per dimensi dan interpretasi.
    """
    params: dict = {}
    if wcp_sesi_id is not None:
        params["wcp_sesi_id"] = wcp_sesi_id
    try:
        return await backend_get(f"/api/v1/dcs/sesi/{sesi_id}/hasil", ctx=ctx, **params)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# DOMAIN: WCP (Work Characteristics Profile)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def daftar_wcp_sesi(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar sesi WCP (Work Characteristics Profile).

    WCP mengukur profil karakteristik pekerjaan yang dibutuhkan suatu jabatan.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list sesi WCP) dan ``total`` (total record).
    """
    try:
        return await backend_get("/api/v1/wcp/sesi", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_wcp_sesi(
    ctx: Context,
    periode: str,
    catatan: str | None = None,
) -> dict:
    """Buat sesi WCP baru (status awal: DRAFT).

    Args:
        periode: Periode studi, mis. ``2025/2026``.
        catatan: Catatan tambahan (opsional).

    Returns:
        Data sesi WCP yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"periode": periode}
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_post("/api/v1/wcp/sesi", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_buka_sesi(ctx: Context, sesi_id: str) -> dict:
    """Buka sesi WCP agar partisipan dapat mengisi kuesioner.

    Transisi status: DRAFT → OPEN.

    Args:
        sesi_id: UUID sesi WCP.

    Returns:
        Data sesi WCP yang sudah diperbarui dengan status ``OPEN``.
    """
    try:
        return await backend_post(f"/api/v1/wcp/sesi/{sesi_id}/buka", ctx=ctx, body={})
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_tutup_sesi(ctx: Context, sesi_id: str) -> dict:
    """Tutup sesi WCP (tidak ada pengisian baru setelah ini).

    Transisi status: OPEN → CLOSED.

    Args:
        sesi_id: UUID sesi WCP.

    Returns:
        Data sesi WCP yang sudah diperbarui dengan status ``CLOSED``.
    """
    try:
        return await backend_post(f"/api/v1/wcp/sesi/{sesi_id}/tutup", ctx=ctx, body={})
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_tambah_responden(
    ctx: Context,
    sesi_id: str,
    jabatan_label: str,
    partisipan_id: str | None = None,
    nama: str | None = None,
) -> dict:
    """Assign partisipan sebagai responden sesi WCP.

    Args:
        sesi_id: UUID sesi WCP.
        jabatan_label: Label jabatan responden untuk keperluan display kuesioner.
        partisipan_id: UUID partisipan terdaftar (opsional).
        nama: Nama responden eksternal (opsional bila ``partisipan_id`` diisi).

    Returns:
        Data responden WCP yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"jabatan_label": jabatan_label}
    if partisipan_id is not None:
        body["partisipan_id"] = partisipan_id
    if nama is not None:
        body["nama"] = nama
    try:
        return await backend_post(f"/api/v1/wcp/sesi/{sesi_id}/responden", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_analisis(ctx: Context, sesi_id: str) -> dict:
    """Jalankan dan ambil hasil analisis sesi WCP.

    Tersedia setelah sesi berstatus CLOSED.

    Args:
        sesi_id: UUID sesi WCP.

    Returns:
        Hasil analisis WCP per dimensi dan agregasi keseluruhan.
    """
    try:
        return await backend_post(f"/api/v1/wcp/sesi/{sesi_id}/analisis", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_hasil(ctx: Context, sesi_id: str) -> dict:
    """Ambil hasil final WCP sesi yang sudah dianalisis.

    Args:
        sesi_id: UUID sesi WCP.

    Returns:
        Hasil final WCP termasuk profil karakteristik per dimensi.
    """
    try:
        return await backend_get(f"/api/v1/wcp/sesi/{sesi_id}/hasil", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# CORE — JENJANG PENDIDIKAN (lengkap: create/search/get/update/delete)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def buat_jenjang_pendidikan(
    ctx: Context,
    kode: str,
    nama: str,
    urutan: int = 0,
    aktif: bool = True,
) -> dict:
    """Buat jenjang pendidikan baru (mis. PAUD, TK, SD, SMP, SMA, SMK).

    Args:
        kode: Kode unik jenjang (mis. ``SD``, ``SMP``).
        nama: Nama jenjang pendidikan.
        urutan: Urutan tampil (semakin kecil semakin awal, default 0).
        aktif: Status aktif (default True).

    Returns:
        Data jenjang pendidikan yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"kode": kode, "nama": nama, "urutan": urutan, "aktif": aktif}
    try:
        return await backend_post("/api/v1/jenjang-pendidikan", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_jenjang_pendidikan(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari jenjang pendidikan dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["nama", "ilike", "dasar"]]``.
        order: Urutan, mis. ``[["urutan", "asc"]]``.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/jenjang-pendidikan/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_jenjang_pendidikan(ctx: Context, jp_id: str) -> dict:
    """Ambil satu jenjang pendidikan berdasarkan ID.

    Args:
        jp_id: UUID jenjang pendidikan.

    Returns:
        Data jenjang pendidikan.
    """
    try:
        return await backend_get(f"/api/v1/jenjang-pendidikan/{jp_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_jenjang_pendidikan(
    ctx: Context,
    jp_id: str,
    kode: str | None = None,
    nama: str | None = None,
    urutan: int | None = None,
    aktif: bool | None = None,
) -> dict:
    """Perbarui sebagian field jenjang pendidikan.

    Hanya field yang diisi (non-None) yang dikirim ke backend.

    Args:
        jp_id: UUID jenjang pendidikan.
        kode: Kode baru (opsional).
        nama: Nama baru (opsional).
        urutan: Urutan baru (opsional).
        aktif: Status aktif baru (opsional).

    Returns:
        Data jenjang pendidikan setelah diperbarui.
    """
    body: dict = {}
    if kode is not None:
        body["kode"] = kode
    if nama is not None:
        body["nama"] = nama
    if urutan is not None:
        body["urutan"] = urutan
    if aktif is not None:
        body["aktif"] = aktif
    try:
        return await backend_patch(f"/api/v1/jenjang-pendidikan/{jp_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_jenjang_pendidikan(ctx: Context, jp_id: str) -> dict:
    """Hapus jenjang pendidikan berdasarkan ID.

    Args:
        jp_id: UUID jenjang pendidikan.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/jenjang-pendidikan/{jp_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# CORE — SEKOLAH (lengkap: search/get/update/delete)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def cari_sekolah(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari sekolah dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["kota", "=", "Semarang"]]``.
        order: Urutan hasil, mis. ``[["nama", "asc"]]``.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/sekolah/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_sekolah(ctx: Context, sekolah_id: str) -> dict:
    """Ambil satu sekolah berdasarkan ID.

    Args:
        sekolah_id: UUID sekolah.

    Returns:
        Data sekolah.
    """
    try:
        return await backend_get(f"/api/v1/sekolah/{sekolah_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_sekolah(
    ctx: Context,
    sekolah_id: str,
    nama: str | None = None,
    npsn: str | None = None,
    jenjang_pendidikan_id: str | None = None,
    kota: str | None = None,
    provinsi: str | None = None,
    aktif: bool | None = None,
) -> dict:
    """Perbarui sebagian field sekolah.

    Args:
        sekolah_id: UUID sekolah.
        nama: Nama baru (opsional).
        npsn: NPSN baru (opsional).
        jenjang_pendidikan_id: UUID jenjang baru (opsional).
        kota: Kota baru (opsional).
        provinsi: Provinsi baru (opsional).
        aktif: Status aktif baru (opsional).

    Returns:
        Data sekolah setelah diperbarui.
    """
    body: dict = {}
    if nama is not None:
        body["nama"] = nama
    if npsn is not None:
        body["npsn"] = npsn
    if jenjang_pendidikan_id is not None:
        body["jenjang_pendidikan_id"] = jenjang_pendidikan_id
    if kota is not None:
        body["kota"] = kota
    if provinsi is not None:
        body["provinsi"] = provinsi
    if aktif is not None:
        body["aktif"] = aktif
    try:
        return await backend_patch(f"/api/v1/sekolah/{sekolah_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_sekolah(ctx: Context, sekolah_id: str) -> dict:
    """Hapus sekolah berdasarkan ID.

    Args:
        sekolah_id: UUID sekolah.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/sekolah/{sekolah_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# CORE — JABATAN (lengkap: search/get/update/delete)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def cari_jabatan(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari jabatan dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["jenis", "=", "struktural"]]``.
        order: Urutan hasil.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/jabatan/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_jabatan(ctx: Context, jabatan_id: str) -> dict:
    """Ambil satu jabatan berdasarkan ID.

    Args:
        jabatan_id: UUID jabatan.

    Returns:
        Data jabatan.
    """
    try:
        return await backend_get(f"/api/v1/jabatan/{jabatan_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_jabatan(
    ctx: Context,
    jabatan_id: str,
    kode: str | None = None,
    nama: str | None = None,
    jenis: str | None = None,
    unit_kerja_id: str | None = None,
    deskripsi: str | None = None,
    aktif: bool | None = None,
) -> dict:
    """Perbarui sebagian field jabatan.

    Args:
        jabatan_id: UUID jabatan.
        kode: Kode baru (opsional).
        nama: Nama baru (opsional).
        jenis: Jenis baru (opsional).
        unit_kerja_id: UUID unit kerja baru (opsional).
        deskripsi: Deskripsi baru (opsional).
        aktif: Status aktif baru (opsional).

    Returns:
        Data jabatan setelah diperbarui.
    """
    body: dict = {}
    if kode is not None:
        body["kode"] = kode
    if nama is not None:
        body["nama"] = nama
    if jenis is not None:
        body["jenis"] = jenis
    if unit_kerja_id is not None:
        body["unit_kerja_id"] = unit_kerja_id
    if deskripsi is not None:
        body["deskripsi"] = deskripsi
    if aktif is not None:
        body["aktif"] = aktif
    try:
        return await backend_patch(f"/api/v1/jabatan/{jabatan_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_jabatan(ctx: Context, jabatan_id: str) -> dict:
    """Hapus jabatan berdasarkan ID.

    Args:
        jabatan_id: UUID jabatan.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/jabatan/{jabatan_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# CORE — PARTISIPAN (lengkap: search/get/update/delete)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def cari_partisipan(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari partisipan dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["sekolah_id", "=", "<uuid>"]]``.
        order: Urutan hasil.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/partisipan/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_partisipan(ctx: Context, partisipan_id: str) -> dict:
    """Ambil satu partisipan berdasarkan ID.

    Args:
        partisipan_id: UUID partisipan.

    Returns:
        Data partisipan.
    """
    try:
        return await backend_get(f"/api/v1/partisipan/{partisipan_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_partisipan(
    ctx: Context,
    partisipan_id: str,
    nama: str | None = None,
    email: str | None = None,
    sekolah_id: str | None = None,
    jabatan_utama_id: str | None = None,
    jabatan_tambahan_ids: list | None = None,
    masa_kerja_tahun: int | None = None,
    masa_kerja_bulan: int | None = None,
    mata_pelajaran_utama_id: str | None = None,
    aktif: bool | None = None,
) -> dict:
    """Perbarui sebagian field partisipan.

    Args:
        partisipan_id: UUID partisipan.
        nama: Nama baru (opsional).
        email: Email baru (opsional).
        sekolah_id: UUID sekolah baru (opsional).
        jabatan_utama_id: UUID jabatan utama baru (opsional).
        jabatan_tambahan_ids: Daftar UUID jabatan tambahan (opsional).
        masa_kerja_tahun: Masa kerja (tahun) baru (opsional).
        masa_kerja_bulan: Masa kerja (bulan) baru (opsional).
        mata_pelajaran_utama_id: UUID mata pelajaran utama (opsional, untuk guru).
        aktif: Status aktif baru (opsional).

    Returns:
        Data partisipan setelah diperbarui.
    """
    body: dict = {}
    if nama is not None:
        body["nama"] = nama
    if email is not None:
        body["email"] = email
    if sekolah_id is not None:
        body["sekolah_id"] = sekolah_id
    if jabatan_utama_id is not None:
        body["jabatan_utama_id"] = jabatan_utama_id
    if jabatan_tambahan_ids is not None:
        body["jabatan_tambahan_ids"] = jabatan_tambahan_ids
    if masa_kerja_tahun is not None:
        body["masa_kerja_tahun"] = masa_kerja_tahun
    if masa_kerja_bulan is not None:
        body["masa_kerja_bulan"] = masa_kerja_bulan
    if mata_pelajaran_utama_id is not None:
        body["mata_pelajaran_utama_id"] = mata_pelajaran_utama_id
    if aktif is not None:
        body["aktif"] = aktif
    try:
        return await backend_patch(f"/api/v1/partisipan/{partisipan_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_partisipan(ctx: Context, partisipan_id: str) -> dict:
    """Hapus partisipan berdasarkan ID.

    Args:
        partisipan_id: UUID partisipan.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/partisipan/{partisipan_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# CORE — MATA PELAJARAN (domain baru: list/create/search/get/update/delete)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def daftar_mata_pelajaran(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar mata pelajaran yang terdaftar.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` (list mata pelajaran) + ``total``.
    """
    try:
        return await backend_get("/api/v1/mata-pelajaran", ctx=ctx, limit=limit, offset=offset)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_mata_pelajaran(
    ctx: Context,
    kode: str,
    nama: str,
    kelompok: str,
    deskripsi: str | None = None,
    aktif: bool = True,
) -> dict:
    """Buat mata pelajaran baru.

    Args:
        kode: Kode unik mata pelajaran (mis. ``MTK``).
        nama: Nama mata pelajaran (mis. ``Matematika``).
        kelompok: Kelompok mata pelajaran (mis. ``umum``).
        deskripsi: Deskripsi singkat (opsional).
        aktif: Status aktif (default True).

    Returns:
        Data mata pelajaran yang baru dibuat termasuk ``id``.
    """
    body: dict = {"kode": kode, "nama": nama, "kelompok": kelompok, "aktif": aktif}
    if deskripsi is not None:
        body["deskripsi"] = deskripsi
    try:
        return await backend_post("/api/v1/mata-pelajaran", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_mata_pelajaran(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari mata pelajaran dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["kelompok", "=", "umum"]]``.
        order: Urutan hasil.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/mata-pelajaran/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_mata_pelajaran(ctx: Context, mp_id: str) -> dict:
    """Ambil satu mata pelajaran berdasarkan ID.

    Args:
        mp_id: UUID mata pelajaran.

    Returns:
        Data mata pelajaran.
    """
    try:
        return await backend_get(f"/api/v1/mata-pelajaran/{mp_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_mata_pelajaran(
    ctx: Context,
    mp_id: str,
    kode: str | None = None,
    nama: str | None = None,
    kelompok: str | None = None,
    deskripsi: str | None = None,
    aktif: bool | None = None,
) -> dict:
    """Perbarui sebagian field mata pelajaran.

    Args:
        mp_id: UUID mata pelajaran.
        kode: Kode baru (opsional).
        nama: Nama baru (opsional).
        kelompok: Kelompok baru (opsional).
        deskripsi: Deskripsi baru (opsional).
        aktif: Status aktif baru (opsional).

    Returns:
        Data mata pelajaran setelah diperbarui.
    """
    body: dict = {}
    if kode is not None:
        body["kode"] = kode
    if nama is not None:
        body["nama"] = nama
    if kelompok is not None:
        body["kelompok"] = kelompok
    if deskripsi is not None:
        body["deskripsi"] = deskripsi
    if aktif is not None:
        body["aktif"] = aktif
    try:
        return await backend_patch(f"/api/v1/mata-pelajaran/{mp_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_mata_pelajaran(ctx: Context, mp_id: str) -> dict:
    """Hapus mata pelajaran berdasarkan ID.

    Args:
        mp_id: UUID mata pelajaran.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/mata-pelajaran/{mp_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# CORE — SME PANEL (lengkap: create/search/update/delete/remove anggota)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def buat_sme_panel(ctx: Context, jabatan_id: str, aktif: bool = True) -> dict:
    """Buat SME Panel baru untuk sebuah jabatan.

    Args:
        jabatan_id: UUID jabatan yang dipanel.
        aktif: Status aktif (default True).

    Returns:
        Data SME Panel yang baru dibuat termasuk ``id``.
    """
    body: dict = {"jabatan_id": jabatan_id, "aktif": aktif}
    try:
        return await backend_post("/api/v1/sme-panel", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_sme_panel(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari SME Panel dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["aktif", "=", true]]``.
        order: Urutan hasil.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/sme-panel/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_sme_panel(
    ctx: Context,
    panel_id: str,
    aktif: bool | None = None,
    koordinator_id: str | None = None,
) -> dict:
    """Perbarui SME Panel (status aktif dan/atau koordinator).

    Args:
        panel_id: UUID SME Panel.
        aktif: Status aktif baru (opsional).
        koordinator_id: UUID partisipan koordinator panel (opsional). Koordinator
            harus sudah menjadi anggota panel. Kirim ``"HAPUS"`` untuk menghapus
            koordinator yang ada.

    Returns:
        Data SME Panel setelah diperbarui.
    """
    body: dict = {}
    if aktif is not None:
        body["aktif"] = aktif
    if koordinator_id == "HAPUS":
        body["koordinator_id"] = None
    elif koordinator_id is not None:
        body["koordinator_id"] = koordinator_id
    try:
        return await backend_patch(f"/api/v1/sme-panel/{panel_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_sme_panel(ctx: Context, panel_id: str) -> dict:
    """Hapus SME Panel berdasarkan ID.

    Args:
        panel_id: UUID SME Panel.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/sme-panel/{panel_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_anggota_sme_panel(ctx: Context, panel_id: str, partisipan_id: str) -> dict:
    """Keluarkan partisipan dari keanggotaan SME Panel.

    Args:
        panel_id: UUID SME Panel.
        partisipan_id: UUID partisipan yang dikeluarkan.

    Returns:
        Konfirmasi penghapusan anggota.
    """
    try:
        return await backend_delete(
            f"/api/v1/sme-panel/{panel_id}/anggota/{partisipan_id}", ctx=ctx
        )
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# SYSTEM — health / ready / version / me
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def cek_kesehatan_backend(ctx: Context) -> dict:
    """Cek liveness backend (apakah service hidup).

    Returns:
        Status kesehatan backend.
    """
    try:
        return await backend_get("/api/v1/health", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cek_kesiapan_backend(ctx: Context) -> dict:
    """Cek readiness backend (apakah siap melayani, termasuk koneksi DB).

    Returns:
        Status kesiapan backend.
    """
    try:
        return await backend_get("/api/v1/ready", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def versi_backend(ctx: Context) -> dict:
    """Ambil versi backend anjab-abk-backend yang sedang berjalan.

    Returns:
        Informasi versi backend.
    """
    try:
        return await backend_get("/api/v1/version", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def info_saya(ctx: Context) -> dict:
    """Ambil informasi pengguna terautentikasi saat ini (dari token Authentik).

    Returns:
        Klaim identitas pengguna (sub, email, groups, dll.) sebagaimana dilihat backend.
    """
    try:
        return await backend_get("/api/v1/me", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# TASK INVENTORY — kelengkapan (search/update/delete, responden, seleksi,
# tahap2, detail, kuesioner, catalog)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def cari_ti_sesi(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari sesi Task Inventory dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["status", "=", "DRAFT"]]``.
        order: Urutan hasil.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/task-inventory/sesi/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_ti_sesi(
    ctx: Context,
    sesi_id: str,
    periode: str | None = None,
    koordinator_id: str | None = None,
    min_responden: int | None = None,
    max_responden: int | None = None,
    catatan: str | None = None,
) -> dict:
    """Perbarui sebagian field sesi Task Inventory.

    Args:
        sesi_id: UUID sesi TI.
        periode: Periode baru (opsional).
        koordinator_id: UUID koordinator SME panel (opsional). Kirim ``"HAPUS"``
            untuk menghapus koordinator yang ada.
        min_responden: Minimal responden (opsional).
        max_responden: Maksimal responden (opsional).
        catatan: Catatan baru (opsional).

    Returns:
        Data sesi TI setelah diperbarui.
    """
    body: dict = {}
    if periode is not None:
        body["periode"] = periode
    if koordinator_id == "HAPUS":
        body["koordinator_id"] = None
    elif koordinator_id is not None:
        body["koordinator_id"] = koordinator_id
    if min_responden is not None:
        body["min_responden"] = min_responden
    if max_responden is not None:
        body["max_responden"] = max_responden
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_patch(f"/api/v1/task-inventory/sesi/{sesi_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_ti_sesi(ctx: Context, sesi_id: str, paksa: bool = False) -> dict:
    """Hapus sesi Task Inventory berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin). Sesi berstatus DRAFT dapat dihapus langsung; sesi di status lain
    ditolak (422) kecuali ``paksa=True``.

    Args:
        sesi_id: UUID sesi TI.
        paksa: Bila True, hapus sesi non-DRAFT beserta SELURUH responden, seleksi,
            detail, dan keputusan Tahap 2 miliknya — **permanen, tidak dapat
            dibatalkan**. Gunakan dengan hati-hati.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(
            f"/api/v1/task-inventory/sesi/{sesi_id}", ctx=ctx, params={"paksa": paksa}
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_daftar_responden(ctx: Context, sesi_id: str) -> list:
    """Ambil daftar responden pada sebuah sesi Task Inventory.

    Args:
        sesi_id: UUID sesi TI.

    Returns:
        Daftar responden sesi.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/sesi/{sesi_id}/responden", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_detail_responden(ctx: Context, responden_id: str) -> dict:
    """Ambil detail satu responden Task Inventory.

    Args:
        responden_id: UUID responden.

    Returns:
        Data responden.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/sesi/responden/{responden_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_hapus_responden(ctx: Context, responden_id: str) -> dict:
    """Hapus responden Task Inventory berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin).

    Args:
        responden_id: UUID responden.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(
            f"/api/v1/task-inventory/sesi/responden/{responden_id}", ctx=ctx
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_seleksi_responden(ctx: Context, responden_id: str) -> dict:
    """Ambil seleksi task (Tahap 1) milik responden.

    Args:
        responden_id: UUID responden.

    Returns:
        Daftar task yang dipilih responden pada Tahap 1.
    """
    try:
        return await backend_get(
            f"/api/v1/task-inventory/sesi/responden/{responden_id}/seleksi", ctx=ctx
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_submit_seleksi(ctx: Context, responden_id: str, task_kode: list[str]) -> dict:
    """Submit seleksi task Tahap 1 untuk seorang responden (anggota SME panel).

    Args:
        responden_id: UUID responden.
        task_kode: Daftar kode task yang dipilih relevan untuk jabatan.

    Returns:
        Konfirmasi penyimpanan seleksi.
    """
    try:
        return await backend_post(
            f"/api/v1/task-inventory/sesi/responden/{responden_id}/seleksi",
            ctx=ctx,
            body={"task_kode": task_kode},
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_tahap2_review(ctx: Context, sesi_id: str) -> dict:
    """Ambil daftar task yang perlu direview koordinator (Tahap 2).

    Berisi task yang TIDAK dipilih secara unanimous di Tahap 1.

    Args:
        sesi_id: UUID sesi TI.

    Returns:
        Daftar task partial untuk keputusan koordinator.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/sesi/{sesi_id}/tahap2", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_submit_tahap2(ctx: Context, sesi_id: str, keputusan: list[dict]) -> dict:
    """Submit keputusan koordinator pada Tahap 2 Task Inventory.

    Args:
        sesi_id: UUID sesi TI.
        keputusan: Daftar keputusan, tiap item berbentuk
            ``{"task_kode": str, "disetujui": bool}`` — ``disetujui=True`` berarti
            task masuk ke Tahap 3.

    Returns:
        Konfirmasi penyimpanan keputusan koordinator.
    """
    try:
        return await backend_post(
            f"/api/v1/task-inventory/sesi/{sesi_id}/tahap2",
            ctx=ctx,
            body={"keputusan": keputusan},
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_daftar_detail(ctx: Context, responden_id: str) -> list:
    """Ambil detail CalHR (Tahap 3) yang sudah diisi responden.

    Args:
        responden_id: UUID responden.

    Returns:
        Daftar detail task (5 komponen CalHR) milik responden.
    """
    try:
        return await backend_get(
            f"/api/v1/task-inventory/sesi/responden/{responden_id}/detail", ctx=ctx
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_submit_detail(ctx: Context, responden_id: str, detail: list[dict]) -> dict | list:
    """Submit detail CalHR Tahap 3 per task untuk seorang responden.

    Menyimpan seluruh detail sebagai draft (``PUT .../detail``) lalu langsung
    memfinalisasi (``POST .../detail/submit``) — dua langkah backend dalam satu
    panggilan tool.

    Args:
        responden_id: UUID responden.
        detail: Daftar detail task. Tiap item memuat ``task_kode``, ``sumber_bukti``
            (Formal/Aktual/Keduanya), ``kondisi`` (Baseline/Peak/Both),
            ``frekuensi_teks``, ``durasi_per_kali`` (menit), ``jam_per_minggu``,
            ``ai_mode`` (Human-led/Co-Pilot/AI-assisted),
            ``va_type`` (VA-Core/VA-Enable/NVA-Residual), serta opsional
            ``peak4w_hours``, ``dcs_flag``, ``catatan``.

    Returns:
        Daftar detail tersimpan setelah finalisasi.
    """
    try:
        await backend_put(
            f"/api/v1/task-inventory/sesi/responden/{responden_id}/detail",
            ctx=ctx,
            body={"detail": detail},
        )
        return await backend_post(
            f"/api/v1/task-inventory/sesi/responden/{responden_id}/detail/submit",
            ctx=ctx,
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_kuesioner_saya(ctx: Context) -> list:
    """Ambil daftar kuesioner Task Inventory yang di-assign ke saya (responden).

    Returns:
        Daftar penugasan Task Inventory milik pengguna terautentikasi.
    """
    try:
        return await backend_get("/api/v1/task-inventory/kuesioner/saya", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_catalog(
    ctx: Context,
    jabatan_id: str | None = None,
    unit: str | None = None,
) -> list:
    """Ambil katalog task inventory (master task) dengan filter opsional.

    Tiap item katalog membawa hirarki tiga tingkat untuk seleksi relevansi Tahap 1
    yang bertingkat (cascade): Tugas Pokok (``tugas_pokok_id``/``tugas_pokok``) →
    Detil Tugas (``detil_tugas_id``/``detil_tugas``, bisa null bila task langsung di
    bawah tugas pokok) → Uraian Tugas (``kode``/``uraian_tugas``). Gunakan
    ``tugas_pokok_id`` lalu ``detil_tugas_id`` sebagai kunci stabil saat mempersempit
    pilihan dari level ke level; ``kode`` uraian tugas terpilih dipakai untuk
    ``ti_submit_seleksi``.

    Args:
        jabatan_id: Filter ID jabatan (opsional). Gunakan ``ti_catalog_kombinasi``
            untuk melihat jabatan_id yang tersedia.
        unit: Filter unit kerja (opsional).

    Returns:
        Daftar task katalog sesuai filter, lengkap dengan id & nama tugas pokok,
        detil tugas, serta uraian tugas.
    """
    params: dict = {}
    if jabatan_id is not None:
        params["jabatan_id"] = jabatan_id
    if unit is not None:
        params["unit"] = unit
    try:
        return await backend_get("/api/v1/task-inventory/catalog", ctx=ctx, **params)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ti_catalog_kombinasi(ctx: Context) -> list:
    """Ambil daftar kombinasi unit × jabatan_id yang tersedia di katalog.

    Returns:
        Daftar kombinasi unit dan jabatan_id untuk membuat sesi TI.
    """
    try:
        return await backend_get("/api/v1/task-inventory/catalog/kombinasi", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# DCS — kelengkapan (get/search/update/delete, responden, jawaban, sub-skala,
# item, kuesioner, hasil responden)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def detail_dcs_sesi(ctx: Context, sesi_id: str) -> dict:
    """Ambil detail satu sesi DCS (Demand Complexity Scale).

    Args:
        sesi_id: UUID sesi DCS.

    Returns:
        Data sesi DCS.
    """
    try:
        return await backend_get(f"/api/v1/dcs/sesi/{sesi_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_dcs_sesi(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari sesi DCS dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["periode", "=", "2025/2026"]]``.
        order: Urutan hasil.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/dcs/sesi/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_dcs_sesi(
    ctx: Context,
    sesi_id: str,
    periode: str | None = None,
    min_responden: int | None = None,
    max_responden: int | None = None,
    catatan: str | None = None,
) -> dict:
    """Perbarui sebagian field sesi DCS.

    Args:
        sesi_id: UUID sesi DCS.
        periode: Periode baru (opsional).
        min_responden: Minimal responden (opsional).
        max_responden: Maksimal responden (opsional).
        catatan: Catatan baru (opsional).

    Returns:
        Data sesi DCS setelah diperbarui.
    """
    body: dict = {}
    if periode is not None:
        body["periode"] = periode
    if min_responden is not None:
        body["min_responden"] = min_responden
    if max_responden is not None:
        body["max_responden"] = max_responden
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_patch(f"/api/v1/dcs/sesi/{sesi_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_dcs_sesi(ctx: Context, sesi_id: str, paksa: bool = False) -> dict:
    """Hapus sesi DCS berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin). Sesi berstatus DRAFT dapat dihapus langsung; sesi di status lain
    ditolak (422) kecuali ``paksa=True``.

    Args:
        sesi_id: UUID sesi DCS.
        paksa: Bila True, hapus sesi non-DRAFT beserta SELURUH responden &
            jawabannya — **permanen, tidak dapat dibatalkan**. Gunakan dengan
            hati-hati.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/dcs/sesi/{sesi_id}", ctx=ctx, params={"paksa": paksa})
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_daftar_responden(ctx: Context, sesi_id: str) -> list:
    """Ambil daftar responden pada sebuah sesi DCS.

    Args:
        sesi_id: UUID sesi DCS.

    Returns:
        Daftar responden sesi.
    """
    try:
        return await backend_get(f"/api/v1/dcs/sesi/{sesi_id}/responden", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_detail_responden(ctx: Context, responden_id: str) -> dict:
    """Ambil detail satu responden DCS.

    Args:
        responden_id: UUID responden.

    Returns:
        Data responden.
    """
    try:
        return await backend_get(f"/api/v1/dcs/sesi/responden/{responden_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_hapus_responden(ctx: Context, responden_id: str) -> dict:
    """Hapus responden DCS berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin).

    Args:
        responden_id: UUID responden.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/dcs/sesi/responden/{responden_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_submit_jawaban(ctx: Context, responden_id: str, jawaban: list[dict]) -> dict | list:
    """Submit jawaban kuesioner DCS untuk seorang responden.

    Menyimpan seluruh jawaban sebagai draft (``PUT .../jawaban``) lalu langsung
    memfinalisasi (``POST .../jawaban/submit``) — dua langkah backend dalam satu
    panggilan tool. Gunakan endpoint draft-save backend langsung (via tool lain)
    bila hanya ingin menyimpan progres parsial tanpa finalisasi.

    Args:
        responden_id: UUID responden.
        jawaban: Daftar jawaban, tiap item ``{"item_id": str, "skor_raw": int}``
            dengan ``skor_raw`` skala 1–5 dan ``item_id`` kode item orisinal (mis. ``D1a``).

    Returns:
        Daftar jawaban tersimpan setelah finalisasi.
    """
    try:
        await backend_put(
            f"/api/v1/dcs/sesi/responden/{responden_id}/jawaban",
            ctx=ctx,
            body={"jawaban": jawaban},
        )
        return await backend_post(
            f"/api/v1/dcs/sesi/responden/{responden_id}/jawaban/submit",
            ctx=ctx,
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_daftar_jawaban(ctx: Context, responden_id: str) -> list:
    """Ambil jawaban DCS yang sudah diisi seorang responden.

    Args:
        responden_id: UUID responden.

    Returns:
        Daftar jawaban responden.
    """
    try:
        return await backend_get(f"/api/v1/dcs/sesi/responden/{responden_id}/jawaban", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_daftar_subskala(ctx: Context) -> dict:
    """Ambil daftar sub-skala DCS (master instrumen).

    Returns:
        Daftar sub-skala DCS.
    """
    try:
        return await backend_get("/api/v1/dcs/sub-skala", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_detail_subskala(ctx: Context, kode: str) -> dict:
    """Ambil detail satu sub-skala DCS berdasarkan kode.

    Args:
        kode: Kode sub-skala DCS.

    Returns:
        Data sub-skala.
    """
    try:
        return await backend_get(f"/api/v1/dcs/sub-skala/{kode}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_subskala_items(ctx: Context, kode: str) -> dict:
    """Ambil daftar item pernyataan pada sebuah sub-skala DCS.

    Args:
        kode: Kode sub-skala DCS.

    Returns:
        Daftar item pernyataan sub-skala.
    """
    try:
        return await backend_get(f"/api/v1/dcs/sub-skala/{kode}/items", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_perbarui_item(
    ctx: Context,
    item_id: str,
    pernyataan: str | None = None,
    arah: str | None = None,
    urutan: int | None = None,
) -> dict:
    """Perbarui item pernyataan DCS (master instrumen).

    Args:
        item_id: UUID item.
        pernyataan: Teks pernyataan baru (opsional).
        arah: Arah penilaian baru (opsional).
        urutan: Urutan tampil baru (opsional).

    Returns:
        Data item setelah diperbarui.
    """
    body: dict = {}
    if pernyataan is not None:
        body["pernyataan"] = pernyataan
    if arah is not None:
        body["arah"] = arah
    if urutan is not None:
        body["urutan"] = urutan
    try:
        return await backend_patch(f"/api/v1/dcs/sub-skala/items/{item_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_kuesioner_saya(ctx: Context) -> list:
    """Ambil daftar kuesioner DCS yang di-assign ke saya (responden).

    Returns:
        Daftar penugasan DCS milik pengguna terautentikasi.
    """
    try:
        return await backend_get("/api/v1/dcs/kuesioner/saya", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def dcs_hasil_responden(ctx: Context, responden_id: str) -> dict:
    """Ambil hasil analisis DCS untuk satu responden.

    Args:
        responden_id: UUID responden.

    Returns:
        Hasil DCS per responden (skor per sub-skala dan agregat).
    """
    try:
        return await backend_get(f"/api/v1/dcs/sesi/responden/{responden_id}/hasil", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# WCP — kelengkapan (get/search/update/delete, responden, jawaban, dimensi,
# item, kuesioner, hasil responden)
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def detail_wcp_sesi(ctx: Context, sesi_id: str) -> dict:
    """Ambil detail satu sesi WCP (Work Complexity Profile).

    Args:
        sesi_id: UUID sesi WCP.

    Returns:
        Data sesi WCP.
    """
    try:
        return await backend_get(f"/api/v1/wcp/sesi/{sesi_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_wcp_sesi(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari sesi WCP dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis. ``[["periode", "=", "2025/2026"]]``.
        order: Urutan hasil.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/wcp/sesi/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_wcp_sesi(
    ctx: Context,
    sesi_id: str,
    periode: str | None = None,
    min_responden: int | None = None,
    max_responden: int | None = None,
    catatan: str | None = None,
) -> dict:
    """Perbarui sebagian field sesi WCP.

    Args:
        sesi_id: UUID sesi WCP.
        periode: Periode baru (opsional).
        min_responden: Minimal responden (opsional).
        max_responden: Maksimal responden (opsional).
        catatan: Catatan baru (opsional).

    Returns:
        Data sesi WCP setelah diperbarui.
    """
    body: dict = {}
    if periode is not None:
        body["periode"] = periode
    if min_responden is not None:
        body["min_responden"] = min_responden
    if max_responden is not None:
        body["max_responden"] = max_responden
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_patch(f"/api/v1/wcp/sesi/{sesi_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_wcp_sesi(ctx: Context, sesi_id: str, paksa: bool = False) -> dict:
    """Hapus sesi WCP berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin). Sesi berstatus DRAFT dapat dihapus langsung; sesi di status lain
    ditolak (422) kecuali ``paksa=True``.

    Args:
        sesi_id: UUID sesi WCP.
        paksa: Bila True, hapus sesi non-DRAFT beserta SELURUH responden &
            jawabannya — **permanen, tidak dapat dibatalkan**. Gunakan dengan
            hati-hati.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/wcp/sesi/{sesi_id}", ctx=ctx, params={"paksa": paksa})
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_daftar_responden(ctx: Context, sesi_id: str) -> list:
    """Ambil daftar responden pada sebuah sesi WCP.

    Args:
        sesi_id: UUID sesi WCP.

    Returns:
        Daftar responden sesi.
    """
    try:
        return await backend_get(f"/api/v1/wcp/sesi/{sesi_id}/responden", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_detail_responden(ctx: Context, responden_id: str) -> dict:
    """Ambil detail satu responden WCP.

    Args:
        responden_id: UUID responden.

    Returns:
        Data responden.
    """
    try:
        return await backend_get(f"/api/v1/wcp/sesi/responden/{responden_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_hapus_responden(ctx: Context, responden_id: str) -> dict:
    """Hapus responden WCP berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin).

    Args:
        responden_id: UUID responden.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/wcp/sesi/responden/{responden_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_submit_jawaban(ctx: Context, responden_id: str, jawaban: list[dict]) -> dict | list:
    """Submit jawaban kuesioner WCP untuk seorang responden.

    Menyimpan seluruh jawaban sebagai draft (``PUT .../jawaban``) lalu langsung
    memfinalisasi (``POST .../jawaban/submit``) — dua langkah backend dalam satu
    panggilan tool.

    Args:
        responden_id: UUID responden.
        jawaban: Daftar jawaban, tiap item ``{"item_id": str, "skor_raw": int}``
            dengan ``skor_raw`` skala 1–5 dan ``item_id`` kode item orisinal (mis. ``SC1a``).

    Returns:
        Daftar jawaban tersimpan setelah finalisasi.
    """
    try:
        await backend_put(
            f"/api/v1/wcp/sesi/responden/{responden_id}/jawaban",
            ctx=ctx,
            body={"jawaban": jawaban},
        )
        return await backend_post(
            f"/api/v1/wcp/sesi/responden/{responden_id}/jawaban/submit",
            ctx=ctx,
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_daftar_jawaban(ctx: Context, responden_id: str) -> list:
    """Ambil jawaban WCP yang sudah diisi seorang responden.

    Args:
        responden_id: UUID responden.

    Returns:
        Daftar jawaban responden.
    """
    try:
        return await backend_get(f"/api/v1/wcp/sesi/responden/{responden_id}/jawaban", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_daftar_dimensi(ctx: Context) -> list:
    """Ambil daftar dimensi WCP (master instrumen).

    Returns:
        Daftar dimensi WCP.
    """
    try:
        return await backend_get("/api/v1/wcp/dimensi", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_detail_dimensi(ctx: Context, kode: str) -> dict:
    """Ambil detail satu dimensi WCP berdasarkan kode.

    Args:
        kode: Kode dimensi WCP.

    Returns:
        Data dimensi.
    """
    try:
        return await backend_get(f"/api/v1/wcp/dimensi/{kode}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_dimensi_items(ctx: Context, kode: str) -> list:
    """Ambil daftar item pernyataan pada sebuah dimensi WCP.

    Args:
        kode: Kode dimensi WCP.

    Returns:
        Daftar item pernyataan dimensi.
    """
    try:
        return await backend_get(f"/api/v1/wcp/dimensi/{kode}/items", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_perbarui_item(
    ctx: Context,
    item_id: str,
    pernyataan: str | None = None,
    reverse_type: str | None = None,
    urutan: int | None = None,
) -> dict:
    """Perbarui item pernyataan WCP (master instrumen).

    Args:
        item_id: UUID item.
        pernyataan: Teks pernyataan baru (opsional).
        reverse_type: Tipe reverse-scoring baru (opsional).
        urutan: Urutan tampil baru (opsional).

    Returns:
        Data item setelah diperbarui.
    """
    body: dict = {}
    if pernyataan is not None:
        body["pernyataan"] = pernyataan
    if reverse_type is not None:
        body["reverse_type"] = reverse_type
    if urutan is not None:
        body["urutan"] = urutan
    try:
        return await backend_patch(f"/api/v1/wcp/dimensi/items/{item_id}", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_kuesioner_saya(ctx: Context) -> list:
    """Ambil daftar kuesioner WCP yang di-assign ke saya (responden).

    Returns:
        Daftar penugasan WCP milik pengguna terautentikasi.
    """
    try:
        return await backend_get("/api/v1/wcp/kuesioner/saya", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def wcp_hasil_responden(ctx: Context, responden_id: str) -> dict:
    """Ambil hasil analisis WCP untuk satu responden.

    Args:
        responden_id: UUID responden.

    Returns:
        Hasil WCP per responden (skor per dimensi dan agregat).
    """
    try:
        return await backend_get(f"/api/v1/wcp/sesi/responden/{responden_id}/hasil", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# DOMAIN: OPM (Overall Priority Matrix)
# ════════════════════════════════════════════════════════════════════════════════
#
# OPM menilai prioritas task (Importance/Frequency/Criticality) berbasis snapshot
# task hasil sesi Task Inventory yang sudah frozen (lihat ti_task_terpilih).


@mcp.tool
async def hapus_opm_sesi(ctx: Context, sesi_id: str, paksa: bool = False) -> dict:
    """Hapus sesi OPM berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin). Sesi berstatus DRAFT dapat dihapus langsung; sesi di status lain
    ditolak (422) kecuali ``paksa=True``.

    Args:
        sesi_id: UUID sesi OPM.
        paksa: Bila True, hapus sesi non-DRAFT beserta SELURUH responden &
            jawabannya — **permanen, tidak dapat dibatalkan**. Gunakan dengan
            hati-hati.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/opm/sesi/{sesi_id}", ctx=ctx, params={"paksa": paksa})
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def opm_hapus_responden(ctx: Context, responden_id: str) -> dict:
    """Hapus responden OPM berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin).

    Args:
        responden_id: UUID responden.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/opm/sesi/responden/{responden_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# DOMAIN: TIME STUDY (TS) — penugasan per partisipan (bukan sesi)
# ════════════════════════════════════════════════════════════════════════════════
#
# Time Study tidak memakai konsep sesi — setiap partisipan mendapat satu
# penugasan (aktif/nonaktif) dan mencatat log harian open-ended selama
# penugasannya aktif. Mengukur alokasi waktu kerja per kategori aktivitas
# (core, character, improve, strategic, admin, recovery).


@mcp.tool
async def daftar_ts_penugasan(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar penugasan Time Study (admin).

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list penugasan TS) dan ``total`` (total record).
    """
    try:
        return await backend_get(
            "/api/v1/time-study/penugasan", ctx=ctx, limit=limit, offset=offset
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_ts_penugasan(
    ctx: Context,
    partisipan_id: str,
    aktif: bool = True,
    catatan: str | None = None,
) -> dict:
    """Tugaskan seorang partisipan untuk mencatat Time Study (admin).

    Args:
        partisipan_id: UUID partisipan yang ditugaskan.
        aktif: Status aktif penugasan (default True).
        catatan: Catatan tambahan (opsional).

    Returns:
        Data penugasan TS yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {"partisipan_id": partisipan_id, "aktif": aktif}
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_post("/api/v1/time-study/penugasan", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_ts_penugasan(ctx: Context, penugasan_id: str) -> dict:
    """Ambil detail satu penugasan Time Study (admin atau pemilik).

    Args:
        penugasan_id: UUID penugasan TS.

    Returns:
        Data penugasan TS.
    """
    try:
        return await backend_get(f"/api/v1/time-study/penugasan/{penugasan_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_ts_penugasan(
    ctx: Context,
    penugasan_id: str,
    aktif: bool | None = None,
    catatan: str | None = None,
) -> dict:
    """Perbarui sebagian field penugasan Time Study (admin; mis. nonaktifkan).

    Args:
        penugasan_id: UUID penugasan TS.
        aktif: Status aktif baru (opsional).
        catatan: Catatan baru (opsional).

    Returns:
        Data penugasan TS setelah diperbarui.
    """
    body: dict = {}
    if aktif is not None:
        body["aktif"] = aktif
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_patch(
            f"/api/v1/time-study/penugasan/{penugasan_id}", ctx=ctx, body=body
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_ts_penugasan(ctx: Context, penugasan_id: str) -> dict:
    """Hapus penugasan Time Study berdasarkan ID.

    **Hanya dapat dijalankan oleh admin** (backend menolak dengan 403 bila token
    bukan admin).

    Args:
        penugasan_id: UUID penugasan TS.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/time-study/penugasan/{penugasan_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ts_daftar_log(ctx: Context, penugasan_id: str) -> list:
    """Ambil daftar log harian Time Study milik sebuah penugasan.

    Args:
        penugasan_id: UUID penugasan TS.

    Returns:
        Daftar log harian penugasan.
    """
    try:
        return await backend_get(f"/api/v1/time-study/penugasan/{penugasan_id}/log", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ts_buat_log(
    ctx: Context,
    penugasan_id: str,
    tanggal: str,
    waktu_masuk: str,
    waktu_keluar: str,
    day_color: str,
    menit_core: int,
    menit_character: int,
    menit_improve: int,
    menit_strategic: int,
    menit_admin: int,
    menit_recovery: int,
    catatan: str | None = None,
) -> dict:
    """Buat satu log harian Time Study untuk sebuah penugasan.

    Args:
        penugasan_id: UUID penugasan TS.
        tanggal: Tanggal log (ISO ``YYYY-MM-DD``).
        waktu_masuk: Jam masuk (mis. ``07:00``).
        waktu_keluar: Jam keluar (mis. ``16:00``).
        day_color: Kategori warna hari (mis. ``green``/``yellow``/``red``).
        menit_core: Menit aktivitas Core.
        menit_character: Menit aktivitas Character.
        menit_improve: Menit aktivitas Improve.
        menit_strategic: Menit aktivitas Strategic.
        menit_admin: Menit aktivitas Admin.
        menit_recovery: Menit Recovery.
        catatan: Catatan (opsional).

    Returns:
        Data log yang baru dibuat termasuk ``id``.
    """
    body: dict = {
        "tanggal": tanggal,
        "waktu_masuk": waktu_masuk,
        "waktu_keluar": waktu_keluar,
        "day_color": day_color,
        "menit_core": menit_core,
        "menit_character": menit_character,
        "menit_improve": menit_improve,
        "menit_strategic": menit_strategic,
        "menit_admin": menit_admin,
        "menit_recovery": menit_recovery,
    }
    if catatan is not None:
        body["catatan"] = catatan
    try:
        return await backend_post(
            f"/api/v1/time-study/penugasan/{penugasan_id}/log", ctx=ctx, body=body
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ts_detail_log(ctx: Context, penugasan_id: str, log_id: str) -> dict:
    """Ambil satu log harian Time Study.

    Args:
        penugasan_id: UUID penugasan TS.
        log_id: UUID log.

    Returns:
        Data log harian.
    """
    try:
        return await backend_get(
            f"/api/v1/time-study/penugasan/{penugasan_id}/log/{log_id}", ctx=ctx
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ts_perbarui_log(
    ctx: Context,
    penugasan_id: str,
    log_id: str,
    tanggal: str | None = None,
    waktu_masuk: str | None = None,
    waktu_keluar: str | None = None,
    day_color: str | None = None,
    menit_core: int | None = None,
    menit_character: int | None = None,
    menit_improve: int | None = None,
    menit_strategic: int | None = None,
    menit_admin: int | None = None,
    menit_recovery: int | None = None,
    catatan: str | None = None,
) -> dict:
    """Perbarui sebagian field log harian Time Study.

    Args:
        penugasan_id: UUID penugasan TS.
        log_id: UUID log.
        tanggal: Tanggal baru (opsional).
        waktu_masuk: Jam masuk baru (opsional).
        waktu_keluar: Jam keluar baru (opsional).
        day_color: Kategori warna hari baru (opsional).
        menit_core: Menit Core baru (opsional).
        menit_character: Menit Character baru (opsional).
        menit_improve: Menit Improve baru (opsional).
        menit_strategic: Menit Strategic baru (opsional).
        menit_admin: Menit Admin baru (opsional).
        menit_recovery: Menit Recovery baru (opsional).
        catatan: Catatan baru (opsional).

    Returns:
        Data log setelah diperbarui.
    """
    body: dict = {}
    for key, val in (
        ("tanggal", tanggal),
        ("waktu_masuk", waktu_masuk),
        ("waktu_keluar", waktu_keluar),
        ("day_color", day_color),
        ("menit_core", menit_core),
        ("menit_character", menit_character),
        ("menit_improve", menit_improve),
        ("menit_strategic", menit_strategic),
        ("menit_admin", menit_admin),
        ("menit_recovery", menit_recovery),
        ("catatan", catatan),
    ):
        if val is not None:
            body[key] = val
    try:
        return await backend_patch(
            f"/api/v1/time-study/penugasan/{penugasan_id}/log/{log_id}", ctx=ctx, body=body
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def ts_kuesioner_saya(ctx: Context) -> list:
    """Ambil daftar kuesioner Time Study yang di-assign ke saya (responden).

    Returns:
        Daftar penugasan Time Study milik pengguna terautentikasi.
    """
    try:
        return await backend_get("/api/v1/time-study/kuesioner/saya", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ════════════════════════════════════════════════════════════════════════════════
# TASK INVENTORY — master data catalog: TugasPokok, DetilTugas, UraianTugas
# ════════════════════════════════════════════════════════════════════════════════


@mcp.tool
async def daftar_tugas_pokok(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar Tugas Pokok (master katalog Task Inventory).

    Tugas Pokok adalah entri katalog tingkat pertama pada Task Inventory,
    mewakili tugas-tugas utama sebuah jabatan sebelum dipecah menjadi
    Detil Tugas dan Uraian Tugas.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list tugas pokok) dan ``total`` (total record).
    """
    try:
        return await backend_get(
            "/api/v1/task-inventory/tugas-pokok", ctx=ctx, limit=limit, offset=offset
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_tugas_pokok(
    ctx: Context,
    jabatan_ids: list[str],
    nama: str,
) -> dict:
    """Buat entri Tugas Pokok baru pada katalog Task Inventory.

    TugasPokok dapat terkait dengan satu atau lebih Jabatan (M2M).
    DetilTugas di bawahnya hanya boleh memilih subset dari jabatan_ids TP ini.

    Args:
        jabatan_ids: Daftar ID jabatan yang terkait (minimal satu). Gunakan
            ``daftar_jabatan`` untuk mendapatkan ID yang valid.
        nama: Nama klaster tugas (mis. ``Pengelolaan SDM``). Bersifat unik
            secara global — dua TP tidak boleh punya nama sama.

    Returns:
        Data tugas pokok yang baru dibuat termasuk ``id``.
    """
    body: dict = {"jabatan_ids": jabatan_ids, "nama": nama}
    try:
        return await backend_post("/api/v1/task-inventory/tugas-pokok", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_tugas_pokok(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari Tugas Pokok dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis.
            ``[["jabatan_id", "=", "jbt_a1b2c3d4"]]``.
        order: Urutan hasil, mis. ``[["urutan", "asc"]]``.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/task-inventory/tugas-pokok/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_tugas_pokok(ctx: Context, tp_id: str) -> dict:
    """Ambil satu Tugas Pokok berdasarkan ID.

    Args:
        tp_id: UUID tugas pokok.

    Returns:
        Data tugas pokok.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/tugas-pokok/{tp_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_tugas_pokok(
    ctx: Context,
    tp_id: str,
    jabatan_ids: list[str] | None = None,
    nama: str | None = None,
) -> dict:
    """Perbarui sebagian field Tugas Pokok.

    Hanya field yang diisi (non-None) yang dikirim ke backend.

    Args:
        tp_id: UUID tugas pokok.
        jabatan_ids: Daftar ID jabatan baru (minimal satu, menggantikan
            seluruh daftar lama; opsional).
        nama: Nama klaster tugas baru (opsional).

    Returns:
        Data tugas pokok setelah diperbarui.
    """
    body: dict = {}
    if jabatan_ids is not None:
        body["jabatan_ids"] = jabatan_ids
    if nama is not None:
        body["nama"] = nama
    try:
        return await backend_patch(
            f"/api/v1/task-inventory/tugas-pokok/{tp_id}", ctx=ctx, body=body
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_tugas_pokok(ctx: Context, tp_id: str) -> dict:
    """Hapus Tugas Pokok berdasarkan ID.

    Args:
        tp_id: UUID tugas pokok.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/task-inventory/tugas-pokok/{tp_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ── DetilTugas ────────────────────────────────────────────────────────────────


@mcp.tool
async def daftar_detil_tugas(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar Detil Tugas (master katalog Task Inventory tingkat kedua).

    Detil Tugas adalah rincian dari Tugas Pokok, satu tingkat lebih spesifik
    sebelum dipecah lebih lanjut menjadi Uraian Tugas.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list detil tugas) dan ``total`` (total record).
    """
    try:
        return await backend_get(
            "/api/v1/task-inventory/detil-tugas", ctx=ctx, limit=limit, offset=offset
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_detil_tugas(
    ctx: Context,
    nama: str,
    tugas_pokok_id: str,
    jabatan_ids: list[str],
) -> dict:
    """Buat entri Detil Tugas baru pada katalog Task Inventory.

    DetilTugas terkait M2M dengan Jabatan; jabatan yang dipilih harus
    merupakan subset dari jabatan_ids TugasPokok induknya.

    Args:
        nama: Nama detil tugas.
        tugas_pokok_id: UUID Tugas Pokok induk (dari ``daftar_tugas_pokok``).
        jabatan_ids: Daftar ID jabatan yang terkait (minimal satu). Setiap
            ID harus ada di dalam ``jabatan_ids`` TugasPokok induk.

    Returns:
        Data detil tugas yang baru dibuat termasuk ``id`` (UUID).
    """
    body: dict = {
        "nama": nama,
        "tugas_pokok_id": tugas_pokok_id,
        "jabatan_ids": jabatan_ids,
    }
    try:
        return await backend_post("/api/v1/task-inventory/detil-tugas", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_detil_tugas(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari Detil Tugas dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis.
            ``[["tugas_pokok_id", "=", "<uuid>"]]``.
        order: Urutan hasil, mis. ``[["urutan", "asc"]]``.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/task-inventory/detil-tugas/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_detil_tugas(ctx: Context, dt_id: str) -> dict:
    """Ambil satu Detil Tugas berdasarkan ID.

    Args:
        dt_id: UUID detil tugas.

    Returns:
        Data detil tugas.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/detil-tugas/{dt_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_detil_tugas(
    ctx: Context,
    dt_id: str,
    nama: str | None = None,
    tugas_pokok_id: str | None = None,
    jabatan_ids: list[str] | None = None,
) -> dict:
    """Perbarui sebagian field Detil Tugas.

    Hanya field yang diisi (non-None) yang dikirim ke backend.

    Args:
        dt_id: UUID detil tugas.
        nama: Nama baru (opsional).
        tugas_pokok_id: UUID Tugas Pokok induk baru (opsional).
        jabatan_ids: Daftar ID jabatan baru (menggantikan seluruh daftar lama;
            setiap ID harus ada di ``jabatan_ids`` TugasPokok induk; opsional).

    Returns:
        Data detil tugas setelah diperbarui.
    """
    body: dict = {}
    if nama is not None:
        body["nama"] = nama
    if tugas_pokok_id is not None:
        body["tugas_pokok_id"] = tugas_pokok_id
    if jabatan_ids is not None:
        body["jabatan_ids"] = jabatan_ids
    try:
        return await backend_patch(
            f"/api/v1/task-inventory/detil-tugas/{dt_id}", ctx=ctx, body=body
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_detil_tugas(ctx: Context, dt_id: str) -> dict:
    """Hapus Detil Tugas berdasarkan ID.

    Args:
        dt_id: UUID detil tugas.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/task-inventory/detil-tugas/{dt_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


# ── UraianTugas ───────────────────────────────────────────────────────────────


@mcp.tool
async def daftar_uraian_tugas(
    ctx: Context,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Ambil daftar Uraian Tugas (master katalog Task Inventory tingkat ketiga).

    Uraian Tugas adalah unit tugas paling atomik dalam katalog Task Inventory —
    inilah entri yang dipilih oleh anggota SME panel saat pengisian Tahap 1.

    Args:
        limit: Jumlah item per halaman (maks 100, default 20).
        offset: Jumlah item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict dengan keys ``items`` (list uraian tugas) dan ``total`` (total record).
    """
    try:
        return await backend_get(
            "/api/v1/task-inventory/uraian-tugas", ctx=ctx, limit=limit, offset=offset
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def buat_uraian_tugas(
    ctx: Context,
    kode: str,
    uraian: str,
    unit: str,
    urutan: int,
    tugas_pokok_id: str,
    jabatan_id: str,
    detil_tugas_id: str | None = None,
) -> dict:
    """Buat entri Uraian Tugas baru pada katalog Task Inventory.

    Jabatan uraian tugas harus disertakan secara eksplisit dan harus merupakan
    salah satu dari jabatan_ids DetilTugas induknya (jika detil_tugas_id diisi).

    Args:
        kode: Kode deterministik unik (mis. ``TIf0b59714``).
        uraian: Pernyataan tugas (task statement), mis.
            ``Menyusun evaluasi karyawan``.
        unit: Unit/jenjang (TK, SD, SMP, SMA, SMK, dll.).
        urutan: Urutan tampil dalam kombinasi unit × jabatan (mulai 1).
        tugas_pokok_id: ID TugasPokok induk.
        jabatan_id: ID Jabatan yang terkait (M2O). Jika ``detil_tugas_id``
            diisi, jabatan ini harus ada di dalam ``jabatan_ids`` DetilTugas.
        detil_tugas_id: ID DetilTugas induk (opsional).

    Returns:
        Data uraian tugas yang baru dibuat termasuk ``id``.
    """
    body: dict = {
        "kode": kode,
        "uraian": uraian,
        "unit": unit,
        "urutan": urutan,
        "tugas_pokok_id": tugas_pokok_id,
        "jabatan_id": jabatan_id,
    }
    if detil_tugas_id is not None:
        body["detil_tugas_id"] = detil_tugas_id
    try:
        return await backend_post("/api/v1/task-inventory/uraian-tugas", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def cari_uraian_tugas(
    ctx: Context,
    domain: list | None = None,
    order: list | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Cari Uraian Tugas dengan domain bergaya Odoo.

    Args:
        domain: Kriteria pencarian, mis.
            ``[["detil_tugas_id", "=", "<uuid>"]]``.
        order: Urutan hasil, mis. ``[["urutan", "asc"]]``.
        limit: Jumlah item per halaman (default 20).
        offset: Item yang dilewati untuk paginasi (default 0).

    Returns:
        Dict ``items`` + ``total`` hasil pencarian.
    """
    body = {"domain": domain or [], "order": order or [], "limit": limit, "offset": offset}
    try:
        return await backend_post("/api/v1/task-inventory/uraian-tugas/search", ctx=ctx, body=body)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def detail_uraian_tugas(ctx: Context, ut_id: str) -> dict:
    """Ambil satu Uraian Tugas berdasarkan ID.

    Args:
        ut_id: UUID uraian tugas.

    Returns:
        Data uraian tugas.
    """
    try:
        return await backend_get(f"/api/v1/task-inventory/uraian-tugas/{ut_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def perbarui_uraian_tugas(
    ctx: Context,
    ut_id: str,
    kode: str | None = None,
    uraian: str | None = None,
    unit: str | None = None,
    urutan: int | None = None,
    tugas_pokok_id: str | None = None,
    detil_tugas_id: str | None = None,
    jabatan_id: str | None = None,
) -> dict:
    """Perbarui sebagian field Uraian Tugas.

    Hanya field yang diisi (non-None) yang dikirim ke backend.

    Args:
        ut_id: UUID uraian tugas.
        kode: Kode baru (opsional).
        uraian: Pernyataan tugas baru (opsional).
        unit: Unit/jenjang baru (opsional).
        urutan: Urutan tampil baru (opsional).
        tugas_pokok_id: ID TugasPokok induk baru (opsional).
        detil_tugas_id: ID DetilTugas induk baru (opsional).
        jabatan_id: ID Jabatan baru (opsional). Harus ada di dalam
            ``jabatan_ids`` DetilTugas terkait.

    Returns:
        Data uraian tugas setelah diperbarui.
    """
    body: dict = {}
    if kode is not None:
        body["kode"] = kode
    if uraian is not None:
        body["uraian"] = uraian
    if unit is not None:
        body["unit"] = unit
    if urutan is not None:
        body["urutan"] = urutan
    if tugas_pokok_id is not None:
        body["tugas_pokok_id"] = tugas_pokok_id
    if detil_tugas_id is not None:
        body["detil_tugas_id"] = detil_tugas_id
    if jabatan_id is not None:
        body["jabatan_id"] = jabatan_id
    try:
        return await backend_patch(
            f"/api/v1/task-inventory/uraian-tugas/{ut_id}", ctx=ctx, body=body
        )
    except BackendError as exc:
        _raise_tool_error(exc)


@mcp.tool
async def hapus_uraian_tugas(ctx: Context, ut_id: str) -> dict:
    """Hapus Uraian Tugas berdasarkan ID.

    Args:
        ut_id: UUID uraian tugas.

    Returns:
        Konfirmasi penghapusan.
    """
    try:
        return await backend_delete(f"/api/v1/task-inventory/uraian-tugas/{ut_id}", ctx=ctx)
    except BackendError as exc:
        _raise_tool_error(exc)
