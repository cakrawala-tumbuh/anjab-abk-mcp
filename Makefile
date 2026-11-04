################################################################################
# Makefile — Automated Test (anjab-abk-mcp, Python/FastMCP)
#
# Prinsip:
#  - SEMUA test (lint + unit) berjalan DI DALAM Docker.
#  - Perintah yang sama (`make test`) dipakai di LOKAL maupun di GitHub Actions
#    → tidak mungkin ada perbedaan antara lokal dan CI.
#  - Source di-COPY ke image (bukan bind-mount), sehingga TIDAK ADA artefak test
#    (coverage, __pycache__, .pytest_cache, dll) yang tertulis ke folder project.
################################################################################

IMAGE_NAME ?= $(shell basename $(CURDIR))-test
DOCKERFILE ?= Dockerfile.test
DOCKER_RUN  = docker run --rm $(IMAGE_NAME)

.DEFAULT_GOAL := test
.PHONY: build lint unit test test-arm64 clean shell help

## help: tampilkan daftar target
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed -e 's/## //'

## build: bangun image test (deps + tooling + source)
build:
	docker build -f $(DOCKERFILE) -t $(IMAGE_NAME) .

## lint: jalankan ruff check + ruff format check di dalam container
lint: build
	$(DOCKER_RUN) sh -c "ruff check . && ruff format --check ."

## unit: jalankan pytest di dalam container
unit: build
	$(DOCKER_RUN) pytest

## test: gate lengkap = lint + unit. Dipakai LOKAL dan CI (identik).
test: lint unit

## test-arm64: uji asap image RUNTIME linux/arm64 (uname -m = aarch64 + HEALTHCHECK healthy <= 60 dtk)
## Terpisah dari `make test` agar gerbang utama tetap cepat. Di host x86_64 butuh QEMU/binfmt arm64;
## di CI dijalankan native pada runner ubuntu-24.04-arm. Kontainer berjalan dengan --rm,
## jadi cukup di-stop untuk dibersihkan.
ARM64_IMAGE ?= $(shell basename $(CURDIR))-arm64-smoke
ARM64_CONTAINER ?= $(ARM64_IMAGE)-run
test-arm64:
	docker buildx build --platform linux/arm64 --load -f Dockerfile -t $(ARM64_IMAGE) .
	docker run -d --rm --name $(ARM64_CONTAINER) --platform linux/arm64 \
		-e BACKEND_BASE_URL=http://backend.invalid:8001 $(ARM64_IMAGE) >/dev/null
	@arch=$$(docker exec $(ARM64_CONTAINER) uname -m); \
	echo "uname -m = $$arch"; \
	if [ "$$arch" != "aarch64" ]; then echo "GAGAL: arsitektur bukan aarch64"; \
		docker stop -t 1 $(ARM64_CONTAINER) >/dev/null; exit 1; fi
	@status=none; i=0; \
	while [ $$i -lt 60 ]; do \
		status=$$(docker inspect -f '{{.State.Health.Status}}' $(ARM64_CONTAINER) 2>/dev/null); \
		[ "$$status" = "healthy" ] && break; \
		i=$$((i+1)); sleep 1; \
	done; \
	echo "HEALTHCHECK status = $$status (setelah $$i dtk)"; \
	if [ "$$status" != "healthy" ]; then docker logs $(ARM64_CONTAINER) 2>&1 | tail -30; fi; \
	docker stop -t 1 $(ARM64_CONTAINER) >/dev/null; \
	[ "$$status" = "healthy" ]

## clean: hapus image test
clean:
	-docker rmi $(IMAGE_NAME)

## shell: masuk ke shell container test (debugging)
shell: build
	docker run --rm -it $(IMAGE_NAME) sh
