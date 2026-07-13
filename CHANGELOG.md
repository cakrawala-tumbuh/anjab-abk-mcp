# Changelog

Semua perubahan penting pada project ini didokumentasikan di file ini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Diverifikasi

- **Backlog 004 (terminologi "Sesi" → "Analisis Jabatan" di TI/OPM): docstring tool
  MCP sudah lengkap sejak commit sebelumnya.** Diaudit ulang seluruh docstring tool
  `*_ti_sesi`/`ti_*`/`opm_*` yang menyebut "sesi" — semuanya sudah menjelaskan bahwa
  **satu "sesi" TI/OPM = satu analisis untuk satu jabatan**, bukan sesi studi
  multi-partisipan, dan satu studi punya banyak di antaranya (satu per jabatan).
  Tidak ada perubahan kode; nama tool tetap tidak diubah.

### Ditambahkan

- **Tool bulk baru: `buat_ts_penugasan_banyak`, `ti_tambah_responden_banyak`,
  `opm_tambah_responden`, `opm_tambah_responden_banyak`.** Meng-expose
  endpoint bulk-assign idempoten baru di `anjab-abk-backend` (TS/TI/OPM) yang
  ditambahkan bersamaan dengan auto-populate SME panel di TI. Tool manual
  (single) yang sudah ada — `buat_ts_penugasan`, `ti_tambah_responden` — tidak
  berubah sama sekali. `opm_tambah_responden` (single) juga baru — domain OPM
  sebelumnya hanya punya tool hapus, meski endpoint backend-nya sudah lama
  ada. Response bulk (`{created, skipped}`) diteruskan apa adanya dari
  backend, tanpa transformasi tambahan di layer MCP.

## [0.12.0] - 2026-07-13

### Diperjelas

- **Docstring tool TI & OPM: klarifikasi arti "sesi"** — docstring seluruh
  tool `*_ti_sesi`/`ti_*`/`*_opm_sesi`/`opm_*` (mis. `buat_ti_sesi`,
  `daftar_ti_sesi`, `detail_ti_sesi`, `cari_ti_sesi`, `perbarui_ti_sesi`,
  `hapus_ti_sesi`, `ti_tambah_responden`, `ti_mulai_tahap1/2/3`,
  `ti_task_terpilih`, `ti_analisis`, `ti_tutup_sesi`, `ti_hasil`,
  `ti_daftar_responden`, `ti_detail_responden`, `ti_hapus_responden`,
  `ti_seleksi_responden`, `ti_submit_seleksi`, `ti_tahap2_review`,
  `ti_submit_tahap2`, `ti_daftar_detail`, `ti_submit_detail`,
  `ti_kuesioner_saya`, `ti_catalog`, `ti_catalog_kombinasi`,
  `ti_catalog_purge`, `ti_catalog_reseed`, `hapus_opm_sesi`,
  `opm_hapus_responden`) diperkaya untuk menegaskan bahwa satu **"sesi" TI/OPM
  adalah satu analisis untuk satu jabatan** — bukan sesi studi
  multi-partisipan; satu studi ANJAB/ABK memiliki banyak sesi seperti itu,
  satu per jabatan yang dianalisis. **Non-breaking**: nama tool, parameter,
  dan endpoint yang dipanggil tidak berubah sama sekali — perubahan murni
  teks docstring agar tidak menyesatkan pemanggil tool (Claude).

### Changed (Breaking)

