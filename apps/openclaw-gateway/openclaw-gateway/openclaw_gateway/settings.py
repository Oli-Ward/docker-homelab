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


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
