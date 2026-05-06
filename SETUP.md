# JobHunter — Setup Guide

A personal AI job-hunting dashboard. Upload your CV once and the app auto-scores every job against your profile, drafts cover letters, and tracks applications.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python3 --version` to check |
| A **Kimi API key** | Sign up at [platform.moonshot.cn](https://platform.moonshot.cn/) — free tier available |
| Chrome (optional) | Only needed for auto-submit features |

---

## 1 · Clone & install

```bash
git clone <repo-url> JobHunter
cd JobHunter
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2 · Configure your API key

```bash
cp .env.example .env           # if .env.example exists, otherwise create .env
```

Open `.env` and set:

```
KIMI_API_KEY=sk-your-key-here
```

> **That's the only required secret.** Everything else is optional.

---

## 3 · Initialise the database

```bash
python migrate_database.py
```

---

## 4 · Start the app

```bash
python web_app.py
```

Open **http://localhost:5002** in your browser.

---

## 5 · Upload your CV (first-time setup)

1. Click **⚙ Setup / Profile** in the left sidebar (or go to http://localhost:5002/setup)
2. Drag-and-drop your CV PDF onto the upload zone and click **Extract with AI**
3. Review and edit the extracted fields (name, skills, target roles, etc.)
4. Click **Save Profile** — your profile is saved to `config/user_profile.json`

The app will now score every job against *your* skills and preferences rather than the defaults.

---

## 6 · Configure job search locations

1. Go to **Settings** in the sidebar
2. Add the cities / regions you want to search
3. Select which job boards to scrape (Seek, LinkedIn, etc.)

---

## 7 · Start finding jobs

Click **🔍 Run Scrape** on the dashboard. Jobs will appear sorted by AI match score.

---

## Daily workflow

```
Dashboard → review new jobs (score ≥ 70 = strong match)
         → click a job to expand
         → Generate Cover Letter  (one click)
         → Generate CV            (tailored, one click)
         → Mark Applied
         → Track in Applied tab
```

---

## Useful commands

```bash
# Re-score all jobs in DB against your current profile
python rescore_all_jobs.py

# Regenerate cover letters for active applications
python regenerate_cover_letters.py

# Run tests
pytest tests/
```

---

## File layout

```
config/
  user_profile.json   ← your personal profile (auto-created, never committed)
  settings.yaml       ← app settings (never committed)
applications/         ← generated CVs & cover letters (never committed)
src/                  ← core logic (scoring, scraping, applying)
templates/            ← HTML templates
static/               ← CSS / JS
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `KIMI_API_KEY not set` | Check your `.env` file and restart the server |
| PDF text extraction fails | Use a text-based PDF (not a scanned image) |
| No jobs showing | Run a scrape from the dashboard first |
| Score seems off | Re-check your skills list in Setup / Profile |

---

## Privacy note

Your profile (`config/user_profile.json`), API keys (`.env`), and generated documents (`applications/`) are all listed in `.gitignore` and will **never be committed** to git.
