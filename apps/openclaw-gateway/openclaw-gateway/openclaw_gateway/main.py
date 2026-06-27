from fastapi import FastAPI

from openclaw_gateway.settings import GatewaySettings, get_settings


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title="OpenClaw Gateway", version="0.1.0")
    app.state.settings = app_settings

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
