# Changelog

Semua perubahan penting pada project ini didokumentasikan di file ini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.0] - 2026-06-23

### Changed

- **`ti_catalog`**: docstring diperkaya untuk menjelaskan hirarki tiga tingkat
  (Tugas Pokok → Detil Tugas → Uraian Tugas) yang menopang seleksi relevansi Tahap 1
  bertingkat. Tiap item katalog kini menyertakan `tugas_pokok_id` dan `detil_tugas_id`
  (kunci stabil) di samping nama-nama yang sudah ada — diteruskan apa adanya dari
  backend `TiCatalogRead`.

## [0.7.0] - 2026-06-23

### Changed (Breaking)

- **`buat_tugas_pokok`**: parameter `jabatan_id` (str tunggal) diganti `jabatan_ids`
  (list[str], minimal satu) — satu TugasPokok kini dapat terhubung ke beberapa Jabatan.
- **`buat_detil_tugas`**: parameter `jabatan_ids` (list[str], minimal satu) ditambahkan;
  nilai harus subset dari `jabatan_ids` TugasPokok terpilih.
- **`buat_uraian_tugas`**: parameter `jabatan_id` kini wajib eksplisit (str, harus ada
  dalam `jabatan_ids` DetilTugas terpilih); sebelumnya diwarisi otomatis dari TugasPokok.
- **`perbarui_tugas_pokok`**: mendukung `jabatan_ids` (list[str]) menggantikan `jabatan_id`.
- **`perbarui_detil_tugas`**: mendukung `jabatan_ids` (list[str]).

## [0.6.0] - 2026-06-22

### Changed (Breaking)

- **`buat_ti_sesi`**: parameter `kategori_jabatan` dihapus; `jabatan_id` kini argumen posisional
  wajib pertama (sebelumnya opsional).
- **`buat_tugas_pokok`**: parameter `jabatan_id` (wajib) ditambahkan; parameter lama `unit`
  dan `kategori_jabatan` dihapus — jabatan ditetapkan di level TugasPokok.
- **`ti_catalog`**: parameter `kategori_jabatan` diganti dengan `jabatan_id`.
- **`buat_uraian_tugas`**: kini memerlukan `kode`, `uraian`, `unit`, `urutan`, `tugas_pokok_id`
  (wajib); `jabatan_id` diwarisi otomatis dari `TugasPokok`.
- **`perbarui_uraian_tugas`**: parameter `nama` diganti `uraian`; `jabatan_id` dan `deskripsi`
  dihapus.

## [0.5.0] - 2026-06-22

### Changed

- Docstring tool TI dan SME panel diperbarui sesuai perubahan perilaku backend v0.13.0
  (unit sesi TI opsional, partisipan bebas ke panel SME).

## [0.4.0] - 2026-06-22

### Added

- **Master data katalog Task Inventory** — 18 tool MCP baru untuk tiga model
  hierarki katalog TI:
  - **TugasPokok** (`daftar_tugas_pokok`, `buat_tugas_pokok`, `cari_tugas_pokok`,
    `detail_tugas_pokok`, `perbarui_tugas_pokok`, `hapus_tugas_pokok`) —
    endpoint `/api/v1/task-inventory/tugas-pokok`.
  - **DetilTugas** (`daftar_detil_tugas`, `buat_detil_tugas`, `cari_detil_tugas`,
    `detail_detil_tugas`, `perbarui_detil_tugas`, `hapus_detil_tugas`) —
    endpoint `/api/v1/task-inventory/detil-tugas`.
  - **UraianTugas** (`daftar_uraian_tugas`, `buat_uraian_tugas`, `cari_uraian_tugas`,
    `detail_uraian_tugas`, `perbarui_uraian_tugas`, `hapus_uraian_tugas`) —
    endpoint `/api/v1/task-inventory/uraian-tugas`.
- Semua tool baru mendukung pola CRUD lengkap: list (GET), create (POST),
  search (POST /search), get (GET /{id}), update (PATCH /{id}), delete (DELETE /{id}).

## [0.3.0] - 2026-06-22

### Added

- **Login M2M headless** (`m2m.py`): pada mode stdio (tanpa OAuth user), MCP
  melakukan Authorization Code + PKCE sendiri ke Authentik via *flow executor API*
  memakai kredensial service user (`BACKEND_M2M_*`), lalu memakai access_token
  sebagai Bearer ke backend. Token di-cache & auto-refresh; tanpa browser, tanpa
  perubahan di sisi Authentik.
- Config baru: `BACKEND_M2M_AUTHENTIK_URL`, `BACKEND_M2M_CLIENT_ID`,
  `BACKEND_M2M_REDIRECT_URI`, `BACKEND_M2M_USERNAME`, `BACKEND_M2M_PASSWORD`,
  `BACKEND_M2M_SCOPE`, `BACKEND_M2M_FLOW_SLUG`.

### Changed

- `client.py`: urutan resolusi Bearer kini token user OAuth → token M2M → 
  `BACKEND_API_TOKEN`. Pada 401, token M2M di-refresh otomatis lalu request diulang.

## [0.2.0] - 2026-06-22

### Added

- Scaffold awal MCP server ANJAB-ABK menggunakan FastMCP Python.
- Tools untuk manajemen data inti: jenjang pendidikan, sekolah, jabatan, partisipan, SME panel.
- Tools untuk alat ukur Task Inventory (TI): sesi, responden, tahap, hasil.
- Tools untuk alat ukur DCS: sesi, responden, hasil.
- Tools untuk alat ukur WCP: sesi, responden, hasil.
- Tools untuk alat ukur Time Study (TS): sesi, responden, analisis.
- Otentikasi Authentik Pola B (token user diteruskan ke backend).
- Dukungan stdio, Claude Code (remote), dan Claude Web (HTTP/SSE + OAuth).
- **Cakupan penuh seluruh endpoint backend** (124 endpoint `/api/v1` → 128 tool MCP).
- Domain **mata pelajaran** lengkap (list/create/search/get/update/delete).
- Operasi CRUD lengkap untuk jenjang pendidikan (termasuk `buat_jenjang_pendidikan`),
  sekolah, jabatan, partisipan, dan SME panel — plus pencarian domain ala Odoo (`cari_*`),
  `detail_*`, `perbarui_*`, `hapus_*`.
- Tools responden, submit jawaban/seleksi/detail, kuesioner-saya, dan hasil per-responden
  untuk DCS, WCP, Task Inventory, dan Time Study.
- Tools master instrumen: sub-skala DCS, dimensi WCP, dan update item.
- Tools log harian Time Study (list/create/get/update).
- Tools sistem: `cek_kesehatan_backend`, `cek_kesiapan_backend`, `versi_backend`, `info_saya`.
- Tool `ti_tutup_sesi` untuk menutup sesi Task Inventory (transisi ke CLOSED).

### Changed

- `client.py` mendukung query parameter pada POST/PATCH (mis. `paksa`, `wcp_sesi_id`).

### Fixed

- Tools `*_analisis` (TI/DCS/WCP/TS) kini memakai metode HTTP `POST` sesuai route
  backend (sebelumnya `GET`, yang menyebabkan 405 Method Not Allowed).
