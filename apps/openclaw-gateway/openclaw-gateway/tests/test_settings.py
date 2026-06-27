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
        "upstream_timeout_seconds": 5.0,
    }


def test_settings_accept_valid_config():
    settings = GatewaySettings(**valid_settings_kwargs())

    assert settings.gateway_auth_token == "gateway-secret"
    assert str(settings.jellyfin_url) == "http://jellyfin:8096/"
    assert str(settings.jellyseerr_url) == "http://jellyseerr:5055/"
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
