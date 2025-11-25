# JobHunter Command Reference

## Setup Commands

```bash
# Initial setup (run once)
chmod +x setup.sh
./setup.sh

# Activate virtual environment (run every time you open terminal)
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt
```

## Running the System

```bash
# Single run (test mode)
python src/main.py

# Continuous mode (every 3 hours)
python src/scheduler/run.py

# Run in background (nohup)
nohup python src/scheduler/run.py > logs/nohup.out 2>&1 &

# Check if running
ps aux | grep jobhunter

# Stop background process
pkill -f scheduler/run.py
```

## Cron Setup

```bash
# Edit crontab
crontab -e

# Add this line (runs every 3 hours)
0 */3 * * * cd /Users/harveyhoulahan/Desktop/JobHunter && /Users/harveyhoulahan/Desktop/JobHunter/venv/bin/python src/main.py >> logs/cron.log 2>&1

# View current cron jobs
crontab -l

# Remove all cron jobs
crontab -r
```

## Database Commands

```bash
# Open database
sqlite3 data/jobhunter.db

# View all jobs
sqlite3 data/jobhunter.db "SELECT title, company, fit_score FROM jobs ORDER BY fit_score DESC LIMIT 20;"

# View high-match jobs
sqlite3 data/jobhunter.db "SELECT title, company, fit_score, url FROM jobs WHERE fit_score >= 70 ORDER BY fit_score DESC;"

# Count jobs by source
sqlite3 data/jobhunter.db "SELECT source, COUNT(*) as count FROM jobs GROUP BY source;"

# Recent jobs (last 24 hours)
sqlite3 data/jobhunter.db "SELECT title, company, fit_score FROM jobs WHERE created_at >= datetime('now', '-1 day') ORDER BY fit_score DESC;"

# Jobs with E-3 visa mention
sqlite3 data/jobhunter.db "SELECT title, company, fit_score FROM jobs WHERE visa_status = 'explicit' ORDER BY fit_score DESC;"

# Export to CSV
sqlite3 -header -csv data/jobhunter.db "SELECT * FROM jobs;" > jobs_export.csv

# Backup database
cp data/jobhunter.db data/jobhunter_backup_$(date +%Y%m%d).db

# View search history
sqlite3 data/jobhunter.db "SELECT timestamp, source, jobs_found, jobs_new FROM search_history ORDER BY timestamp DESC LIMIT 10;"
```

## Viewing Logs

```bash
# View latest logs
tail -f logs/jobhunter.log

# View last 100 lines
tail -n 100 logs/jobhunter.log

# Search logs for errors
grep -i error logs/jobhunter.log

# View logs from today
grep "$(date +%Y-%m-%d)" logs/jobhunter.log

# Count successful runs
grep "Job hunt cycle complete" logs/jobhunter.log | wc -l
```

## Configuration

```bash
# Edit main configuration
nano config/settings.yaml

# Edit environment variables
nano .env

# Test configuration
python -c "import yaml; print(yaml.safe_load(open('config/settings.yaml')))"
```

## Testing

```bash
# Run all tests
pytest tests/test_jobhunter.py -v

# Run specific test
pytest tests/test_jobhunter.py::TestJobScorer::test_perfect_ml_job -v

# Run with coverage
pytest tests/test_jobhunter.py --cov=src --cov-report=html

# Test email delivery
python -c "
from src.alerts.notifications import EmailAlerter
email = EmailAlerter()
result = email.send_immediate_alert({
    'title': 'Test Job',
    'company': 'Test Company',
    'url': 'https://test.com',
    'fit_score': 85,
    'matches': {'tech': ['Python'], 'industry': [], 'role': []},
    'reasoning': 'This is a test alert',
    'visa_status': 'explicit',
    'location': 'NYC'
}, 'your-email@example.com')
print('Email sent!' if result else 'Email failed')
"

# Test scraper
python -c "
from src.scrapers.indeed import IndeedScraper
scraper = IndeedScraper()
jobs = scraper.search_jobs(['Software Engineer'], 'New York, NY')
print(f'Found {len(jobs)} jobs')
"

# Test scoring
python -c "
from src.scoring.engine import score_job
result = score_job({
    'title': 'ML Engineer',
    'company': 'AI Startup',
    'description': 'Python, ML, AWS, NLP, E-3 visa sponsorship',
    'location': 'NYC'
})
print(f'Score: {result[\"fit_score\"]}/100')
"
```

## Docker Commands

```bash
# Build image
docker build -t jobhunter .

# Run container
docker run -d --name jobhunter \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  jobhunter

# Using docker-compose
docker-compose up -d

# View logs
docker logs -f jobhunter

# Stop container
docker stop jobhunter

# Remove container
docker rm jobhunter

# Access container shell
docker exec -it jobhunter /bin/bash

# Stop via docker-compose
docker-compose down
```

## Maintenance

