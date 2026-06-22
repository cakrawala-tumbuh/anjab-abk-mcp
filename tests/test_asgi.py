"""Smoke test ASGI app (Streamable HTTP + /health).

Menjaga dua regresi yang pernah membuat deployment gagal di produksi:

1. ``/health`` HARUS ada — kalau hilang, health check Docker/Compose selalu
   ``unhealthy`` (``mcp.http_app()`` tidak menyediakan endpoint ini).
2. ``lifespan`` MCP HARUS dioper ke Starlette — kalau tidak, request MCP pertama
   yang lolos auth crash ``RuntimeError: Task group is not initialized``.

``TestClient`` dipakai sebagai context manager agar lifespan (startup/shutdown)
ikut dijalankan — itulah yang menginisialisasi ``StreamableHTTPSessionManager``.

Catatan: test ini mengasumsikan TIDAK ada env auth (``AUTHENTIK_*`` / ``MCP_API_KEY``),
sama seperti gate test di Docker/CI, sehingga request ``initialize`` tidak terblokir
auth dan benar-benar mencapai session manager.
"""

from starlette.testclient import TestClient

from anjab_abk_mcp.asgi import app


def test_health_ok():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_mcp_initialize_tidak_crash_task_group():
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0"},
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    with TestClient(app) as client:
        resp = client.post("/mcp", json=payload, headers=headers, follow_redirects=True)
    # Bila lifespan tidak dioper, request ini raise RuntimeError "Task group is not
    # initialized" (atau balas 500). Status 200 = session manager hidup.
    assert resp.status_code == 200, resp.text
