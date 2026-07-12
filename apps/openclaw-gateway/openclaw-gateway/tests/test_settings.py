import pytest
from pydantic import ValidationError

from openclaw_gateway.settings import GatewaySettings


def valid_settings_kwargs() -> dict[str, str | float]:
    return {
        "gateway_auth_token": "gateway-secret",
        "jellyfin_url": "http://jellyfin:8096",
        "jellyfin_api_key": "jellyfin-secret",
        "seerr_url": "http://seerr:5055",
        "seerr_api_key": "seerr-secret",
        "sonarr_url": "http://sonarr:8989",
        "sonarr_api_key": "sonarr-secret",
        "radarr_url": "http://radarr:7878",
        "radarr_api_key": "radarr-secret",
        "ryot_url": "http://ryot:8000",
        "ryot_admin_access_token": "ryot-secret",
        "plane_api_base_url": "http://192.168.1.103:8085",
        "plane_api_key": "plane-secret",
        "plane_workspace_slug": "openclaw",
        "n8n_webhook_base_url": "http://n8n:5678",
        "n8n_openclaw_smoke_path": "/webhook/openclaw-smoke",
        "upstream_timeout_seconds": 5.0,
    }


def test_settings_accept_valid_config():
    settings = GatewaySettings(**valid_settings_kwargs())

    assert settings.gateway_auth_token == "gateway-secret"
    assert str(settings.jellyfin_url) == "http://jellyfin:8096/"
    assert str(settings.seerr_url) == "http://seerr:5055/"
    assert str(settings.sonarr_url) == "http://sonarr:8989/"
    assert str(settings.radarr_url) == "http://radarr:7878/"
    assert str(settings.ryot_url) == "http://ryot:8000/"
    assert settings.ryot_admin_access_token == "ryot-secret"
    assert str(settings.plane_api_base_url) == "http://192.168.1.103:8085/"
    assert settings.plane_api_key == "plane-secret"
    assert settings.plane_workspace_slug == "openclaw"
    assert settings.plane_default_project_id is None
    assert settings.plane_webhook_secret is None
    assert settings.plane_webhook_queue_backend == "redis"
    assert settings.plane_webhook_redis_url == "redis://redis:6379/0"
    assert settings.plane_webhook_redis_prefix == "openclaw:plane:webhooks"
    assert settings.plane_webhook_max_attempts == 5
    assert settings.plane_webhook_retry_base_seconds == 30
    assert settings.plane_webhook_retry_max_seconds == 1800
    assert settings.plane_webhook_queue_path == "/app/state/plane-webhooks/events.jsonl"
    assert settings.plane_webhook_dedupe_path is None
    assert settings.plane_webhook_ignored_actor_ids == ""
    assert settings.plane_webhook_ignored_actor_id_set() == set()
    assert str(settings.n8n_webhook_base_url) == "http://n8n:5678/"
    assert settings.n8n_openclaw_smoke_path == "/webhook/openclaw-smoke"
    assert settings.n8n_plane_webhook_dispatch_path == "/webhook/plane-openclaw-dispatch"
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


def test_settings_reject_empty_n8n_smoke_path():
    kwargs = valid_settings_kwargs()
    kwargs["n8n_openclaw_smoke_path"] = ""

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)


def test_settings_reject_non_webhook_n8n_smoke_path():
    kwargs = valid_settings_kwargs()
    kwargs["n8n_openclaw_smoke_path"] = "/api/v1/workflows"

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)


def test_settings_reject_non_webhook_plane_dispatch_path():
    kwargs = valid_settings_kwargs()
    kwargs["n8n_plane_webhook_dispatch_path"] = "/api/v1/workflows"

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)


def test_settings_reject_empty_ryot_admin_access_token():
    kwargs = valid_settings_kwargs()
    kwargs["ryot_admin_access_token"] = ""

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)


def test_settings_reject_empty_plane_api_key():
    kwargs = valid_settings_kwargs()
    kwargs["plane_api_key"] = ""

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)


def test_settings_reject_empty_plane_workspace_slug():
    kwargs = valid_settings_kwargs()
    kwargs["plane_workspace_slug"] = ""

    with pytest.raises(ValidationError):
        GatewaySettings(**kwargs)


def test_settings_accept_empty_plane_webhook_secret_as_disabled():
    kwargs = valid_settings_kwargs()
    kwargs["plane_webhook_secret"] = ""

    settings = GatewaySettings(**kwargs)

    assert settings.plane_webhook_secret == ""


def test_settings_parses_plane_webhook_ignored_actor_ids():
    kwargs = valid_settings_kwargs()
    kwargs["plane_webhook_ignored_actor_ids"] = " automation-user-1, codex-user-1,, "

    settings = GatewaySettings(**kwargs)

    assert settings.plane_webhook_ignored_actor_id_set() == {
        "automation-user-1",
        "codex-user-1",
    }


def test_plane_webhook_queue_backend_accepts_file_for_local_development() -> None:
    kwargs = valid_settings_kwargs()
    kwargs["plane_webhook_queue_backend"] = "file"

    settings = GatewaySettings(**kwargs)

    assert settings.plane_webhook_queue_backend == "file"
