# Stage 1: Builder
# Must match the runtime's Python (3.13) and glibc (Debian 13) so wheels load.
FROM python:3.13-slim-trixie AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .

RUN pip install --only-binary=:all: --no-compile \
    --target=/opt/packages -r requirements.txt \
    && rm -rf /opt/packages/bin \
    && find /opt/packages -depth -type d \
    \( -name __pycache__ -o -name tests -o -name test \) -exec rm -rf {} + \
    && find /opt/packages -name '*.pyi' -delete


# Stage 2: Distroless runtime
FROM gcr.io/distroless/python3-debian13:nonroot

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/packages \
    FASTMCP_TRANSPORT=http \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000 \
    FASTMCP_SHOW_SERVER_BANNER=false

WORKDIR /app

COPY --from=builder /opt/packages /opt/packages
COPY LICENSE server.py ./

EXPOSE 8000

ENTRYPOINT ["python3", "server.py"]
