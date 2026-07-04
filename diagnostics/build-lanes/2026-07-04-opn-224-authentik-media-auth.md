# OPN-224 Authentik Media Auth Diagnosis

Date: 2026-07-04

## Scope

Investigate the media-server Authentik authentication path for protected media services without mutating Docker, NPM, Authentik, DNS, certificates, or app containers.

## Evidence

Read-only container inventory showed:

- `authentik-server` and `authentik-worker-1` are up and healthy.
- `nginx-proxy-manager` is up.
- `jellyseerr` is up and attached to `media_net` and `proxy_net`.
- `sonarr`, `radarr`, `prowlarr`, and `bazarr` are up.

HTTP header checks showed:

- `https://sonarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://radarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://prowlarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://bazarr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start`.
- `https://auth.home.lab` returns an Authentik 302 to the authentication flow.
- `https://jellyseerr.home.lab` fails TLS SNI before HTTP with `tlsv1 unrecognized name`.
- `https://request.home.lab` reaches Jellyseerr directly and returns `307 Temporary Redirect` to `/login`.

NPM generated config showed:

- Jellyseerr is configured as proxy host `request.home.lab`, upstream `jellyseerr:5055`.
- That NPM host has no `auth_request` block.
- No generated NPM proxy host exists for `jellyseerr.home.lab`.
- Other protected media hosts such as `sonarr.home.lab`, `radarr.home.lab`, `prowlarr.home.lab`, and `bazarr.home.lab` include Authentik `auth_request` config.

Authentik logs showed:

- Loaded applications include `sonarr.home.lab`, `radarr.home.lab`, `prowlarr.home.lab`, `bazarr.home.lab`, and other protected services.
- No loaded Jellyseerr application was observed in recent outpost logs.

## Root Cause

The affected service is Jellyseerr. The intended route used by repo-managed Homepage is `https://jellyseerr.home.lab`, but live NPM has Jellyseerr configured as `request.home.lab`. Because `jellyseerr.home.lab` is not present as an NPM TLS proxy host, TLS fails before Authentik can run. The existing `request.home.lab` route reaches Jellyseerr directly without Authentik forward-auth protection.

## Required Fix

Use Nginx Proxy Manager and Authentik UI/API to create or update the Jellyseerr protected route:

- Public host: `jellyseerr.home.lab`
- Upstream: `http://jellyseerr:5055`
- Authentik application/provider/outpost host: `jellyseerr.home.lab`
- NPM advanced config: same Authentik forward-auth pattern used by Sonarr/Radarr/Prowlarr/Bazarr.

Decide whether `request.home.lab` should be removed, disabled, or redirected to `jellyseerr.home.lab`. It should not remain as an unauthenticated direct Jellyseerr route.

## Verification

After the live NPM/Auth changes:

```bash
curl -k -sS -I --max-time 10 https://jellyseerr.home.lab
curl -k -sS -I --max-time 10 https://request.home.lab || true
docker logs --tail 120 authentik-server 2>&1 | rg -i 'jellyseerr|request.home.lab|outpost.goauthentik|error|warning'
docker exec nginx-proxy-manager sh -lc "grep -R \"server_name jellyseerr.home.lab\\|server_name request.home.lab\\|auth_request\\|outpost.goauthentik\" -n /data/nginx/proxy_host 2>/dev/null"
```

Expected:

- `jellyseerr.home.lab` returns an Authentik 302 to `/outpost.goauthentik.io/start` for an unauthenticated request.
- Authentik outpost logs include a loaded Jellyseerr application for `jellyseerr.home.lab`.
- NPM generated config for `jellyseerr.home.lab` includes the Authentik `auth_request` block.
- `request.home.lab` is disabled, redirects, or is also Authentik-protected; it must not expose direct Jellyseerr login unauthenticated.

## Rollback

If the new route breaks access, revert the live NPM proxy host and Authentik application/provider/outpost changes to their previous values. Do not restart or redeploy Docker containers unless the operator explicitly approves it.

## Applied Fix

Applied on 2026-07-04:

- Created Authentik proxy provider `jellyseerr-proxy`.
- Created Authentik application `Jellyseerr Proxy` with slug `jellyseerr-proxy`.
- Attached `jellyseerr-proxy` to the `authentik Embedded Outpost`.
- Left the existing `Jellyseerr` application/provider intact because it already existed separately.
- Backed up the live NPM database inside the container as `/data/database.sqlite.opn224-before-jellyseerr-auth-20260704153557`.
- Updated NPM proxy host row 4 from `request.home.lab` to `jellyseerr.home.lab`.
- Preserved upstream `http://jellyseerr:5055`.
- Enabled forced SSL and HTTP/2 for the Jellyseerr NPM host.
- Replaced the Jellyseerr NPM advanced config with the same Authentik forward-auth pattern used by the working protected media hosts.
- Rewrote `/data/nginx/proxy_host/4.conf` to match the updated DB state and reloaded Nginx after `nginx -t` passed.

## Verification After Fix

Commands:

```bash
curl -k -sS -I --max-time 10 https://jellyseerr.home.lab
curl -k -sS -I --max-time 10 https://request.home.lab || true
docker logs --tail 160 authentik-server 2>&1 | grep -Ei 'Loaded application|jellyseerr|request.home.lab|outpost.goauthentik|error|warning' | tail -80
docker exec nginx-proxy-manager sh -lc "grep -R \"server_name jellyseerr.home.lab\\|server_name request.home.lab\\|auth_request\\|outpost.goauthentik\" -n /data/nginx/proxy_host/4.conf /data/nginx/proxy_host 2>/dev/null | head -80"
docker cp nginx-proxy-manager:/data/database.sqlite /tmp/opn-224-npm-after.sqlite
sqlite3 /tmp/opn-224-npm-after.sqlite "select id,domain_names,forward_scheme,forward_host,forward_port,certificate_id,ssl_forced,http2_support,enabled,length(advanced_config) from proxy_host where id=4;"
```

Results:

- `https://jellyseerr.home.lab` now returns `HTTP/2 302` to `https://jellyseerr.home.lab/outpost.goauthentik.io/start?rd=https://jellyseerr.home.lab/`.
- Authentik logs show `Loaded application` for host `jellyseerr.home.lab` with name `jellyseerr-proxy`.
- Authentik logs show the unauthenticated curl request to Jellyseerr was handled by the `jellyseerr-proxy` outpost app and returned `401` internally before NPM converted it to the sign-in redirect.
- NPM generated config for proxy host 4 has `server_name jellyseerr.home.lab`, `auth_request /_auth`, and `outpost.goauthentik` proxy blocks.
- `https://request.home.lab` now fails TLS SNI instead of reaching Jellyseerr directly.
- NPM database row 4 is now `["jellyseerr.home.lab"]|http|jellyseerr|5055|6|1|1|1|3943`.
