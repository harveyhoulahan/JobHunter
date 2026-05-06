"""
Prune noise from the DB after rescoring.

Removes:
  1. Jobs below the store_only score floor
  2. Duplicate title+company pairs (keep highest-scored version)
  3. Non-English job postings (langdetect on title + first 300 chars of description)

Usage:
  python3 src/tools/prune_db.py              # dry-run (safe — prints what would be deleted)
  python3 src/tools/prune_db.py --confirm    # actually deletes

Env vars:
  JOBHUNTER_DB   override DB path
"""
import os
import sys
import sqlite3
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC  = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_SRC)

sys.path.insert(0, _ROOT)
sys.path.insert(0, _SRC)

DB_PATH = os.environ.get(
    'JOBHUNTER_DB',
    os.path.join(_SRC, 'data', 'jobhunter.db')
)

SEP = "─" * 90

# ── Language detection ────────────────────────────────────────────────────────
try:
    from langdetect import detect as _detect_lang
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    print("WARNING: langdetect not installed — language filter skipped. pip install langdetect")


def _is_english(text: str) -> bool:
    if not _LANGDETECT_AVAILABLE or not text or len(text.strip()) < 20:
        return True
    try:
        return _detect_lang(text[:300]) == 'en'
    except Exception:
        return True  # fail open


# ── Profile thresholds ────────────────────────────────────────────────────────
from src.profile import HARVEY_PROFILE

thresholds = HARVEY_PROFILE.get("alert_thresholds", {})
STORE_ONLY = thresholds.get("store_only", 40)


def main():
    parser = argparse.ArgumentParser(description="Prune noise from JobHunter DB.")
    parser.add_argument("--confirm", action="store_true",
                        help="Actually delete rows. Default is dry-run (safe).")
    args = parser.parse_args()

    dry_run = not args.confirm

    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Count before
    cur.execute("SELECT COUNT(*) FROM jobs")
    total_before = cur.fetchone()[0]

    print(f"\n{SEP}")
    print(f"  PRUNE DB {'[DRY RUN]' if dry_run else '[LIVE — deleting]'}")
    print(f"  DB: {DB_PATH}")
    print(f"  Before prune: {total_before} jobs")
    print(f"  store_only floor: {STORE_ONLY}")
    print(SEP)

    # ── 1. Below score floor ──────────────────────────────────────────────────
    cur.execute("SELECT id FROM jobs WHERE fit_score < ? OR fit_score IS NULL",
                (STORE_ONLY,))
    below_floor_ids = [r[0] for r in cur.fetchall()]
    print(f"\n  [1] Below score floor (<{STORE_ONLY}): {len(below_floor_ids)} jobs")

    # ── 2. Duplicate title+company (keep highest score) ───────────────────────
    cur.execute("""
        SELECT title, company, COUNT(*) as cnt, MAX(fit_score) as best_score
        FROM jobs
        GROUP BY LOWER(TRIM(title)), LOWER(TRIM(company))
        HAVING cnt > 1
    """)
    dup_groups = cur.fetchall()

    dup_ids = []
    for row in dup_groups:
        cur.execute("""
            SELECT id, fit_score
            FROM jobs
            WHERE LOWER(TRIM(title)) = LOWER(TRIM(?))
              AND LOWER(TRIM(company)) = LOWER(TRIM(?))
            ORDER BY fit_score DESC NULLS LAST
        """, (row['title'], row['company']))
        rows = cur.fetchall()
        # Keep first (highest score), delete the rest
        dup_ids.extend(r['id'] for r in rows[1:])

    # Don't double-count with below_floor_ids
    dup_ids = list(set(dup_ids) - set(below_floor_ids))
    print(f"  [2] Duplicate title+company (lower-scored copies): {len(dup_ids)} jobs")

    # ── 3. Non-English ────────────────────────────────────────────────────────
    non_english_ids = []
    if _LANGDETECT_AVAILABLE:
        already_marked = set(below_floor_ids) | set(dup_ids)
        cur.execute("""
            SELECT id, title, description
            FROM jobs
            WHERE id NOT IN ({})
        """.format(
            ','.join('?' * len(already_marked)) if already_marked else '0'
        ), list(already_marked) if already_marked else [])
        remaining = cur.fetchall()

        for row in remaining:
            text = f"{row['title'] or ''} {(row['description'] or '')[:300]}"
            if not _is_english(text):
                non_english_ids.append(row['id'])

        print(f"  [3] Non-English postings: {len(non_english_ids)} jobs")
    else:
        print(f"  [3] Non-English postings: SKIPPED (langdetect not installed)")

    # ── Summary ───────────────────────────────────────────────────────────────
    all_delete_ids = list(set(below_floor_ids + dup_ids + non_english_ids))
    total_delete = len(all_delete_ids)
    print(f"\n  Total to delete: {total_delete}")
    print(f"  After prune:     {total_before - total_delete} jobs")

    if dry_run:
        print(f"\n  ⚠  DRY RUN — nothing deleted.")
        print(f"     Re-run with --confirm to execute.\n")
        conn.close()
        return

    # ── Execute deletions ─────────────────────────────────────────────────────
    CHUNK = 500  # SQLite SQLITE_MAX_VARIABLE_NUMBER safe limit
    deleted_total = 0

    def delete_ids(ids: list, label: str):
        nonlocal deleted_total
        for i in range(0, len(ids), CHUNK):
            chunk = ids[i:i + CHUNK]
            placeholders = ','.join('?' * len(chunk))
            cur.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", chunk)
        deleted_total += len(ids)
        print(f"  ✓ Deleted {len(ids)} {label}")

    try:
        delete_ids(below_floor_ids, f"below floor (<{STORE_ONLY})")
        delete_ids(dup_ids, "duplicate title+company")
        delete_ids(non_english_ids, "non-English")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR — rolled back. No rows deleted. Details: {e}")
        conn.close()
        sys.exit(1)

    cur.execute("SELECT COUNT(*) FROM jobs")
    total_after = cur.fetchone()[0]

    # VACUUM to reclaim disk space
    print("  Running VACUUM to reclaim disk space...")
    conn.execute("VACUUM")
    conn.close()

    print(f"\n{SEP}")
    print(f"  PRUNE COMPLETE")
    print(f"  Before: {total_before}  |  Deleted: {deleted_total}  |  After: {total_after}")
    print(SEP)


if __name__ == '__main__':
    main()
