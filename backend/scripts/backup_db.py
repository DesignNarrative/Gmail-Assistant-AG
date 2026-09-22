"""
InboxIQ — Automated PostgreSQL Database Backup Script
Dumps PostgreSQL database, compresses via gzip, and automatically prunes old backups.
"""

import os
import sys
import glob
import gzip
import shutil
import argparse
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

# Add backend directory to sys.path so we can load settings cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import get_settings


def find_pg_dump() -> str:
    """Locate pg_dump executable on Windows or in system PATH."""
    # 1. Check system PATH
    which_path = shutil.which("pg_dump")
    if which_path:
        return which_path

    # 2. Check common Windows PostgreSQL installation paths
    candidate_patterns = [
        r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe",
        r"C:\Program Files (x86)\PostgreSQL\*\bin\pg_dump.exe",
    ]
    for pattern in candidate_patterns:
        matches = glob.glob(pattern)
        if matches:
            matches.sort(reverse=True)
            return matches[0]

    raise FileNotFoundError(
        "Could not find pg_dump.exe. Please ensure PostgreSQL is installed or add pg_dump to your PATH."
    )


def parse_db_connection():
    """Extract host, port, user, password, and dbname from settings."""
    settings = get_settings()
    db_url = settings.DATABASE_URL

    # Replace asyncpg scheme with standard postgresql for urlparse
    if "+asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    parsed = urlparse(db_url)
    user = unquote(parsed.username) if parsed.username else "postgres"
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    dbname = parsed.path.lstrip("/") if parsed.path else "gmail_assistant"

    return host, port, user, password, dbname


def prune_old_backups(backup_dir: str, retention_days: int = 14, dry_run: bool = False):
    """Delete backup archives older than retention_days."""
    if not os.path.exists(backup_dir):
        return

    now = datetime.now(timezone.utc).timestamp()
    cutoff_seconds = retention_days * 86400
    pruned_count = 0
    reclaimed_bytes = 0

    for fname in os.listdir(backup_dir):
        if fname.startswith("backup_") and fname.endswith(".sql.gz"):
            fpath = os.path.join(backup_dir, fname)
            try:
                mtime = os.path.getmtime(fpath)
                age_seconds = now - mtime
                if age_seconds > cutoff_seconds:
                    fsize = os.path.getsize(fpath)
                    age_days = round(age_seconds / 86400, 1)
                    if dry_run:
                        print(f"  [DRY RUN] Would prune: {fname} (age: {age_days} days, size: {fsize / 1024:.1f} KB)")
                    else:
                        os.remove(fpath)
                        print(f"  [PRUNED] {fname} (age: {age_days} days, reclaimed: {fsize / 1024:.1f} KB)")
                    pruned_count += 1
                    reclaimed_bytes += fsize
            except Exception as e:
                print(f"  [WARN] Failed to check/prune {fname}: {e}")

    if pruned_count > 0:
        print(f"Disk cleanup complete: {pruned_count} old backup(s) pruned ({reclaimed_bytes / (1024 * 1024):.2f} MB reclaimed).")
    else:
        print(f"Retention check: all backups are within the {retention_days}-day retention window.")


def run_backup(retention_days: int = 14, output_dir: str = None, dry_run: bool = False):
    """Execute pg_dump, compress output with gzip, and prune old backups."""
    if output_dir is None:
        output_dir = os.path.join(BACKEND_DIR, "backups")
    os.makedirs(output_dir, exist_ok=True)

    pg_dump_bin = find_pg_dump()
    host, port, user, password, dbname = parse_db_connection()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{dbname}_{timestamp}.sql.gz"
    backup_path = os.path.join(output_dir, backup_filename)

    print("=" * 60)
    print(f"InboxIQ Automated Database Backup")
    print(f"Timestamp    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target DB    : {dbname}@{host}:{port} (User: {user})")
    print(f"pg_dump tool : {pg_dump_bin}")
    print(f"Destination  : {backup_path}")
    print("=" * 60)

    if dry_run:
        print("[DRY RUN] Skipping dump execution. Running retention check only...")
        prune_old_backups(output_dir, retention_days=retention_days, dry_run=True)
        return

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    cmd = [
        pg_dump_bin,
        "-h", str(host),
        "-p", str(port),
        "-U", str(user),
        "-F", "p",
        dbname
    ]

    print(f"Starting database dump...")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        with gzip.open(backup_path, "wb", compresslevel=9) as gz_out:
            shutil.copyfileobj(proc.stdout, gz_out)

        _, stderr = proc.communicate()

        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            if os.path.exists(backup_path):
                os.remove(backup_path)
            raise RuntimeError(f"pg_dump failed with exit code {proc.returncode}: {err_msg}")

        file_size_kb = os.path.getsize(backup_path) / 1024
        print(f"Backup SUCCESS: Created {backup_filename} ({file_size_kb:.1f} KB compressed)")

    except Exception as e:
        print(f"ERROR during backup: {e}", file=sys.stderr)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        sys.exit(1)

    print("\nChecking backup retention policy...")
    prune_old_backups(output_dir, retention_days=retention_days, dry_run=False)
    print("Backup process finished successfully.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InboxIQ Database Backup & Retention Utility")
    parser.add_argument("--retention-days", type=int, default=14, help="Number of days to keep backups (default: 14)")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom directory to store backups")
    parser.add_argument("--dry-run", action="store_true", help="Preview backup and retention without modifying files")
    args = parser.parse_args()

    run_backup(
        retention_days=args.retention_days,
        output_dir=args.output_dir,
        dry_run=args.dry_run
    )
