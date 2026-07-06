#!/usr/bin/env bash
set -euo pipefail

gateway_url="${1:-${GATEWAY_URL:-}}"
gateway_token="${2:-${GATEWAY_AUTH_TOKEN:-}}"

if [[ -z "${gateway_url}" ]]; then
  echo "Usage: $0 <gateway-url> <gateway-token>" >&2
  echo "Or set GATEWAY_URL and GATEWAY_AUTH_TOKEN." >&2
  exit 2
fi

if [[ -z "${gateway_token}" ]]; then
  echo "Missing gateway token." >&2
  exit 2
fi

health_status="$(curl -sS -o /dev/null -w "%{http_code}" "${gateway_url%/}/health")"
if [[ "${health_status}" != "200" ]]; then
  echo "Health check failed with HTTP ${health_status}." >&2
  exit 1
fi

search_status="$(
  curl -sS \
    -o /dev/null \
    -w "%{http_code}" \
    -H "Authorization: Bearer ${gateway_token}" \
    "${gateway_url%/}/v1/media/jellyfin/search?q=smoke"
)"

if [[ "${search_status}" != "200" ]]; then
  echo "Authenticated Jellyfin search failed with HTTP ${search_status}." >&2
  exit 1
fi

ryot_probe_status="$(
  curl -sS \
    -o /tmp/openclaw-gateway-ryot-probe.json \
    -w "%{http_code}" \
    -H "Authorization: Bearer ${gateway_token}" \
    "${gateway_url%/}/v1/media/ryot/probe"
)"

if [[ "${ryot_probe_status}" != "200" ]]; then
  echo "Authenticated Ryot probe failed with HTTP ${ryot_probe_status}." >&2
  exit 1
fi

if [[ "${CHECK_ARR_ENDPOINTS:-0}" == "1" ]]; then
  sonarr_status="$(
    curl -sS \
      -o /dev/null \
      -w "%{http_code}" \
      -H "Authorization: Bearer ${gateway_token}" \
      "${gateway_url%/}/v1/media/sonarr/series"
  )"

  if [[ "${sonarr_status}" != "200" ]]; then
    echo "Authenticated Sonarr series check failed with HTTP ${sonarr_status}." >&2
    exit 1
  fi

  radarr_status="$(
    curl -sS \
      -o /dev/null \
      -w "%{http_code}" \
      -H "Authorization: Bearer ${gateway_token}" \
      "${gateway_url%/}/v1/media/radarr/movies"
  )"

  if [[ "${radarr_status}" != "200" ]]; then
    echo "Authenticated Radarr movies check failed with HTTP ${radarr_status}." >&2
    exit 1
  fi
fi

if [[ "${CHECK_JELLYSEERR_REQUESTS:-0}" == "1" ]]; then
  jellyseerr_request_status="$(
    curl -sS \
      -o /dev/null \
      -w "%{http_code}" \
      -X POST \
      -H "Authorization: Bearer ${gateway_token}" \
      -H "Content-Type: application/json" \
      --data-raw '{"media_type":"movie","tmdb_id":348,"note":"OpenClaw gateway smoke dry-run","dry_run":true}' \
      "${gateway_url%/}/v1/media/jellyseerr/requests"
  )"

  if [[ "${jellyseerr_request_status}" != "200" ]]; then
    echo "Authenticated Jellyseerr request dry-run failed with HTTP ${jellyseerr_request_status}." >&2
    exit 1
  fi
fi

if [[ "${CHECK_N8N_SMOKE:-0}" == "1" ]]; then
  n8n_status="$(
    curl -sS \
      -o /dev/null \
      -w "%{http_code}" \
      -X POST \
      -H "Authorization: Bearer ${gateway_token}" \
      "${gateway_url%/}/v1/automation/n8n/openclaw-smoke"
  )"

  if [[ "${n8n_status}" != "200" ]]; then
    echo "Authenticated n8n smoke check failed with HTTP ${n8n_status}." >&2
    exit 1
  fi
fi

echo "OpenClaw gateway smoke test passed."
