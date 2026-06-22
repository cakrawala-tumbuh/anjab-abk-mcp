# Changelog

Semua perubahan penting pada project ini didokumentasikan di file ini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
