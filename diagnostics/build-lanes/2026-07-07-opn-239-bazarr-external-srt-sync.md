# OPN-239 Bazarr External SRT Sync Workflow

Date: 2026-07-07

## Scope

Document the workflow for making Jellyfin use synced external SRT subtitles from Bazarr, especially on the Google 4K Streamer where embedded subtitle playback can get stuck.

No Docker, Komodo, Bazarr, Jellyfin, Nginx Proxy Manager, Authentik, AdGuard, media files, or appdata state was changed by this repo update.

## Repository Boundary

Bazarr is already present in `apps/arr-stack/compose.yml` and has the media mounts needed to write subtitle files next to media:

```yaml
bazarr:
  volumes:
    - ${APPDATA_ROOT}/bazarr:/config
    - ${DATA_ROOT}/media/tv:/tv
    - ${DATA_ROOT}/media/movies:/movies
```

No compose change is needed for OPN-239. The important settings live in Bazarr runtime configuration under `${APPDATA_ROOT}/bazarr`, which this repository deliberately does not manage.

## Target Behavior

For newly downloaded subtitles:

- Bazarr downloads English subtitles as external `.srt` files next to the movie or episode file.
- Bazarr synchronizes downloaded subtitles when the match score is below the configured threshold.
- Jellyfin sees the external SRT track after a library scan.
- Playback can select an external SRT track such as `English - SRT - External`.
- Subtitle burn-in is not forced as the default workaround, because burn-in may trigger transcoding and hurt 4K playback.

## Bazarr Settings

Apply these settings in `https://bazarr.home.lab`.

### Subtitles Synchronization

Path:

```text
Settings -> Subtitles
```

Set:

```text
Automatic Subtitles Synchronization: enabled
Series Score Threshold: enabled, 96
Movies Score Threshold: enabled, 86
```

Rationale:

- Bazarr documents automatic subtitle synchronization after download.
- TRaSH Guides recommend starting with `96` for series and `86` for movies.
- The threshold avoids trying to synchronize subtitles that already have strong release matches.

Operational note: subtitle synchronization can use CPU and I/O because Bazarr may analyze media/audio to align the subtitle. If Bazarr causes noticeable load during large backfills, pause the backfill and resume in smaller batches.

### Language/Profile Handling

Path:

```text
Settings -> Languages / Profiles
```

Set or confirm:

```text
Language: English
Subtitle type: normal external subtitles
Profile assignment: applied to monitored Sonarr series and Radarr movies
Embedded subtitles: do not treat embedded subtitles as sufficient when cleaner external SRT is the goal
```

Exact labels can vary by Bazarr version. The outcome to verify is that items with only embedded subtitles remain eligible for an external English SRT download.

### Providers

Confirm at least one configured subtitle provider can supply English SRT subtitles for both movies and series. Do not add provider credentials to this repository.

## Jellyfin Verification

After Bazarr downloads or synchronizes subtitles:

1. Run a Jellyfin library scan for the affected library.
2. Open a known affected movie or episode on the Google 4K Streamer.
3. In subtitle selection, choose `English - SRT - External` or the closest Jellyfin label for an external English SRT track.
4. Confirm the video direct-plays or otherwise does not force subtitle burn-in as the default.
5. Watch through the section that previously froze or left subtitles stuck on screen.

Expected result: the external SRT track plays without the stuck embedded-subtitle behavior.

## Existing Library Cleanup

Use this path for already-affected movies and episodes.

### First Pass: Bazarr UI

Start in Bazarr:

```text
1. Filter for affected or missing-subtitle movies and series.
2. Search/download external English SRT subtitles for a small sample.
3. Use any available per-item or per-series synchronization action.
4. Verify the sample in Jellyfin before expanding to the whole library.
```

If the sample works, repeat in batches. Avoid a full-library sync until CPU, I/O, and subtitle quality look acceptable.

### One-Off Bazarr Sync Helper

This repo includes a disabled-by-default `bazarr-sync` helper service in `apps/arr-stack/compose.yml`. It is intended for manual use through Komodo when existing subtitles need a bulk audio sync pass.

Guardrails:

- Trigger it only as a one-off job, not as a scheduler.
- Store `BAZARR_SYNC_API_TOKEN` only in the untracked `apps/arr-stack/.env`.
- Keep the default internal Docker target as `BAZARR_SYNC_URL=http://bazarr:6767`.
- Do not store the API key in this repository, shell history, docs, or Linear comments.
- Confirm backups/checkpoints exist before broad cleanup.
- Keep a backup/checkpoint for Bazarr appdata and any affected media subtitle files before broad cleanup.
- Expect it to run movies first and shows second, then exit.

Service shape:

```yaml
bazarr-sync:
  image: ghcr.io/ajmandourah/bazarr-sync:latest
  profiles:
    - manual
  restart: "no"
```

Komodo trigger checklist:

```text
1. Confirm `BAZARR_SYNC_API_TOKEN` is set in the arr-stack environment.
2. Confirm the helper points at the internal Docker service with `BAZARR_SYNC_URL=http://bazarr:6767`.
3. In Komodo, run the `bazarr-sync` helper from the arr stack with the manual profile enabled.
4. Watch logs until both `sync movies` and `sync shows` finish, or stop if Bazarr/server load is too high.
5. Run a Jellyfin library scan for affected libraries.
6. Verify a sample item on the Google 4K Streamer.
```

Do not commit the command with a real API key.

## Manual Deployment Checklist

- [ ] Confirm backups/checkpoints exist for `${APPDATA_ROOT}/bazarr` and the affected media folders.
- [ ] Apply Bazarr subtitle synchronization settings.
- [ ] Confirm English external subtitle profile behavior for movies and series.
- [ ] Download/sync a small affected sample.
- [ ] Run a Jellyfin library scan.
- [ ] Verify `English - SRT - External` playback on the Google 4K Streamer.
- [ ] Expand cleanup in batches.
- [ ] Trigger `bazarr-sync` from Komodo only when a one-off bulk sync pass is needed.

## Sources Checked

- Bazarr settings documentation: https://wiki.bazarr.media/Additional-Configuration/Settings/
- Bazarr performance note for synchronization: https://wiki.bazarr.media/Additional-Configuration/Performance-Tuning/
- Bazarr setup guide: https://wiki.bazarr.media/Getting-Started/Setup-Guide/
- TRaSH Guides Bazarr suggested scoring: https://trash-guides.info/Bazarr/Bazarr-suggested-scoring/
- `bazarr-sync` helper: https://github.com/ajmandourah/bazarr-sync

## Verification

Repo-side verification:

```bash
rg -n "token|secret|password|api[_-]?key|cookie|authorization|privkey|BEGIN " diagnostics/build-lanes/2026-07-07-opn-239-bazarr-external-srt-sync.md docs/superpowers/plans/2026-07-07-opn-239-bazarr-external-srt-sync.md
git diff --check
```

Live verification after applying the manual settings:

```text
1. A new subtitle appears next to a movie or episode as an external `.srt` file.
2. Jellyfin detects the external SRT after a library scan.
3. The Google 4K Streamer can select the external English SRT track.
4. The previously affected playback section no longer sticks or freezes subtitles.
```
