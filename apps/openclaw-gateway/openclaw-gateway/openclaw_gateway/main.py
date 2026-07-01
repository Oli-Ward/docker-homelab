from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from openclaw_gateway.routers.automation import build_automation_router
from openclaw_gateway.routers.media import build_media_router
from openclaw_gateway.settings import GatewaySettings, get_settings


def _include_gateway_routers(app: FastAPI, settings: GatewaySettings) -> None:
    if getattr(app.state, "gateway_routers_included", False):
        return

    app.include_router(build_media_router(settings))
    app.include_router(build_automation_router(settings))
    app.state.gateway_routers_included = True


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    if settings is None:

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncIterator[None]:
            app.state.settings = get_settings()
            _include_gateway_routers(app, app.state.settings)
            yield

        app = FastAPI(title="OpenClaw Gateway", version="0.1.0", lifespan=lifespan)
    else:
        app = FastAPI(title="OpenClaw Gateway", version="0.1.0")
        app.state.settings = settings
        _include_gateway_routers(app, settings)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
