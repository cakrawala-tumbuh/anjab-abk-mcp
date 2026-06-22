# Changelog

Semua perubahan penting pada project ini didokumentasikan di file ini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
