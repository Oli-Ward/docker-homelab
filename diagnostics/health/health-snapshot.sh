#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: diagnostics/health/health-snapshot.sh <job-slug> -- <command> [args...]

Writes diagnostics/health/YYYY-MM-DD-<job-slug>.md with Before, Command/job run,
After, Diff / observations, and Recommendation / follow-up sections.

The checks are read-only and intentionally avoid environment dumps, Docker
inspect environment output, secret files, and full service logs.
USAGE
}

if [[ $# -lt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

job_slug=$1
shift

if [[ ! "$job_slug" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid job slug: $job_slug" >&2
  echo "Use only letters, numbers, dots, underscores, and hyphens." >&2
  exit 2
fi

if [[ "${1:-}" != "--" ]]; then
  usage >&2
  exit 2
fi
shift

if [[ $# -eq 0 ]]; then
  echo "Missing command to run after --" >&2
  usage >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
output_dir=$script_dir
report_path="$output_dir/$(date +%F)-$job_slug.md"

quote_command() {
  printf '%q ' "$@"
}

append_fenced_command() {
  local label=$1
  shift

  {
    printf '### `%s`\n\n' "$label"
    printf '```text\n'
  } >> "$report_path"

  if "$@" >> "$report_path" 2>&1; then
    printf '```\n\n' >> "$report_path"
  else
    local status=$?
    {
      printf '\n[command exited %s]\n' "$status"
      printf '```\n\n'
    } >> "$report_path"
  fi
}

append_note() {
  local label=$1
  local note=$2

  {
    printf '### `%s`\n\n' "$label"
    printf '```text\n%s\n```\n\n' "$note"
  } >> "$report_path"
}

collect_health() {
  append_fenced_command "date -Iseconds" date -Iseconds

  if command -v hostnamectl >/dev/null 2>&1; then
    append_fenced_command "hostnamectl --static" hostnamectl --static
  elif command -v hostname >/dev/null 2>&1; then
    append_fenced_command "hostname" hostname
  else
    append_note "hostname" "hostname command unavailable"
  fi

  if command -v systemd-detect-virt >/dev/null 2>&1; then
    append_fenced_command "systemd-detect-virt" systemd-detect-virt
  else
    append_note "systemd-detect-virt" "systemd-detect-virt command unavailable"
  fi

  if command -v uptime >/dev/null 2>&1; then
    append_fenced_command "uptime" uptime
  else
    append_note "uptime" "uptime command unavailable"
  fi

  if command -v free >/dev/null 2>&1; then
    append_fenced_command "free -h" free -h
  else
    append_note "free -h" "free command unavailable"
  fi

  if command -v df >/dev/null 2>&1; then
    append_fenced_command "df -h" df -h
  else
    append_note "df -h" "df command unavailable"
  fi

  if command -v docker >/dev/null 2>&1; then
    append_fenced_command "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}'" \
      docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}'
    append_fenced_command "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'" \
      docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
  else
    append_note "docker stats --no-stream" "docker command unavailable; skip Docker checks on non-Docker hosts"
    append_note "docker ps" "docker command unavailable; skip Docker checks on non-Docker hosts"
  fi

  if command -v ps >/dev/null 2>&1 && command -v head >/dev/null 2>&1; then
    append_fenced_command "ps aux --sort=-%mem | head -n 20" bash -c "ps aux --sort=-%mem | head -n 20"
  else
    append_note "ps aux --sort=-%mem | head -n 20" "ps or head command unavailable"
  fi

  if command -v systemctl >/dev/null 2>&1; then
    append_fenced_command "systemctl --failed" systemctl --failed
  else
    append_note "systemctl --failed" "systemctl command unavailable; skip failed-unit checks"
  fi

  if command -v journalctl >/dev/null 2>&1; then
    append_fenced_command "journalctl -p warning..alert -n 100 --no-pager" \
      journalctl -p warning..alert -n 100 --no-pager
  else
    append_note "journalctl -p warning..alert -n 100 --no-pager" "journalctl command unavailable; skip recent warning/error checks"
  fi
}

command_text=$(quote_command "$@")
started_at=$(date -Iseconds)

cat > "$report_path" <<EOF
# Health snapshot: $job_slug

- Started at: \`$started_at\`
- Captured from: \`$(hostname 2>/dev/null || printf 'unknown')\`
- Job command: \`$command_text\`
- Safety: read-only health checks only; no secrets, full environment output, Docker inspect env output, or full service logs.

## Before

EOF

collect_health

{
  printf '## Command/job run\n\n'
  printf -- '- Started at: `%s`\n\n' "$(date -Iseconds)"
  printf '```text\n'
} >> "$report_path"

set +e
"$@" >> "$report_path" 2>&1
job_status=$?
set -e

{
  printf '```\n\n'
  printf -- '- Finished at: `%s`\n' "$(date -Iseconds)"
  printf -- '- Exit code: `%s`\n\n' "$job_status"
  printf '## After\n\n'
} >> "$report_path"

collect_health

cat >> "$report_path" <<'EOF'
## Diff / observations

- Compare `free -h` before and after for available RAM, swap use, and cache changes.
- Compare `df -h` before and after for filesystem pressure or unexpected growth.
- Compare `ps aux --sort=-%mem | head -n 20` before and after for new or growing memory-heavy processes.
- Compare Docker stats and container status when Docker is available on the host.
- Compare `systemctl --failed` and `journalctl -p warning..alert -n 100 --no-pager` for new failed units, warnings, errors, OOMs, or service instability.
EOF

printf -- '- Job exit code: `%s`.\n\n' "$job_status" >> "$report_path"

cat >> "$report_path" <<'EOF'

## Recommendation / follow-up

- Add a short human summary here before using this report for an operational decision.
- If pressure or failures changed during the job, capture the affected service logs separately with a narrow, secret-safe command.
- If this was a deployment-affecting job, use Komodo for any follow-up deploy, restart, update, or rollback action.
EOF

printf 'Wrote %s\n' "$report_path"
exit "$job_status"
