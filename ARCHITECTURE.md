# Architecture

## System overview

```
Scheduler (every 3h)
        │
        ▼
  src/main.py  ──── Scrapers ──── LinkedIn / BuiltIn / Seek / YC
        │
        ├── Scoring engine  ──── Keyword + embedding + LLM gate
        │
        ├── Database (SQLite)
        │
        └── Alert system  ──── Email (immediate ≥78) / Digest (≥62)

web_app.py (Flask dashboard)
        │
        ├── Job feed + score filters
        ├── CV generator (on-demand, per job)
        ├── Cover letter generator
        ├── Application tracker
        └── /setup  ──── Kimi document ingestion + profile builder
```

## Key components

### Scrapers — `src/scrapers/`

| File | Source | Method |
|---|---|---|
| `linkedin.py` | LinkedIn | HTTP + BeautifulSoup, paginated search |
| `builtin.py` | BuiltIn | HTTP scrape |
| `seek.py` | Seek (AU) | HTTP scrape |
| `yc.py` | Y Combinator | HTTP scrape |

All scrapers extend `BaseScraper` which handles rate limiting (2–5 s delays), retry logic, user-agent rotation, and deduplication by URL.

### Scoring engine — `src/scoring/`

Three-layer pipeline, runs per job:

1. **Hard gates** (`engine.py`) — immediately discard if visa impossible, seniority mismatch, location infeasible
2. **Hybrid scorer** (`engine.py`) — weighted sum of:
   - Keyword overlap (skills, role titles, industries) — fast, no model
   - Sentence-transformer embedding cosine similarity — meaning-level alignment
3. **AI gate** (`ai_scorer.py`) — jobs scoring ≥62 get a Kimi `moonshot-v1-8k` call for reasoning, company research, and final confidence adjustment

### Candidate profile — `src/profile.py`

Loads `config/user_profile.json` if present (written by `/setup`), otherwise falls back to the hardcoded `HARVEY_PROFILE` constant. Profile contains: skills (core/strong/familiar), target roles, industries, visa status, location, salary floor, and search terms used by each scraper.

### Alert system — `src/alerts/`

- Immediate email for score ≥78
- Daily digest for 62–77
- Nothing sent below 62 (stored in DB only)

### CV + cover letter generation — `src/applying/`

On-demand from the dashboard. `cv_generator.py` parses the base resume PDF, then Kimi rewrites/tailors it to the specific job. `cover_letter_generator.py` follows the same pattern. Both write output to `applications/`.

### Dashboard — `web_app.py`

Flask app on port 5002. Key routes:

| Route | Purpose |
|---|---|
| `/` | Job feed, filterable by score/source/status |
| `/setup` | Onboarding — upload CVs, Kimi extracts profile |
| `/api/generate_cv` | Trigger CV generation for a job |
| `/api/rescore` | Re-run scorer on stored jobs |
| `/api/mark_applied` | Log application |

### Database — `src/database/`

SQLite via SQLAlchemy. Two main tables:
- **`jobs`** — all scraped listings with scores, reasoning, status
- **`search_history`** — per-run stats (source, count, duration)

## Data flow

```
Scraper → raw JobListing
       → dedup check (URL in DB?) → skip if seen
       → HardGate → drop if fails
       → HybridScore → 0-100
       → if score ≥ 62 → AI gate → adjusted score + reasoning
       → write to DB
       → if score ≥ 78 → immediate email alert
       → if score 62-77 → add to digest queue
```

## Configuration

All runtime config lives in `config/` (gitignored):
- `user_profile.json` — candidate profile (written by `/setup`)
- `locations.json` — scraping location list
- `auto_submit.json` — auto-apply settings

Environment variables (`.env`):
- `KIMI_API_KEY` — required for scoring, CV/letter generation, setup
- `GMAIL_USER` / `GMAIL_APP_PASSWORD` — optional, for email alerts
