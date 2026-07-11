FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY openclaw_gateway /app/openclaw_gateway
COPY openclaw_plane_sdk /app/openclaw_plane_sdk
RUN pip install --no-cache-dir "."

EXPOSE 8080

CMD ["uvicorn", "openclaw_gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