```bash
# Clean old logs (keep last 30 days)
find logs/ -name "*.log" -mtime +30 -delete

# Vacuum database (optimize)
sqlite3 data/jobhunter.db "VACUUM;"

# Check database size
ls -lh data/jobhunter.db

# Remove jobs older than 60 days
sqlite3 data/jobhunter.db "DELETE FROM jobs WHERE created_at < datetime('now', '-60 days');"

# Update dependencies
pip install --upgrade -r requirements.txt
```

## Debugging

```bash
# Enable debug logging
# In .env: LOG_LEVEL=DEBUG

# Python interactive mode with context
python -i -c "
import sys
sys.path.insert(0, 'src')
from main import JobHunter
from database.models import Database
from scoring.engine import JobScorer

db = Database()
scorer = JobScorer()
print('Context loaded. Use: db, scorer')
"

# Check Python environment
which python
python --version
pip list

# Verify imports
python -c "import requests, bs4, sqlalchemy, loguru; print('All imports OK')"

# Test database connection
python -c "from src.database.models import init_db; db = init_db(); print('Database OK')"
```

## Git Commands (If versioning)

```bash
# Initialize repo
git init
git add .
git commit -m "Initial JobHunter setup"

# Create .gitignore additions
echo "data/*.db" >> .gitignore
echo "logs/*.log" >> .gitignore
echo ".env" >> .gitignore

# Push to GitHub (optional)
git remote add origin https://github.com/yourusername/jobhunter.git
git push -u origin main
```

## Monitoring

```bash
# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "JobHunter Status Report - $(date)"
echo "=================================="
echo ""
echo "Database Stats:"
sqlite3 data/jobhunter.db "
SELECT 
  COUNT(*) as total_jobs,
  COUNT(CASE WHEN fit_score >= 70 THEN 1 END) as high_matches,
  COUNT(CASE WHEN created_at >= datetime('now', '-1 day') THEN 1 END) as last_24h
FROM jobs;
"
echo ""
echo "Recent High Matches:"
sqlite3 data/jobhunter.db "
SELECT title, company, fit_score 
FROM jobs 
WHERE fit_score >= 70 
  AND created_at >= datetime('now', '-7 days')
ORDER BY fit_score DESC 
LIMIT 5;
"
echo ""
echo "Last Run:"
tail -n 20 logs/jobhunter.log | grep "complete"
EOF

chmod +x monitor.sh
./monitor.sh
```

## Quick Diagnostics

```bash
# Full health check
python << EOF
import os
import sys
sys.path.insert(0, 'src')

print("🔍 JobHunter Health Check")
print("=" * 50)

# Check Python version
import sys
print(f"✓ Python {sys.version.split()[0]}")

# Check dependencies
try:
    import requests, bs4, sqlalchemy, loguru
    print("✓ Core dependencies installed")
except ImportError as e:
    print(f"✗ Missing dependency: {e}")

# Check database
try:
    from database.models import Database
    db = Database()
    print("✓ Database accessible")
except Exception as e:
    print(f"✗ Database error: {e}")

# Check .env
if os.path.exists('.env'):
    print("✓ .env file exists")
else:
    print("⚠ .env file missing")

# Check config
if os.path.exists('config/settings.yaml'):
    print("✓ Configuration file exists")
else:
    print("⚠ Configuration file missing")

print("\n✅ System ready!" if all else "⚠️  Fix issues above")
EOF
```

## Performance Tuning

```bash
# Reduce scraping frequency (in config/settings.yaml)
# schedule.interval_hours: 6  # Instead of 3

# Limit results per source
# In src/scrapers/*.py: job_cards[:10]  # Instead of [:20]

# Adjust request delay (in .env)
# REQUEST_DELAY_SECONDS=5  # Slower but safer
```

## Uninstall

```bash
# Stop all processes
pkill -f jobhunter

# Remove cron job
crontab -r

# Remove files (careful!)
cd /Users/harveyhoulahan/Desktop
rm -rf JobHunter

# Remove Docker images (if using Docker)
docker rmi jobhunter
```

---

## Common Workflows

### Daily Check
```bash
# Quick status check
./monitor.sh
```

### Weekly Review
```bash
# Export high matches
sqlite3 -header -csv data/jobhunter.db \
  "SELECT * FROM jobs WHERE fit_score >= 70 AND created_at >= datetime('now', '-7 days');" \
  > weekly_matches.csv
```

### After Configuration Changes
```bash
# Stop scheduler
pkill -f scheduler/run.py

# Test single run
python src/main.py

# Restart scheduler
nohup python src/scheduler/run.py > logs/nohup.out 2>&1 &
```

---

**Tip**: Create aliases in `~/.zshrc` for common commands:
```bash
alias jh-run="cd /Users/harveyhoulahan/Desktop/JobHunter && source venv/bin/activate && python src/main.py"
alias jh-logs="tail -f /Users/harveyhoulahan/Desktop/JobHunter/logs/jobhunter.log"
alias jh-db="sqlite3 /Users/harveyhoulahan/Desktop/JobHunter/data/jobhunter.db"
```
