"""
Score debug tool — re-scores top/bottom jobs from DB with SCORE_DEBUG=true
so you can see exactly what each component contributes.

Run from project root:
  SCORE_DEBUG=true python3 src/tools/score_debug.py

Prints full component breakdown per job so you can validate calibration
before/after weight changes.
"""
import os
import sys
import sqlite3

# Activate SCORE_DEBUG before importing the engine
os.environ["SCORE_DEBUG"] = "true"

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


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pull top 5 and bottom 5 scored jobs that have a description stored
    cur.execute("""
        SELECT id, title, company, location, url, source, fit_score, description
        FROM jobs
        WHERE fit_score IS NOT NULL
          AND description IS NOT NULL AND description != ''
        ORDER BY fit_score DESC
        LIMIT 5
    """)
    top_jobs = cur.fetchall()

    cur.execute("""
        SELECT id, title, company, location, url, source, fit_score, description
        FROM jobs
        WHERE fit_score IS NOT NULL
          AND description IS NOT NULL AND description != ''
        ORDER BY fit_score ASC
        LIMIT 5
    """)
    bottom_jobs = cur.fetchall()
    conn.close()

    # Now import the scorer (SCORE_DEBUG=true is already set in env)
    from src.scoring.engine import JobScorer
    scorer = JobScorer()

    def rescore_group(label, jobs):
        print(f"\n{SEP}")
        print(f"  {label}")
        print(SEP)
        for row in jobs:
            job_data = {
                'title': row['title'],
                'company': row['company'],
                'location': row['location'],
                'url': row['url'],
                'source': row['source'],
                'description': row['description'],
            }
            old_score = row['fit_score']
            print(f"\n  ── {row['title']} @ {row['company']}  (DB score={old_score}) ──")
            result = scorer.score_job(job_data)
            new_score = result['fit_score']
            bd = result['breakdown']
            ai_d = result.get('ai_details', {})
            print(f"     NEW score={new_score:.1f}  (Δ {new_score - old_score:+.1f})")
            print(f"     AI: {bd.get('ai_semantic',0):.1f}  method={ai_d.get('method')}  fallback={ai_d.get('is_fallback')}")
            print(f"     tech={bd.get('technical',0):.1f}  culture={bd.get('culture',0):.1f}  "
                  f"industry={bd.get('industry',0):.1f}  role={bd.get('role',0):.1f}  "
                  f"elig={bd.get('eligibility',0):.1f}  visa={bd.get('visa',0):.1f}")
            print(f"     loc={result.get('location_flag')}  seniority={result.get('seniority_flag')}")

    rescore_group("TOP 5 JOBS — re-scored with new weights", top_jobs)
    rescore_group("BOTTOM 5 JOBS — re-scored with new weights", bottom_jobs)

    print(f"\n{SEP}")
    print("  TIP: Compare 'DB score' vs 'NEW score' to validate recalibration.")
    print("  Run score_audit.py after a fresh scrape to see the new distribution.")
    print(SEP)


if __name__ == '__main__':
    main()
