FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir "."

COPY openclaw_gateway /app/openclaw_gateway

EXPOSE 8080

CMD ["uvicorn", "openclaw_gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
