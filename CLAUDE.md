# anjab-abk-mcp — MCP Server (ANJAB & ABK, Yayasan Pendidikan)

Ikhtisar & cara pakai (untuk manusia): lihat README.md.
Konteks domain (yayasan pendidikan, jenjang sekolah, struktur organisasi): lihat CLAUDE.md repo induk.

## Perintah

@Makefile

## Struktur / Arsitektur

**FastMCP Python** — satu server melayani stdio, Claude Code, dan Claude Web (HTTP/SSE).
MCP ini bertindak sebagai **adapter**: menerima permintaan Claude → memanggil REST API `anjab-abk-backend` → mengembalikan hasil.

```
src/anjab_abk_mcp/
├── __init__.py         # __version__ (sumber tunggal versi)
├── config.py           # pydantic-settings: transport, Authentik, backend URL
├── server.py           # FastMCP + definisi tools (docstring = deskripsi tool di Claude)
├── auth_provider.py    # Authentik Pola B (backend sudah Authentik — teruskan token user)
├── asgi.py             # ASGI wrapper (Starlette + /health + lifespan MCP)
├── client.py           # HTTP client ke anjab-abk-backend (Bearer forwarding)
└── __main__.py         # entrypoint: pilih transport via env (stdio/http)
tests/
├── test_server.py      # test tools in-memory FastMCP
├── test_auth.py        # test auth: token forwarding + error_code valid
├── test_config.py      # parse config dari env (format username dll)
└── test_asgi.py        # boot ASGI: /health + initialize di bawah lifespan
.github/workflows/
└── release.yml         # tag v* → GitHub Release + Docker image (GHCR)
```

- Entrypoint: `python -m anjab_abk_mcp`
- Backend: `anjab-abk-backend` via `BACKEND_BASE_URL` (REST API)
- Auth: Authentik **Pola B** — issuer/JWKS sama dengan backend, token user diteruskan

## Konvensi & Invariants

- **DCS & WCP adalah instrumen singleton (tanpa sesi)** — satu deployment backend = satu studi. Tool-tool domain ini (`dcs_*`, `wcp_*`) TIDAK menerima/menghasilkan `sesi_id`; status instrumen mengalir `OPEN -> CLOSED -> ANALYZED` lewat `dcs_instrumen`/`wcp_instrumen` + `*_tutup_instrumen` + `*_buka_ulang_instrumen`. **TI (Task Inventory) dan OPM tetap memakai sesi** (`sesi_id` wajib) — desain produk sengaja berbeda antar domain, jangan disamakan.
- **`*_buka_ulang_instrumen` vs `*_reset_instrumen` (DCS/WCP) adalah dua jalur berbeda, jangan tertukar.** `*_buka_ulang_instrumen` **non-destruktif**: sah dari `CLOSED` **dan** `ANALYZED` → `OPEN`, tidak menghapus data — inilah jalan membuka instrumen `ANALYZED`. `*_reset_instrumen` **destruktif**, admin-only, dan kini **hanya sah bila instrumen belum berisi jawaban** (selain itu 409 `instrument_has_responses`); BUKAN lagi jalan keluar dari `ANALYZED`. Hal sama: `*_hapus_item`/`*_perbarui_item` ditolak 409 `instrument_has_responses` bila sudah ada jawaban, dan `ti_catalog_purge` ditolak 409 `catalog_in_use` bila katalog dipakai sesi TI/OPM. Galat backend diteruskan lewat `_raise_tool_error` tanpa pemetaan baru; konfirmasi destruktif ada di level percakapan, bukan parameter tool.
- **Hasil WCP/DCS adalah union `mode`** (`SCORED` | `RAW_ONLY`, digerbang flag `WCP_DCS_SCORING`, dibaca lewat `fitur_status`). Saat `RAW_ONLY`, Claude dilarang menyimpulkan skor dimensi/sub-skala, label risiko, atau indeks gabungan dari data raw; `*_hasil_responden` menjawab 409 `scoring_key_not_approved` selama flag mati.
- **Tool AI dan narasi hanya metadata (K-16, `NO_SELF_AUTH`)**: `ai_saklar_status`, `ai_daftar_run`, `ai_detail_run` hanya membaca; `_tanpa_isi_run` membuang `masukan`/`keluaran`. Dilarang menambah tool yang mengubah saklar (`matikan`/`hidupkan`), memuat isi run/draf, atau menulis/meninjau narasi: MCP meneruskan token pengguna, sehingga tool tulis narasi melanggar `NO_SELF_AUTH`, dan membaca isi membuka jalur data di luar gerbang PII.
- **Register pengecualian OPM** (`opm_daftar_pengecualian`): task yang tak bisa dinilai dicatat dengan alasan `TI_DETAIL_UNMATCHED`/`OPM_STD_MISSING`/`OPM_RATING_MISSING` dan bernilai `null` di hasil; dilarang mengisi nilainya otomatis.
- **Identitas responden = `kode_orang`** (`O-nnnn`, pseudonim); respons responden tidak memuat nama.
- **Docstring fungsi tool = deskripsi tool yang dibaca Claude** — wajib informatif, dikelola skill `docstring` (Google style).
- `asgi.py` **wajib** membungkus MCP app dengan Starlette, menambah `/health`, dan mengoper `lifespan` ke Starlette — tanpa lifespan, setiap request MCP crash `RuntimeError: Task group is not initialized`.
- `TokenError` hanya boleh memakai error_code valid OAuth/MCP: `invalid_request`, `invalid_client`, `invalid_grant`, `unauthorized_client`, `unsupported_grant_type`, `invalid_scope` — kode lain memicu ValidationError.
- Config field `list[str]` dari env harus toleran format JSON array, comma-separated, dan nilai tunggal (patch kedua source: OS env **dan** file `.env`).
- Rilis **hanya via GitHub** (GitHub Release + Docker image ke GHCR) — tidak ke PyPI.
- Versi: sumber tunggal di `src/anjab_abk_mcp/__init__.py` (`__version__`).

