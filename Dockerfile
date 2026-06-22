# Image RUNTIME server MCP (bukan image test — itu milik skill `automated-test`).
# Ramping, deterministik, dan berjalan sebagai user non-root.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install paket dari source. README.md ikut di-COPY karena direferensikan
# sebagai `readme` di pyproject.toml (tanpa itu `pip install .` gagal).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install . \
    && useradd --create-home --uid 1000 appuser

USER appuser

# Jalan sebagai service HTTP (Streamable HTTP) via uvicorn — kompatibel Claude Web.
# Auth Authentik diatur lewat environment (lihat .env.example).
ENV MCP_LOG_LEVEL=INFO
EXPOSE 8000

# Health check via endpoint /health milik asgi.py (python urllib — image slim tanpa curl).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "anjab_abk_mcp.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
