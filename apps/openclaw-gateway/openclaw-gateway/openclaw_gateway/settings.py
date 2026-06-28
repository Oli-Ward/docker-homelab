from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_auth_token: Annotated[str, Field(min_length=1, pattern=r"^[\x21-\x7E]+$")]
    jellyfin_url: AnyHttpUrl
    jellyfin_api_key: Annotated[str, Field(min_length=1)]
    jellyseerr_url: AnyHttpUrl
    jellyseerr_api_key: Annotated[str, Field(min_length=1)]
    sonarr_url: AnyHttpUrl
    sonarr_api_key: Annotated[str, Field(min_length=1)]
    radarr_url: AnyHttpUrl
    radarr_api_key: Annotated[str, Field(min_length=1)]
    upstream_timeout_seconds: Annotated[float, Field(gt=0)] = 5.0


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
