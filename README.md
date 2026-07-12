# anjab-abk-mcp

MCP Server untuk **ANJAB** (Analisis Jabatan) dan **ABK** (Analisis Beban Kerja) yayasan pendidikan.

Server ini bertindak sebagai adapter antara Claude dan REST API [`anjab-abk-backend`](https://github.com/cakrawala-tumbuh/anjab-abk-backend), mengekspos tools untuk mengelola data dan sesi studi ANJAB/ABK.

## Fitur

- Tools untuk data inti: jenjang pendidikan, sekolah, jabatan, partisipan, SME panel
- Tools untuk alat ukur **Task Inventory** (TI): sesi 3 tahap, responden, hasil
- Tools untuk alat ukur **DCS** (Dimension Classification Survey): instrumen singleton (tanpa sesi) — satu deployment = satu studi
- Tools untuk alat ukur **WCP** (Work Characteristics Profile): instrumen singleton (tanpa sesi) — satu deployment = satu studi
- Tools untuk alat ukur **Time Study** (TS)
- Auth via Authentik OAuth (Pola B) + API key statis
- Mendukung stdio, Claude Code (remote), dan Claude Web (HTTP/SSE)

## Konfigurasi MCP Client

### stdio (Claude Desktop / Claude Code lokal)

```json
{
  "mcpServers": {
    "anjab-abk": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/cakrawala-tumbuh/anjab-abk-mcp", "anjab-abk-mcp"],
      "env": {
        "BACKEND_BASE_URL": "https://api.anjab.example.com",
        "BACKEND_API_TOKEN": "<token-service-account>"
      }
    }
  }
}
```

### Docker (HTTP / Claude Web)

```bash
docker run -d \
  -p 8000:8000 \
  -e BACKEND_BASE_URL=https://api.anjab.example.com \
  -e MCP_BASE_URL=https://mcp.anjab.example.com \
  -e AUTHENTIK_ISSUER_URL=https://auth.example.com/application/o/anjab-abk/ \
  -e AUTHENTIK_CLIENT_ID=<client-id> \
  -e AUTHENTIK_CLIENT_SECRET=<client-secret> \
  ghcr.io/cakrawala-tumbuh/anjab-abk-mcp:latest
```

## Konfigurasi Lengkap

Salin `.env.example` menjadi `.env` dan isi nilainya:

```bash
cp .env.example .env
```

## Lisensi

MIT © Cakrawala Tumbuh
