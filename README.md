# JobHunter

Built this in a New York winter because it was too cold to go outside and I needed a job. Started as a tool to help my mates find work too, then it got out of hand.

Autonomous job matching engine that scrapes, deduplicates, and semantically scores thousands of listings per run against a structured candidate profile. Hybrid scoring: keyword signals, sentence-transformer embeddings, location/visa/seniority gating, and an LLM pass for high-confidence matches with live company research. It found me interviews at two sovereign AI startups in the same week.

---

## What it does

1. **Scrapes** LinkedIn, BuiltIn, Y Combinator, and Seek on a 3-hour cron
2. **Deduplicates** across sources using URL + title normalisation
3. **Scores** every listing 0–100 against a structured candidate profile (skills, industries, visa status, seniority, location)
4. **Gates** top matches through an LLM (Kimi/Moonshot) for deeper reasoning and company context
5. **Alerts** immediately on high matches (≥78), batches the rest into a daily digest
6. **Dashboard** — Flask web UI to review, score-filter, generate tailored CVs, and track applications

---

## Scoring pipeline

| Stage | Method | Signal |
|---|---|---|
| Hard gates | Rule-based | Visa status, seniority, location feasibility |
| Keyword match | Weighted token overlap | Tech stack, role titles, industries |
| Semantic match | Sentence-transformer embeddings | Meaning-level skill/role alignment |
| LLM gate | Kimi `moonshot-v1-8k` | Company quality, role fit, reasoning |

Scores below 40 are dropped silently. Scores ≥78 trigger an immediate email alert.

---

## Setup

### Prerequisites
- Python 3.11+
- `KIMI_API_KEY` (Moonshot AI — used for scoring, cover letters, CV generation, and setup onboarding)
- `GMAIL_USER` + `GMAIL_APP_PASSWORD` for email alerts (optional)

### Install

```bash
git clone https://github.com/harveyhoulahan/JobHunter
cd JobHunter
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in your keys
```

### First run — profile setup

```bash
python web_app.py           # starts on http://localhost:5002
# visit /setup — upload your CV (+ optional docs)
# Kimi extracts your full profile and search terms automatically
```

### Run the scraper

```bash
python src/main.py          # single run
python src/scheduler/run.py # continuous (every 3 hours)
```

### Dashboard

```bash
python web_app.py           # http://localhost:5002
```

---

## Project structure

```
JobHunter/
├── web_app.py              # Flask dashboard + API
├── src/
│   ├── main.py             # Orchestrator
│   ├── profile.py          # Candidate profile loader
│   ├── scrapers/           # LinkedIn, BuiltIn, Seek, YC scrapers
│   ├── scoring/            # Hybrid scoring engine + AI scorer
│   ├── alerts/             # Email/SMS alert delivery
│   ├── applying/           # CV generator, cover letter generator
│   ├── database/           # SQLite models + query layer
│   ├── scheduler/          # Cron runner
│   └── tools/              # DB pruning, score audit utilities
├── scripts/                # One-off maintenance scripts
├── tests/                  # Test suite
├── config/                 # Runtime config (gitignored)
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS / JS
├── Dockerfile
├── docker-compose.yml
├── railway.json            # Railway deployment config
└── render.yaml             # Render deployment config
```

---

## Deployment

The app runs as a single Flask process. Deploy anywhere that can run Python:

**Railway / Render** — configs included (`railway.json`, `render.yaml`)

**Docker**
```bash
docker compose up --build
```

**Self-hosted cron**
```bash
# Add to crontab — runs scraper every 3 hours
0 */3 * * * cd /path/to/JobHunter && venv/bin/python src/scheduler/run.py
```

---

## Personalising for your own use

