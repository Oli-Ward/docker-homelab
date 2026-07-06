import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "backup-media-appdata.sh"


def base_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["APPDATA_ROOT"] = str(tmp_path / "appdata")
    env["BACKUP_DEST"] = str(tmp_path / "backup")
    env["BACKUP_AGE_RECIPIENT"] = "age1example"
    return env


def test_backup_script_dry_run_lists_inventory_without_writing(tmp_path: Path):
    appdata = tmp_path / "appdata"
    backup = tmp_path / "backup"
    (appdata / "jellyfin").mkdir(parents=True)
    (appdata / "jellyseerr").mkdir(parents=True)
    (appdata / "ryot-postgres").mkdir(parents=True)
    backup.mkdir()

    result = subprocess.run(
        [str(SCRIPT), "--dry-run"],
        cwd=REPO_ROOT,
        env=base_env(tmp_path),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "DRY RUN" in result.stdout
    assert "APPDATA_ROOT/jellyfin" in result.stdout
    assert "APPDATA_ROOT/jellyseerr" in result.stdout
    assert "APPDATA_ROOT/ryot-postgres" in result.stdout
    assert not list(backup.iterdir())


def write_fake_tools(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    for name in ("tar", "gzip", "age", "sha256sum"):
        tool = bin_dir / name
        tool.write_text(
            f"""#!/usr/bin/env sh
printf '%s\\n' "{name} $*" >> "{log}"
case "{name}" in
  tar) printf 'tar-bytes' ;;
  gzip) cat ;;
  age)
    output=""
    while [ "$#" -gt 0 ]; do
      if [ "$1" = "-o" ]; then
        shift
        output=$1
      fi
      shift || true
    done
    cat > "$output"
    ;;
  sha256sum) printf 'abc123  %s\\n' "$1" ;;
esac
""",
            encoding="utf-8",
        )
        tool.chmod(0o755)
    return bin_dir


def test_backup_script_requires_guard_file_for_run(tmp_path: Path):
    appdata = tmp_path / "appdata"
    (appdata / "jellyfin").mkdir(parents=True)
    (tmp_path / "backup").mkdir()

    result = subprocess.run(
        [str(SCRIPT), "--run"],
        cwd=REPO_ROOT,
        env=base_env(tmp_path),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert ".opn-192-media-backups-ok" in result.stderr


def test_backup_script_run_writes_encrypted_artifact_with_fake_tools(tmp_path: Path):
    appdata = tmp_path / "appdata"
    backup = tmp_path / "backup"
    (appdata / "jellyfin").mkdir(parents=True)
    (appdata / "jellyfin" / "config.xml").write_text("<xml />", encoding="utf-8")
    backup.mkdir()
    (backup / ".opn-192-media-backups-ok").write_text("ok\n", encoding="utf-8")
    bin_dir = write_fake_tools(tmp_path)
    env = base_env(tmp_path)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["BACKUP_TIMESTAMP"] = "2026-07-01T09-30-00Z"

    result = subprocess.run(
        [str(SCRIPT), "--run"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    artifact = backup / "media-appdata-2026-07-01T09-30-00Z.tar.gz.age"
    assert result.returncode == 0
    assert artifact.exists()
    assert (backup / "media-appdata-2026-07-01T09-30-00Z.tar.gz.age.sha256").exists()
    commands = (tmp_path / "commands.log").read_text(encoding="utf-8")
    assert "tar" in commands
    assert "gzip" in commands
    assert "age -r age1example" in commands
    assert "config.xml" not in result.stdout
