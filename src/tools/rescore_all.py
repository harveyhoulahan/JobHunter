"""
Rescore every job in the DB using the current calibrated scorer.

Run from project root:
  python3 src/tools/rescore_all.py

Operates in batches of 200, committing after each batch so the DB is
never locked for the full duration. If an error occurs mid-run the last
committed batch is retained (no full rollback needed for a read-modify-write
script; per-batch commit is the correct pattern here).

Env vars:
  JOBHUNTER_DB   override DB path
  SCORE_DEBUG    set to 'true' to log component breakdown per job
"""
import os
import sys
import sqlite3
import json
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC  = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_SRC)

sys.path.insert(0, _ROOT)
sys.path.insert(0, _SRC)

DB_PATH = os.environ.get(
    'JOBHUNTER_DB',
    os.path.join(_SRC, 'data', 'jobhunter.db')
)

BATCH_SIZE = 200

# ── Import scorer ─────────────────────────────────────────────────────────────
from src.scoring.engine import JobScorer
from src.profile import HARVEY_PROFILE

thresholds = HARVEY_PROFILE.get("alert_thresholds", {})
IMMEDIATE  = thresholds.get("immediate",  78)
DIGEST     = thresholds.get("digest",     62)
STORE_ONLY = thresholds.get("store_only", 40)

SEP = "─" * 90


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB not found at {DB_PATH}")
        print("Set JOBHUNTER_DB env var to override.")
        sys.exit(1)

    print(f"\n{SEP}")
    print(f"  RESCORE ALL — DB: {DB_PATH}")
    print(f"  Thresholds  immediate={IMMEDIATE}  digest={DIGEST}  store_only={STORE_ONLY}")
    print(SEP)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Fetch all scoreable jobs (have a description stored)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, company, location, source, url,
               description, fit_score
        FROM jobs
        WHERE description IS NOT NULL AND description != ''
        ORDER BY id
    """)
    jobs = cur.fetchall()

    total = len(jobs)
    print(f"  Jobs with descriptions to rescore: {total}\n")

    scorer = JobScorer()

    updated    = 0
    fallbacks  = 0
    errors     = 0
    new_scores = []

    batch_updates = []  # (new_score, breakdown_json, id)

    for i, row in enumerate(jobs, 1):
        job_data = {
            'id':          row['id'],
            'title':       row['title'] or '',
            'company':     row['company'] or '',
            'location':    row['location'] or '',
            'source':      row['source'] or '',
            'url':         row['url'] or '',
            'description': row['description'] or '',
        }

        try:
            result      = scorer.score_job(job_data)
            new_score   = result['fit_score']
            breakdown   = result.get('breakdown', {})
            ai_details  = result.get('ai_details', {})

            if ai_details.get('is_fallback', False):
                fallbacks += 1

            new_scores.append(new_score)
            batch_updates.append((
                new_score,
                json.dumps(breakdown),
                row['id'],
            ))
            updated += 1

        except Exception as e:
            print(f"  ERROR scoring job id={row['id']} '{row['title']}': {e}")
            errors += 1

        # Progress log
        if i % 100 == 0:
            print(f"  Rescored {i}/{total} jobs "
                  f"(fallbacks so far: {fallbacks}, errors: {errors})...")

        # Batch commit every BATCH_SIZE rows
        if len(batch_updates) >= BATCH_SIZE:
            _flush(conn, batch_updates)
            batch_updates.clear()

    # Flush remaining
    if batch_updates:
        _flush(conn, batch_updates)

    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  RESCORE COMPLETE")
    print(f"  Updated : {updated} jobs")
    print(f"  Fallbacks (Kimi unavailable): {fallbacks} ({100*fallbacks/max(updated,1):.1f}%)")
    print(f"  Errors  : {errors}")
    print(SEP)

    if new_scores:
        _print_distribution(new_scores)
        _print_threshold_counts(new_scores)


def _flush(conn: sqlite3.Connection, updates: list):
    """Write a batch of (score, breakdown_json, id) to the DB."""
    cur = conn.cursor()
    cur.executemany(
        "UPDATE jobs SET fit_score = ?, score_breakdown = ? WHERE id = ?",
        updates
    )
    conn.commit()


def _print_distribution(scores: list):
    buckets = defaultdict(int)
    for s in scores:
        b = int(s // 10) * 10
        b = min(b, 90)
        buckets[b] += 1

    total = len(scores) or 1
    avg = sum(scores) / total
    med = sorted(scores)[total // 2]

    print(f"\n{'─'*26}  SCORE DISTRIBUTION  {'─'*26}")
    print(f"  {'BUCKET':<12}  {'COUNT':>6}  BAR")
    print("  " + "-" * 60)
    for low in range(0, 100, 10):
        count = buckets[low]
        bar   = "█" * int(count / total * 40)
        print(f"  {low:>3}–{low+10:<3}  {count:>8}  {bar}")

    print(f"\n  Mean: {avg:.1f}   Median: {med:.1f}   "
          f"Min: {min(scores):.1f}   Max: {max(scores):.1f}")


def _print_threshold_counts(scores: list):
    n_immediate  = sum(1 for s in scores if s >= IMMEDIATE)
    n_digest     = sum(1 for s in scores if DIGEST <= s < IMMEDIATE)
    n_store_only = sum(1 for s in scores if STORE_ONLY <= s < DIGEST)
    n_noise      = sum(1 for s in scores if s < STORE_ONLY)

    print(f"\n{'─'*26}  THRESHOLD BUCKETS   {'─'*26}")
    print(f"  Immediate  (≥{IMMEDIATE}):              {n_immediate:>5}")
    print(f"  Digest     ({DIGEST}–{IMMEDIATE-1}):            {n_digest:>5}")
    print(f"  Store-only ({STORE_ONLY}–{DIGEST-1}):            {n_store_only:>5}")
    print(f"  Noise      (<{STORE_ONLY}):               {n_noise:>5}  ← will be pruned")
    print(SEP)


if __name__ == '__main__':
    main()
