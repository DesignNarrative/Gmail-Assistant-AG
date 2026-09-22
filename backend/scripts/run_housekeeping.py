"""
InboxIQ — Unified Daily Housekeeping & Maintenance Runner
Runs both database backup (with gzip and retention pruning) and storage housekeeping in one step.
Ideal for scheduling via Windows Task Scheduler or nightly cron.
"""

import os
import sys
import argparse
from datetime import datetime

# Add backend directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from scripts.backup_db import run_backup
from scripts.prune_storage import prune_storage


def run_full_housekeeping(retention_days: int = 14, older_than_hours: float = 24.0, dry_run: bool = False):
    start_time = datetime.now()
    print("\n" + "#" * 65)
    print(f"  INBOXIQ DAILY HOUSEKEEPING & MAINTENANCE PIPELINE")
    print(f"  Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 65 + "\n")

    # Step 1: Database Backup & Retention
    print("[TASK 1/2] PostgreSQL Automated Backup & Retention Check")
    try:
        run_backup(retention_days=retention_days, dry_run=dry_run)
    except Exception as e:
        print(f"[TASK 1 ERROR] Database backup failed: {e}", file=sys.stderr)

    # Step 2: Storage Pruning
    print("[TASK 2/2] Upload Storage & Orphan Attachment Cleanup")
    try:
        prune_storage(older_than_hours=older_than_hours, dry_run=dry_run)
    except Exception as e:
        print(f"[TASK 2 ERROR] Storage pruning failed: {e}", file=sys.stderr)

    duration = (datetime.now() - start_time).total_seconds()
    print("#" * 65)
    print(f"  HOUSEKEEPING COMPLETE in {duration:.2f}s")
    print("#" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InboxIQ Unified Daily Housekeeping Runner")
    parser.add_argument("--retention-days", type=int, default=14, help="Days of database backups to keep (default: 14)")
    parser.add_argument("--older-than-hours", type=float, default=24.0, help="Hours before orphaned files are pruned (default: 24.0)")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without modifying or deleting files")
    args = parser.parse_args()

    run_full_housekeeping(
        retention_days=args.retention_days,
        older_than_hours=args.older_than_hours,
        dry_run=args.dry_run
    )
