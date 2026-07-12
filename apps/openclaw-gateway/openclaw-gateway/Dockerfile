FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY packages/openclaw-plane-sdk /build/openclaw-plane-sdk
RUN pip install --no-cache-dir /build/openclaw-plane-sdk

COPY apps/openclaw-gateway/openclaw-gateway/pyproject.toml /app/pyproject.toml
COPY apps/openclaw-gateway/openclaw-gateway/openclaw_gateway /app/openclaw_gateway
RUN pip install --no-cache-dir "."

EXPOSE 8080

CMD ["uvicorn", "openclaw_gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
