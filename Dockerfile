# syntax=docker/dockerfile:1.7

# Dependencias aisladas: pip corre como usuario sin privilegios dentro de un venv.
FROM python:3.11-slim AS builder

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home appuser \
    && python -m venv "$VIRTUAL_ENV" \
    && chown -R appuser:appgroup "$VIRTUAL_ENV"

USER appuser
COPY --chown=appuser:appgroup requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-compile --upgrade pip \
    && python -m pip install --no-compile -r /tmp/requirements.txt

FROM python:3.11-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5002

RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home appuser

COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv

WORKDIR /app
COPY --chown=appuser:appgroup . /app

# Evita `/bin/sh\r: not found` aunque el checkout se haya hecho en Windows.
RUN sed -i 's/\r$//' /app/scripts/*.sh \
    && chmod 0555 /app/scripts/*.sh \
    && install -d -o appuser -g appgroup -m 0750 /app/logs /app/tmp

USER appuser:appgroup

EXPOSE 5002

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5002/health', timeout=5)"]

ENTRYPOINT ["/app/scripts/init.sh"]