- **DCS & WCP: sesi dihapus total, diganti instrumen singleton** — mengikuti
  refactor `anjab-abk-backend` yang menghapus entitas sesi DCS/WCP (satu
  deployment = satu studi, status `OPEN -> CLOSED -> ANALYZED`, tanpa
  create/delete). Tool `sesi_id`/`wcp_sesi_id` DIHAPUS total dari domain DCS/WCP;
  TI dan OPM **tidak berubah** (tetap memakai sesi).
  - **Dihapus**: `daftar_dcs_sesi`, `buat_dcs_sesi`, `dcs_buka_sesi`,
    `cari_dcs_sesi`, `hapus_dcs_sesi`, `daftar_wcp_sesi`, `buat_wcp_sesi`,
    `wcp_buka_sesi`, `cari_wcp_sesi`, `hapus_wcp_sesi`.
  - **Diganti nama** (mengikuti endpoint baru `/api/v1/{dcs,wcp}/instrumen`):
    `detail_dcs_sesi` → `dcs_instrumen`, `perbarui_dcs_sesi` →
    `dcs_perbarui_instrumen`, `dcs_tutup_sesi` → `dcs_tutup_instrumen` (idem
    untuk WCP).
  - **Baru**: `dcs_buka_ulang_instrumen`, `wcp_buka_ulang_instrumen`
    (`POST /instrumen/buka-ulang`, transisi CLOSED → OPEN).
  - **Signature berubah**: `dcs_tambah_responden`/`wcp_tambah_responden` kini
    menerima `partisipan_ids: list[str]` (bulk-assign, minimal 1) menggantikan
    `partisipan_id`/`nama` tunggal per sesi. `dcs_analisis`/`dcs_hasil`
    (dan padanan WCP) tidak lagi menerima `sesi_id`/`wcp_sesi_id` — K-Index
    gabungan DCS+WCP kini otomatis dihitung backend. `dcs_daftar_responden`/
    `wcp_daftar_responden` tidak lagi menerima `sesi_id`.
  - **Path diperbaiki** (tanpa perubahan nama/signature tool, path lama sudah
    404 di backend baru): `dcs_detail_responden`, `dcs_hapus_responden`,
    `dcs_submit_jawaban`, `dcs_daftar_jawaban`, `dcs_hasil_responden` dan
    padanan WCP-nya — `/api/v1/{dcs,wcp}/sesi/responden/...` menjadi
    `/api/v1/{dcs,wcp}/responden/...`.
  - Docstring `dcs_kuesioner_saya`/`wcp_kuesioner_saya` diperbarui: field
    respons `sesi_id`/`sesi_periode`/`sesi_catatan`/`sesi_status` sudah tidak
    ada, diganti `instrumen_status` + `catatan`.

## [0.11.0] - 2026-07-12

### Ditambahkan

- **Tool `ti_catalog_purge` & `ti_catalog_reseed`** — mencerminkan endpoint
  admin `POST /task-inventory/catalog/purge` dan `/reseed` di
  `anjab-abk-backend` v0.28.0. Memungkinkan purge total + reseed katalog
  master Task Inventory langsung dari Claude tanpa akses `DATABASE_URL`.

## [0.10.1] - 2026-07-12

### Fixed

