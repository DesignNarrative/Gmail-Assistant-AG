"""
InboxIQ — Storage Housekeeping & Orphan Attachment Pruner
Safely scans uploads/ directory, compares against PostgreSQL attachments table,
and purges orphaned files older than 24 hours to reclaim disk space.
"""

import os
import sys
import time
import asyncio
import argparse
from datetime import datetime, timezone

# Add backend directory to sys.path so we can import app modules cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.attachment import Attachment


async def get_active_storage_paths() -> set[str]:
    """Fetch all registered storage paths and filenames from the database."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Attachment.storage_path).where(Attachment.storage_path.isnot(None))
        )
        paths = result.scalars().all()

    active_set = set()
    for p in paths:
        if p:
            norm_abs = os.path.normpath(os.path.abspath(p))
            fname = os.path.basename(norm_abs)
            active_set.add(norm_abs)
            active_set.add(fname)
    return active_set


def prune_storage(older_than_hours: float = 24.0, dry_run: bool = False):
    """Scan upload directory and remove orphaned files older than older_than_hours."""
    settings = get_settings()
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)

    print("=" * 60)
    print("InboxIQ Storage Housekeeping & Orphan Pruner")
    print(f"Timestamp        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Directory : {upload_dir}")
    print(f"Safety Window    : Files older than {older_than_hours} hour(s)")
    print(f"Dry Run Mode     : {dry_run}")
    print("=" * 60)

    if not os.path.exists(upload_dir):
        print(f"Directory {upload_dir} does not exist. Nothing to prune.")
        return

    # Fetch active attachments from DB
    print("Querying active database attachments...")
    active_paths = asyncio.run(get_active_storage_paths())
    print(f"Found {len(active_paths)} active attachment reference(s) in database.")

    # Scan directory
    now = time.time()
    cutoff_seconds = older_than_hours * 3600

    scanned_count = 0
    active_count = 0
    in_flight_count = 0
    orphaned_count = 0
    reclaimed_bytes = 0

    for entry in os.scandir(upload_dir):
        if not entry.is_file():
            continue

        scanned_count += 1
        fpath = os.path.normpath(entry.path)
        fname = entry.name
        fsize = entry.stat().st_size
        mtime = entry.stat().st_mtime
        age_hours = (now - mtime) / 3600

        # Check if file belongs to an active database attachment
        if fpath in active_paths or fname in active_paths:
            active_count += 1
            continue

        # File is not in database: check safety buffer
        if (now - mtime) < cutoff_seconds:
            # Modified recently: likely active in-flight download/OCR
            in_flight_count += 1
            continue

        # File is orphaned and older than safety cutoff: candidate for pruning
        orphaned_count += 1
        reclaimed_bytes += fsize

        if dry_run:
            print(f"  [DRY RUN] Would prune: {fname} (age: {age_hours:.1f} hrs, size: {fsize / 1024:.1f} KB)")
        else:
            try:
                os.remove(fpath)
                print(f"  [PRUNED] {fname} (age: {age_hours:.1f} hrs, reclaimed: {fsize / 1024:.1f} KB)")
            except Exception as err:
                print(f"  [ERROR] Could not remove {fname}: {err}")

    print("-" * 60)
    print(f"Scanned files on disk      : {scanned_count}")
    print(f"Active database attachments: {active_count}")
    print(f"Recent in-flight files kept : {in_flight_count}")
    print(f"Orphaned files {'identified' if dry_run else 'pruned'}     : {orphaned_count}")
    print(f"Disk space {'reclaimable' if dry_run else 'reclaimed'}      : {reclaimed_bytes / (1024 * 1024):.2f} MB")
    print("Storage housekeeping finished successfully.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InboxIQ Storage Housekeeping & Orphan Pruner")
    parser.add_argument(
        "--older-than-hours",
        type=float,
        default=24.0,
        help="Only prune orphaned files older than this many hours (default: 24.0)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview orphaned files without deleting anything"
    )
    args = parser.parse_args()

    prune_storage(older_than_hours=args.older_than_hours, dry_run=args.dry_run)
