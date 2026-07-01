import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "smoke-openclaw-gateway.sh"


def write_fake_curl(
    tmp_path: Path,
    sonarr_status: str = "200",
    radarr_status: str = "200",
    n8n_status: str = "200",
    jellyseerr_request_status: str = "200",
) -> Path:
    curl = tmp_path / "curl"
    log = tmp_path / "curl.log"
    curl.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail

printf '%s\\n' "$*" >> "{log}"

has_fail=0
for arg in "$@"; do
  if [[ "$arg" == "-f"* ]]; then
    has_fail=1
  fi
done

url="${{@: -1}}"
case "$url" in
  */health)
    printf "200"
    ;;
  */v1/media/jellyfin/search*)
    printf "200"
    ;;
  */v1/media/sonarr/series)
    if [[ "$has_fail" == "1" && "{sonarr_status}" -ge 400 ]]; then
      echo "curl: (22) The requested URL returned error: {sonarr_status}" >&2
      exit 22
    fi
    printf "{sonarr_status}"
    ;;
  */v1/media/radarr/movies)
    if [[ "$has_fail" == "1" && "{radarr_status}" -ge 400 ]]; then
      echo "curl: (22) The requested URL returned error: {radarr_status}" >&2
      exit 22
    fi
    printf "{radarr_status}"
    ;;
  */v1/media/jellyseerr/requests)
    if [[ "$has_fail" == "1" && "{jellyseerr_request_status}" -ge 400 ]]; then
      echo "curl: (22) The requested URL returned error: {jellyseerr_request_status}" >&2
      exit 22
    fi
    printf "{jellyseerr_request_status}"
    ;;
  */v1/automation/n8n/openclaw-smoke)
    if [[ "$has_fail" == "1" && "{n8n_status}" -ge 400 ]]; then
      echo "curl: (22) The requested URL returned error: {n8n_status}" >&2
      exit 22
    fi
    printf "{n8n_status}"
    ;;
  *)
    echo "unexpected URL: $url" >&2
    exit 99
    ;;
esac
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    return curl


def smoke_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    env["GATEWAY_URL"] = "http://gateway.example"
    env["GATEWAY_AUTH_TOKEN"] = "gateway-secret"
    env["CHECK_ARR_ENDPOINTS"] = "1"
    return env


def test_smoke_script_reports_sonarr_http_status(tmp_path: Path):
    write_fake_curl(tmp_path, sonarr_status="404")

    result = subprocess.run(
        [str(SMOKE_SCRIPT)],
        cwd=REPO_ROOT,
        env=smoke_env(tmp_path),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Authenticated Sonarr series check failed with HTTP 404." in result.stderr


def test_smoke_script_can_check_jellyseerr_request_dry_run(tmp_path: Path):
    write_fake_curl(tmp_path, jellyseerr_request_status="200")
    env = smoke_env(tmp_path)
    env["CHECK_JELLYSEERR_REQUESTS"] = "1"

    result = subprocess.run(
        [str(SMOKE_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    curl_log = (tmp_path / "curl.log").read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "OpenClaw gateway smoke test passed." in result.stdout
    assert "/v1/media/jellyseerr/requests" in curl_log
    assert '"media_type":"movie"' in curl_log
    assert '"tmdb_id":348' in curl_log
    assert '"dry_run":true' in curl_log
    assert "gateway-secret" not in result.stdout
    assert "gateway-secret" not in result.stderr


def test_smoke_script_reports_jellyseerr_request_dry_run_http_status(tmp_path: Path):
    write_fake_curl(tmp_path, jellyseerr_request_status="404")
    env = smoke_env(tmp_path)
    env["CHECK_JELLYSEERR_REQUESTS"] = "1"

    result = subprocess.run(
        [str(SMOKE_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Authenticated Jellyseerr request dry-run failed with HTTP 404." in result.stderr
    assert "gateway-secret" not in result.stdout
    assert "gateway-secret" not in result.stderr


def test_smoke_script_can_check_n8n_smoke_route(tmp_path: Path):
    write_fake_curl(tmp_path, n8n_status="200")
    env = smoke_env(tmp_path)
    env["CHECK_N8N_SMOKE"] = "1"

    result = subprocess.run(
        [str(SMOKE_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "OpenClaw gateway smoke test passed." in result.stdout


def test_smoke_script_reports_n8n_smoke_http_status(tmp_path: Path):
    write_fake_curl(tmp_path, n8n_status="404")
    env = smoke_env(tmp_path)
    env["CHECK_N8N_SMOKE"] = "1"

    result = subprocess.run(
        [str(SMOKE_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Authenticated n8n smoke check failed with HTTP 404." in result.stderr
