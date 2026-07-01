import pytest
from pydantic import ValidationError

from openclaw_gateway.settings import GatewaySettings


def valid_settings_kwargs() -> dict[str, str | float]:
    return {
        "gateway_auth_token": "gateway-secret",
        "jellyfin_url": "http://jellyfin:8096",
        "jellyfin_api_key": "jellyfin-secret",
        "jellyseerr_url": "http://jellyseerr:5055",
        "jellyseerr_api_key": "jellyseerr-secret",
        "sonarr_url": "http://sonarr:8989",
        "sonarr_api_key": "sonarr-secret",
        "radarr_url": "http://radarr:7878",
        "radarr_api_key": "radarr-secret",
        "n8n_webhook_base_url": "http://n8n:5678",
        "n8n_jellyfin_rating_prompt_path": "/webhook/jellyfin-rating-prompt",
        "upstream_timeout_seconds": 5.0,
    }


def test_settings_accept_valid_config():
    settings = GatewaySettings(**valid_settings_kwargs())

    assert settings.gateway_auth_token == "gateway-secret"
    assert str(settings.jellyfin_url) == "http://jellyfin:8096/"
    assert str(settings.jellyseerr_url) == "http://jellyseerr:5055/"
    assert str(settings.sonarr_url) == "http://sonarr:8989/"
    assert str(settings.radarr_url) == "http://radarr:7878/"
    assert str(settings.n8n_webhook_base_url) == "http://n8n:5678/"
    assert settings.n8n_jellyfin_rating_prompt_path == "/webhook/jellyfin-rating-prompt"
    assert settings.upstream_timeout_seconds == 5.0


def test_settings_reject_missing_gateway_token():
    kwargs = valid_settings_kwargs()
    kwargs["gateway_auth_token"] = ""

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)


def test_settings_reject_non_ascii_gateway_token():
    kwargs = valid_settings_kwargs()
    kwargs["gateway_auth_token"] = "gateway-secrēt"

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)