- **Release workflow gagal sejak 2026-06-23** — `release.yml` memanggil
  reusable workflow di org `cakrawala-tumbuh/github-release` dan
  `cakrawala-tumbuh/release-docker-image-ghcr`, padahal kedua repo itu ada
  di `andhit-r/github-release` dan `andhit-r/release-docker-image-ghcr`
  (sama seperti `anjab-abk-backend` & `anjab-abk-web-app` yang releasenya
  sukses). GitHub menolak run tanpa menjalankan job sama sekali ("workflow
  file issue") karena tidak bisa me-resolve reusable workflow-nya.

## [0.10.0] - 2026-07-12

### Fixed

- **Bug 204/304 di `backend_request`** (`client.py`) — body kosong (`204 No
  Content`, `304 Not Modified`) tak lagi diparse sebagai JSON (dulu meledak
  `Expecting value: line 1 column 1 (char 0)` walau operasi backend sebenarnya
  berhasil, mis. 18 dari 19 tool `hapus_*`). Kegagalan parse JSON pada body
  non-kosong kini terbungkus `BackendError` (bukan `JSONDecodeError` mentah).
  `304` sengaja ditangani terpisah dari cek `response.is_success` — httpx
  menganggap `304` BUKAN sukses (di luar rentang 2xx) walau bukan error.
- **19 tool salah anotasi return `-> dict`** padahal endpoint backend membalas
  JSON array, memicu `structured_content must be a dict or None. Got list`.
  Diubah ke `-> list` (atau `-> dict | list` untuk tool yang dua langkah).
  Termasuk perbaikan tersembunyi: `dcs_submit_jawaban`, `wcp_submit_jawaban`,
  `ti_submit_detail` ternyata memanggil endpoint bulk-POST yang sudah dihapus
  backend (revisi draft-save/submit v0.25.0) — sekarang memanggil `PUT` (draft)
  lalu `POST .../submit` sesuai kontrak baru.

### Added

- **`paksa=True` pada `hapus_ti_sesi`/`hapus_dcs_sesi`/`hapus_wcp_sesi`/
  `hapus_opm_sesi`** — admin dapat menghapus sesi non-DRAFT beserta SELURUH
  responden & jawabannya (permanen), mengikuti backend `?paksa=true`.
- `backend_put` di `client.py` — helper PUT (draft-save parsial), belum ada
  sebelumnya walau backend sudah punya endpoint `PUT .../jawaban` & `.../detail`
  sejak v0.25.0.

### Changed

- `requirements-test.txt`: `respx` 0.21.1 → 0.23.1 — versi lama tidak
  kompatibel dengan `httpx` 0.28.1 yang sudah dipin (route respx tak pernah
  match, gagal senyap sebagai `AllMockedAssertionError`). Baru ketahuan
  sekarang karena `respx` sebelumnya tidak pernah benar-benar dipakai
  (`test_server.py` mem-mock `backend_*` langsung, melewati layer httpx).

## [0.9.0] - 2026-07-12

### Added

- **Domain OPM**: `hapus_opm_sesi` (`DELETE /opm/sesi/{id}`) dan
  `opm_hapus_responden` (`DELETE /opm/sesi/responden/{id}`) — sebelumnya OPM
  tidak punya tool MCP sama sekali. Sisa domain OPM (buat sesi, tambah
  responden, submit jawaban, analisis, hasil) tetap di luar lingkup — lihat
  `plan-lengkapi-delete-mcp.md`.
- **Time Study**: `daftar_ts_penugasan`, `buat_ts_penugasan`,
  `detail_ts_penugasan`, `perbarui_ts_penugasan`, `hapus_ts_penugasan` —
  menggantikan tool berbasis sesi yang sudah dihapus dari backend.

### Changed (Breaking)

- **Time Study**: backend menghapus konsep sesi TS (revisi 2026-07-04),
  digantikan penugasan per partisipan. Tool lama yang memanggil
  `/time-study/sesi/*` sudah 404 dan dihapus: `daftar_ts_sesi`, `buat_ts_sesi`,
  `ts_buka_sesi`, `ts_tutup_sesi`, `ts_tambah_responden`, `ts_analisis`,
  `detail_ts_sesi`, `perbarui_ts_sesi`, `hapus_ts_sesi`, `ts_daftar_responden`,
  `ts_hapus_responden`. `ts_daftar_log`, `ts_buat_log`, `ts_detail_log`, dan
  `ts_perbarui_log` dipertahankan tetapi parameter `responden_id` diganti
  `penugasan_id` (path berubah dari `/time-study/responden/{id}/log` menjadi
  `/time-study/penugasan/{id}/log`).

### Fixed

- Docstring `hapus_dcs_sesi`, `dcs_hapus_responden`, `hapus_ti_sesi`,
  `ti_hapus_responden`, `hapus_wcp_sesi`, `wcp_hapus_responden` kini menyatakan
  eksplisit bahwa tool ini hanya bisa dijalankan admin (backend menolak 403
  untuk token non-admin) — sebelumnya tidak disebutkan sehingga Claude bisa
  menyarankan pemakaiannya ke partisipan biasa.

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