## Jangan Sentuh

- `.github/workflows/release.yml` — workflow rilis otomatis; hanya diubah bila ada perubahan pipeline CI/CD eksplisit.
- Token user yang diterima — hanya diteruskan ke backend, **tidak** disimpan atau di-log.

## Gotcha

- `asgi.py` tanpa `lifespan=_mcp_app.lifespan` membuat container `unhealthy` dan setiap request MCP crash — ini pitfall paling umum saat membuat MCP baru.
- `BACKEND_BASE_URL` wajib di-set; tanpa itu semua tool gagal memanggil backend.
- Authentik Pola B: issuer dan audience harus identik dengan konfigurasi `anjab-abk-backend` — pastikan keduanya membaca dari Authentik instance yang sama.
- `make test` butuh Docker; tanpa Docker perintah gagal (test berjalan di dalam container, bukan di host).
- Format `AUTHENTIK_ALLOWED_USERNAMES` di `.env.example` dan kode harus sepakat (JSON array `["u1","u2"]`, comma-separated `u1,u2`, atau nilai tunggal `u1`).

## Alur Kerja & Definition of Done

- Sebelum lapor selesai: `make test` hijau (lint + unit) **dan** workflow `release.yml` terdaftar. Branch utama: `master`.
- Setiap tool/resource baru wajib punya docstring — gunakan skill `docstring`.
- Commit/branch/PR/tag → skill `git-workflow`; eksekusi `gh` → skill `github-cli-skill`.
- Gate test → skill `automated-test`; README → skill `readme`.

## Delegasi Skill

| Tugas | Skill |
|---|---|
| Scaffold MCP server (FastMCP, transport, auth Authentik, workflow rilis) | `mcp-development-skill` |
| Gate test (lint + unit, Makefile + Docker, lokal == CI, Python preset) | `automated-test-skill` |
| Docstring tool/resource/fungsi (Google style, deskripsi tool FastMCP) | `docstring-skill` |
| README.md (pintu depan repo, cara daftar ke Claude, auth, mode stdio) | `readme-skill` |
| Commit, branch, PR, tag/release semver, changelog | `git-workflow-skill` |
| Eksekusi perintah `gh` (release, Actions, API GitHub) | `github-cli-skill` |
| Orkestrasi deploy HTTP transport (Docker Compose + Traefik) | `copier-docker-compose-skill` |
