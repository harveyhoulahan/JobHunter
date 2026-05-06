"""
Score audit tool — pulls top/bottom scored jobs and prints distribution.
Run from project root:  python3 -m src.tools.score_audit
"""
import os
import sys
import sqlite3
from collections import defaultdict

# Resolve DB path relative to this file
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
DB_PATH = os.path.join(_PROJECT_ROOT, 'src', 'data', 'jobhunter.db')

# Allow override via env
DB_PATH = os.environ.get('JOBHUNTER_DB', DB_PATH)


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB not found at {DB_PATH}")
        print("Set JOBHUNTER_DB env var if it's in a different location.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ── Top 20 ────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT title, fit_score, source, location
        FROM jobs
        WHERE fit_score IS NOT NULL
        ORDER BY fit_score DESC
        LIMIT 20
    """)
    top = cur.fetchall()

    # ── Bottom 20 ─────────────────────────────────────────────────────────
    cur.execute("""
        SELECT title, fit_score, source, location
        FROM jobs
        WHERE fit_score IS NOT NULL
        ORDER BY fit_score ASC
        LIMIT 20
    """)
    bottom = cur.fetchall()

    # ── Distribution ──────────────────────────────────────────────────────
    cur.execute("SELECT fit_score FROM jobs WHERE fit_score IS NOT NULL")
    all_scores = [row[0] for row in cur.fetchall()]
    conn.close()

    # ── Print results ─────────────────────────────────────────────────────
    SEP = "─" * 90

    print(f"\n{SEP}")
    print(f"  DATABASE: {DB_PATH}")
    print(f"  Total scored jobs: {len(all_scores)}")
    print(SEP)

    print(f"\n{'─'*30}  TOP 20 JOBS  {'─'*30}")
    _print_table(top)

    print(f"\n{'─'*28}  BOTTOM 20 JOBS  {'─'*28}")
    _print_table(bottom)

    print(f"\n{'─'*26}  SCORE DISTRIBUTION  {'─'*26}")
    _print_distribution(all_scores)


def _print_table(rows):
    header = f"  {'SCORE':>6}  {'SOURCE':<14}  {'LOCATION':<22}  TITLE"
    print(header)
    print("  " + "-" * 86)
    for row in rows:
        score  = row['fit_score']
        source = (row['source'] or '—')[:14]
        loc    = (row['location'] or '—')[:22]
        title  = (row['title'] or '—')[:55]
        print(f"  {score:>6.1f}  {source:<14}  {loc:<22}  {title}")


def _print_distribution(scores):
    buckets = defaultdict(int)
    for s in scores:
        bucket = int(s // 10) * 10   # 0,10,20,...,90
        bucket = min(bucket, 90)     # cap 100 into the 90-100 bucket
        buckets[bucket] += 1

    total = len(scores) or 1
    print(f"  {'BUCKET':<12}  {'COUNT':>6}  {'BAR'}")
    print("  " + "-" * 60)
    for low in range(0, 100, 10):
        high  = low + 10
        count = buckets[low]
        bar   = "█" * int(count / total * 40)
        label = f"{low:>3}–{high:<3}"
        print(f"  {label:<12}  {count:>6}  {bar}")

    avg = sum(scores) / total
    med = sorted(scores)[total // 2]
    print(f"\n  Mean: {avg:.1f}   Median: {med:.1f}   Min: {min(scores):.1f}   Max: {max(scores):.1f}")


if __name__ == '__main__':
    main()
