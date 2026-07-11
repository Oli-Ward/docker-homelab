from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_auth_token: Annotated[str, Field(min_length=1, pattern=r"^[\x21-\x7E]+$")]
    jellyfin_url: AnyHttpUrl
    jellyfin_api_key: Annotated[str, Field(min_length=1)]
    seerr_url: AnyHttpUrl
    seerr_api_key: Annotated[str, Field(min_length=1)]
    sonarr_url: AnyHttpUrl
    sonarr_api_key: Annotated[str, Field(min_length=1)]
    radarr_url: AnyHttpUrl
    radarr_api_key: Annotated[str, Field(min_length=1)]
    ryot_url: AnyHttpUrl
    ryot_admin_access_token: Annotated[str, Field(min_length=1)]
    plane_api_base_url: AnyHttpUrl
    plane_api_key: Annotated[str, Field(min_length=1)]
    plane_workspace_slug: Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")]
    plane_default_project_id: str | None = None
    plane_webhook_secret: str | None = None
    plane_webhook_queue_path: str = "/app/state/plane-webhooks/events.jsonl"
    plane_webhook_dedupe_path: str | None = None
    plane_webhook_ignored_actor_ids: str = ""
    n8n_webhook_base_url: AnyHttpUrl
    n8n_openclaw_smoke_path: Annotated[
        str,
        Field(min_length=1, pattern=r"^/webhook/[A-Za-z0-9._~!$&'()*+,;=:@/-]+$"),
    ]
    n8n_jellyfin_rating_prompt_path: Annotated[
        str,
        Field(min_length=1, pattern=r"^/webhook/[A-Za-z0-9._~!$&'()*+,;=:@/-]+$"),
    ] = "/webhook/jellyfin-rating-prompt"
    upstream_timeout_seconds: Annotated[float, Field(gt=0)] = 5.0

    def plane_webhook_ignored_actor_id_set(self) -> set[str]:
        return {
            actor_id.strip()
            for actor_id in self.plane_webhook_ignored_actor_ids.split(",")
            if actor_id.strip()
        }


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
