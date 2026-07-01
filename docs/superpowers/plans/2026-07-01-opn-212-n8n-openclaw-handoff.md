# OPN-212 n8n to OpenClaw Handoff

## Goal

Replace the `jellyfin-rating-prompt` n8n smoke/ack workflow with a real handoff to the existing OpenClaw rating prompt handler while keeping tokens and SSH keys out of Git.

## Source Of Truth

Latest Linear comments say the media side is working:

- Jellyfin Webhook sends completed movie events.
- `openclaw-gateway` accepts and forwards them to n8n.
- n8n currently acknowledges only.
- Manual Discord DM send worked through `tools/bin/openclaw-with-secrets` with `OPENCLAW_GATEWAY_TOKEN` mapped from `OPENCLAW_GATEWAY_AUTH_TOKEN`.

## Scope

- Add a repo-managed n8n helper script that reads the normalized event JSON from stdin.
- SSH to the OpenClaw host using env-configured host/user/key settings.
- Run `execution/jellyfin-rating-prompt.py --send` inside the OpenClaw workspace through `tools/bin/openclaw-with-secrets`.
- Update the n8n workflow JSON so the webhook path builds the payload, calls the helper, then returns the gateway acknowledgement.
- Add example env placeholders and mount the helper/key paths into the n8n service.

## Validation

- `jq empty apps/utilities/n8n/workflows/jellyfin-rating-prompt.workflow.json`
- `sh -n apps/utilities/n8n/scripts/send-jellyfin-rating-prompt.sh`
- `docker compose --env-file apps/utilities/example.env -f apps/utilities/compose.yml config`
- `git diff --check`

## Live Follow-Up

After commit/push/deploy, import or update the live n8n workflow and activate it. Then run one Jellyfin-originated smoke and retry the same `dedupe_key` to verify only one prompt is sent.
