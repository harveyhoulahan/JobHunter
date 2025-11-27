# JobHunter - Automated Job-Hunting & Alert System

**Built for Harvey J. Houlahan**

## Overview

An intelligent, automated job monitoring system that continuously scans multiple job boards, evaluates listings against Harvey's profile, and sends real-time alerts for high-match opportunities.

### Core Features

- **Multi-Source Monitoring**: LinkedIn, BuiltIn, Y Combinator, Seek (Australia), and more
- **Smart Matching**: 0-100 fit scoring based on tech stack, industry, role, and visa sponsorship
- **Real-Time Alerts**: Email/SMS notifications for high-quality matches
- **E-3 Visa Optimization**: Prioritizes visa-friendly employers
- **Deduplication**: Prevents duplicate alerts across sources
- **Continuous Operation**: Runs every 3 hours automatically
- **Global Coverage**: US and Australian job markets with location-based scraper activation

## Architecture

```
JobHunter/
├── src/
│   ├── scrapers/          # Job board connectors
│   ├── parsers/           # NLP extraction & parsing
│   ├── scoring/           # Fit score calculation
│   ├── alerts/            # Notification delivery
│   ├── database/          # Storage layer
│   └── scheduler/         # Orchestration
├── config/
│   └── settings.yaml      # Configuration
├── data/
│   └── jobhunter.db       # SQLite database
├── tests/
└── requirements.txt
```

## Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure settings
cp config/settings.example.yaml config/settings.yaml
# Edit settings.yaml with your email/API keys
```

### Running

```bash
# Run once manually
python src/main.py

# Run with scheduler
python src/scheduler/run.py

# Deploy as cron (every 3 hours)
crontab -e
# Add: 0 */3 * * * cd /path/to/JobHunter && /path/to/venv/bin/python src/main.py
```

## Fit Scoring Algorithm

Jobs are scored 0-100 based on:

| Category | Weight | Criteria |
|----------|--------|----------|
| **Technical Stack** | 40% | Python, Swift, TypeScript, AWS, ML/AI frameworks, React, etc. |
| **Industry** | 25% | Fashion tech, Sustainability, Healthcare, AI/ML, Marketplaces |
| **Role** | 20% | ML Engineer, Software Engineer, Full-Stack, iOS, Backend |
| **Visa Friendliness** | 15% | E-3 mentions, sponsorship availability |

### Alert Thresholds

- **≥70**: Immediate push notification
- **50-69**: Daily digest
- **<50**: Store only (no alert)

## Harvey's Profile

The system matches against:

**Core Skills**: AI/ML (LLMs, NLP, CoreML), Python, Swift/SwiftUI, TypeScript/React, AWS, IoT, Data Engineering

**Industries**: Fashion tech, Sustainability, Healthcare, AI/ML, Marketplaces

**Target Roles**: ML Engineer, Software Engineer, Full-Stack Engineer, iOS Engineer

**Location**: NYC or Remote (US)

**Visa**: E-3 sponsorship required

## Configuration

Edit `config/settings.yaml`:

```yaml
alerts:
  email: harvey@example.com
  sms: "+1234567890"  # Optional
  
thresholds:
  immediate: 70
  digest: 50
  
schedule:
  interval_hours: 3
  
sources:
  - linkedin
  - indeed
  - ziprecruiter
  - angellist
```

## Deployment Options

### 1. AWS Lambda (Serverless)
- Use EventBridge for scheduling
- DynamoDB for storage
- SES for email alerts

### 2. Docker Container
- Deploy to EC2/Digital Ocean
- Use cron for scheduling
- Self-contained and portable

### 3. Local Machine
- Simple cron job
- SQLite database
- Email via SMTP

## Database Schema

**jobs** table:
- id, title, company, url, description, posted_date
- source, fit_score, reasoning
- tech_matches, industry_matches, visa_status
- created_at, clicked, applied

**search_history** table:
- timestamp, source, jobs_found, errors

## API & Dashboard (Optional)

Future enhancement: Web dashboard at `http://localhost:5000`

- View all active opportunities
- Filter by score/industry/source
- Mark as applied/rejected
- Analytics and trends

## License

Private use - Harvey J. Houlahan

---

**Status**: In Development
**Last Updated**: November 2025
