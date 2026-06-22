"""ASGI entrypoint untuk deployment HTTP (dipakai uvicorn / Docker).

Auth sudah menempel pada objek ``mcp`` (lihat server.py). Modul ini membungkus MCP
app dengan transport Streamable HTTP — kompatibel dengan Claude Web (claude.ai)
sebagai remote MCP server — lalu menambah endpoint ``/health`` untuk health check
container.

Jalankan:
    uvicorn anjab_abk_mcp.asgi:app --host 0.0.0.0 --port 8000

PENTING — dua hal yang WAJIB benar saat membungkus MCP app dalam Starlette:

1. ``lifespan=_mcp_app.lifespan`` HARUS dioper ke Starlette. Tanpa itu,
   ``StreamableHTTPSessionManager`` milik MCP tidak pernah diinisialisasi, sehingga
   setiap request MCP yang lolos auth langsung crash dengan
   ``RuntimeError: Task group is not initialized``.
2. Endpoint ``/health`` perlu ditambah sendiri karena ``mcp.http_app()`` tidak
   menyediakannya. Tanpa ini, health check Docker/Compose selalu ``unhealthy``.
"""

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .server import mcp

logger = logging.getLogger(__name__)


async def health(request: Request) -> JSONResponse:
    """Health check ringan untuk Docker/Compose — tidak menyentuh MCP/auth."""
    return JSONResponse({"status": "ok"})


_mcp_app = mcp.http_app()

# lifespan WAJIB dioper agar StreamableHTTPSessionManager terinisialisasi (lihat docstring).
app = Starlette(
    lifespan=_mcp_app.lifespan,
    routes=[
        Route("/health", health),
        Mount("/", app=_mcp_app),
    ],
)
logger.info("ASGI app siap (Streamable HTTP + /health)")
