# Quick Start Guide

## Installation (5 minutes)

### Step 1: Run Setup Script
```bash
cd /Users/harveyhoulahan/Desktop/JobHunter
chmod +x setup.sh
./setup.sh
```

This will:
- Create Python virtual environment
- Install all dependencies
- Download NLP models
- Set up database
- Create config files

### Step 2: Configure Credentials

Edit `.env` with your email settings:

**Option A: Outlook/Hotmail (Recommended for you)**
```bash
nano .env
```

Change these lines:
```
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=harveyhoulahan@outlook.com
SMTP_PASSWORD=your-outlook-password
ALERT_EMAIL=harveyhoulahan@outlook.com
```

To get Outlook app password:
1. Go to https://account.microsoft.com/security
2. Click "Advanced security options"
3. Under "App passwords", click "Create a new app password"
4. Copy the generated password and use it above

**Option B: Gmail**
```bash
nano .env
```

Change these lines:
```
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
ALERT_EMAIL=harvey@example.com
```

To get Gmail app password:
1. Go to https://myaccount.google.com/apppasswords
2. Generate new app password
3. Copy and paste it

**Option C: SendGrid (Better for production)**
```
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxx
ALERT_EMAIL=harveyhoulahan@outlook.com
```

### Step 3: Customize Settings (Optional)

Edit `config/settings.yaml`:
```bash
nano config/settings.yaml
```

Key settings:
- `alerts.email.recipients`: Your email
- `alerts.thresholds.immediate`: Alert threshold (default: 70)
- `sources`: Enable/disable job boards
- `schedule.interval_hours`: How often to run (default: 3)

### Step 4: Test Run

```bash
# Activate virtual environment
source venv/bin/activate

# Run once to test
python src/main.py
```

You should see:
```
✓ JobHunter initialized
✓ Scraping jobs...
✓ Found X jobs
✓ Sent Y alerts
```

### Step 5: Run Continuously

**Option A: Using the scheduler**
```bash
python src/scheduler/run.py
```
This runs in foreground, every 3 hours.

**Option B: Using cron (runs in background)**
```bash
crontab -e
```

Add this line:
```
0 */3 * * * cd /Users/harveyhoulahan/Desktop/JobHunter && /Users/harveyhoulahan/Desktop/JobHunter/venv/bin/python src/main.py >> logs/cron.log 2>&1
```

Save and exit. Now it runs automatically every 3 hours!

---

## How It Works

### 1. Job Discovery (Every 3 hours)
- Searches Indeed, LinkedIn, ZipRecruiter
- Looks for: ML Engineer, Software Engineer, AI roles
- Location: NYC + Remote
- Posted within: Last 7 days

### 2. Smart Matching
Each job gets scored 0-100:

| Factor | Weight | What it checks |
|--------|--------|----------------|
| **Tech Stack** | 40% | Python, ML, AWS, Swift, React, etc. |
| **Industry** | 25% | Fashion tech, Healthcare, AI, Sustainability |
| **Role** | 20% | ML Engineer, Software Engineer, etc. |
| **Visa** | 15% | E-3 sponsorship availability |

### 3. Alerts
- **Score ≥ 70**: Immediate email 🔥
- **Score 50-69**: Daily digest 📬
- **Score < 50**: Stored only (no alert)

### 4. Deduplication
Same job from multiple sites? Only alerted once.

---

## What You'll Get

### Immediate Alert Email (Score ≥ 70)
```
Subject: 🎯 High-Match Job: ML Engineer at TechCo

Fit Score: 87/100

Technical Match: Python, ML, AWS, NLP
Industry: AI/ML, Fashion Tech
Visa Status: Explicit sponsorship

Why this matches:
Strong technical alignment with LLM and NLP experience.
Fashion tech industry match. E-3 visa sponsorship mentioned.

[Apply Now →]
```

### Daily Digest (Score 50-69)
Multiple moderate matches in one email, sent at 9 AM.

---

## Viewing Results

### Check the database
```bash
sqlite3 data/jobhunter.db

# Top 10 matches
SELECT title, company, fit_score FROM jobs ORDER BY fit_score DESC LIMIT 10;

# Jobs by source
SELECT source, COUNT(*) FROM jobs GROUP BY source;

# Recent high matches
SELECT title, company, fit_score FROM jobs WHERE fit_score >= 70 ORDER BY created_at DESC;
```

### Check logs
```bash
tail -f logs/jobhunter.log
```

---

## Troubleshooting

### "No jobs found"
- **Cause**: Scrapers might be blocked
- **Fix**: 
  - Check `logs/jobhunter.log` for errors
  - Try with VPN
  - Reduce request frequency in `.env`

### "Email not received"
- **Check spam folder**
- **Verify credentials** in `.env`
- **Test email**:
  ```python
  from src.alerts.notifications import EmailAlerter
  email = EmailAlerter()
  email.send_immediate_alert({
      'title': 'Test Job',
      'company': 'Test',
      'url': 'https://test.com',
      'fit_score': 85,
      'matches': {'tech': ['Python'], 'industry': [], 'role': []},
      'reasoning': 'Test',
      'visa_status': 'explicit'
  }, 'your-email@example.com')
  ```

### "Import errors"
- Make sure virtual environment is activated:
  ```bash
  source venv/bin/activate
  ```

---

## Customization

### Add more job boards
Edit `src/main.py` and add new scraper to `self.scrapers`

### Change search terms
Edit `config/settings.yaml`:
```yaml
sources:
  indeed:
    search_terms:
      - "Your Custom Search Term"
      - "Another Term"
```

### Adjust scoring
Edit weights in `config/settings.yaml`:
```yaml
scoring:
  weights:
    technical_stack: 40  # Change to 50 for more tech focus
    industry_match: 25
    role_match: 20
    visa_friendliness: 15
```

---

## Next Steps

1. ✅ Run test: `python src/main.py`
2. ✅ Check you get an email
3. ✅ Set up cron or scheduler
4. ✅ Let it run for a week
5. ✅ Review matches in database
6. ✅ Adjust search terms/thresholds as needed

---

## Getting Help

Check these files:
- `logs/jobhunter.log` - Detailed logs
- `DEPLOYMENT.md` - Advanced deployment options
- `README.md` - Full documentation

For E-3 visa resources:
- https://www.uscis.gov/working-in-the-united-states/temporary-workers/e-3-specialty-occupation-workers-from-australia
- Track LCA approvals: https://www.dol.gov/agencies/eta/foreign-labor/performance

---

**You're all set! The system will now automatically find and alert you about jobs that match your profile.** 🚀
