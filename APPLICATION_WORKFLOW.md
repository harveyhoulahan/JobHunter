# Application Workflow Guide

Complete end-to-end workflow for applying to jobs with JobHunter.

## 🎯 Overview

JobHunter automates the entire job search pipeline:
1. **Scrape** - Find jobs from LinkedIn, BuiltIn NYC, etc.
2. **Score** - AI ranks jobs based on your profile (semantic matching)
3. **Generate** - Auto-creates customized CVs for jobs >= 50% match
4. **Email** - Sends you all CVs with job details
5. **Track** - Manage applications, interviews, offers

---

## 📧 Step 1: Receive Email with CVs

After running JobHunter, you'll receive an email with:
- **Job list** sorted by match score (highest first)
- **PDF CVs attached** (one per job)
- **Quick apply links** (click to open job posting)
- **Summary stats** (jobs found, new jobs, CVs generated)

### Email Setup

Configure SMTP credentials in your environment or `.env` file:

```bash
# Gmail example
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use app password, not account password
FROM_EMAIL=your-email@gmail.com
TO_EMAIL=harveyhoulahan@outlook.com

# Enable/disable CV emails
ENABLE_CV_EMAILS=true
```

**For Gmail:**
1. Enable 2FA: https://myaccount.google.com/security
2. Create App Password: https://myaccount.google.com/apppasswords
3. Use app password (not your regular password)

**For Outlook/Microsoft:**
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=harveyhoulahan@outlook.com
SMTP_PASSWORD=your-password
```

---

## 💼 Step 2: Apply to Jobs

### From Email
1. **Click "Apply Now"** - Opens job posting
2. **Find matching CV** - PDF filename matches company name
   - Example: `Cohere_ML_Engineer_Resume.pdf` for Cohere
3. **Upload CV** - Use the customized PDF for that specific job
4. **Copy cover letter** - Check `applications/` folder for `.txt` file

### From Applications Folder

All applications saved in `applications/` directory:

```
applications/
├── Cohere_ML_Engineer_Resume.pdf
├── Cohere_ML_Engineer_CoverLetter.txt
├── Cohere_ML_Engineer_metadata.json
├── Anthropic_AI_Researcher_Resume.pdf
├── Anthropic_AI_Researcher_CoverLetter.txt
└── ...
```

**Each application includes:**
- **PDF** - Customized resume highlighting relevant skills
- **TXT** - Cover letter in natural, conversational style (your voice)
- **JSON** - Metadata (job details, score, tech matches)

---

## 📊 Step 3: Track Applications

After applying, mark the job in the database so you can track progress.

### Quick Tracking

```bash
python3 -i manage_applications.py
```

This opens an interactive Python shell with helper functions:

```python
# View current stats
>>> get_stats()

# See top jobs (shows job IDs)
>>> view_top_jobs(10)

# Mark job as applied (use ID from view_top_jobs)
>>> mark_as_applied(123, "Cohere_ML_Engineer_Resume.pdf", "linkedin")
```

### Update Job Status

As you progress through the interview pipeline:

```python
# After phone screen
>>> update_status(123, "phone_screen", "Scheduled for Tuesday")

# After technical interview
>>> add_interview(123, "technical", "Discussed ML architecture - went well")

# After onsite
>>> add_interview(123, "onsite", "Met team, culture fit good")

# Got offer!
>>> update_status(123, "offer", "85k, equity, starts June 1")

# Or rejected
>>> update_status(123, "rejected", "Not moving forward")
```

### Status Flow

```
new → applied → phone_screen → interview → offer
                                         ↘ rejected
                                         ↘ withdrawn
```

---

## 🔄 Complete Workflow Example

### Morning: Run JobHunter

```bash
cd /Users/harveyhoulahan/Desktop/JobHunter
python3 src/main.py
```

**What happens:**
- Scrapes LinkedIn + BuiltIn NYC (~582 jobs)
- Checks database for duplicates (skip already-seen jobs)
- Fetches descriptions for new jobs only (~138 new)
- AI scores each job (semantic matching with your profile)
- Generates CVs for jobs >= 50% match (e.g., 27 CVs)
- **Emails you** all CVs with job list

### Afternoon: Check Email

1. Open email: "🎯 27 Job Applications Ready"
2. Review job list (sorted by match score)
3. Top job: **Cohere - ML Engineer** (91.2% match)

### Apply to Top Job

1. Click "Apply Now" → Opens Cohere job posting
2. Attach `Cohere_ML_Engineer_Resume.pdf` from email or `applications/` folder
3. Copy cover letter from `applications/Cohere_ML_Engineer_CoverLetter.txt`
4. Submit application on Cohere's website

### Track Application

```bash
python3 -i manage_applications.py
>>> view_top_jobs(5)

🎯 Top 5 Jobs:
===================
1. [91.2] 🆕 ML Engineer
   Cohere - New York, NY
   ID: 123
   🔗 https://...

>>> mark_as_applied(123, "Cohere_ML_Engineer_Resume.pdf", "linkedin")
✓ Marked job 123 as applied with CV: Cohere_ML_Engineer_Resume.pdf
```

### Week Later: Phone Screen

```python
>>> update_status(123, "phone_screen", "30min call scheduled for Friday")
>>> get_stats()

APPLICATION STATISTICS
============================================================
Total jobs in database: 582
Applications sent:      1
Phone screens:          1
Interviews:             0
Offers:                 0
Rejections:             0
Response rate:          100.0%
============================================================
```

### After Technical Interview

```python
>>> add_interview(123, "technical", "Discussed ML pipelines, transformers architecture")
>>> update_status(123, "interview")
```

### Got Offer!

```python
>>> update_status(123, "offer", "$95k base, equity, health insurance, starts July 1")
>>> get_stats()

APPLICATION STATISTICS
============================================================
Applications sent:      1
Phone screens:          1
Interviews:             1
Offers:                 1
Response rate:          100.0%
============================================================
```

---

## 🛠️ Automation Tips

### Run Daily

Set up a cron job to run JobHunter every morning:

```bash
crontab -e
```

Add line:
```cron
0 9 * * * cd /Users/harveyhoulahan/Desktop/JobHunter && /usr/bin/python3 src/main.py
```

This runs at 9 AM daily. You'll get an email with new jobs every morning.

### Customize Min Score

Edit `config/settings.yaml`:

```yaml
auto_apply:
  enabled: true
  min_fit_score: 60.0  # Only generate CVs for jobs >= 60% (default: 50%)
```

### Bulk Apply

After receiving email, apply to multiple jobs at once:

```python
# View top 10
>>> view_top_jobs(10)

# Apply to top 5
>>> mark_as_applied(101, "DataDog_Backend_Engineer.pdf", "linkedin")
>>> mark_as_applied(102, "Stripe_ML_Engineer.pdf", "company_site")
>>> mark_as_applied(103, "OpenAI_Researcher.pdf", "email")
>>> mark_as_applied(104, "Meta_AI_Engineer.pdf", "linkedin")
>>> mark_as_applied(105, "Google_Software_Engineer.pdf", "company_site")
```

---

## 📈 Track Your Progress

### View Stats Anytime

```python
>>> get_stats()
```

Shows:
- Total applications sent
- Response rate (phone screens / applications)
- Interview conversion rate
- Offer rate

### Filter by Status

```python
# See all jobs you've applied to
session = db.get_session()
from src.database.models import Job
applied_jobs = session.query(Job).filter(Job.status == 'applied').all()

for job in applied_jobs:
    print(f"{job.title} at {job.company} - {job.applied_date}")
```

### Export to CSV

```python
import csv
session = db.get_session()
jobs = session.query(Job).filter(Job.status.in_(['applied', 'phone_screen', 'interview'])).all()

with open('my_applications.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Company', 'Title', 'Status', 'Score', 'Applied Date'])
    for job in jobs:
        writer.writerow([job.company, job.title, job.status, job.fit_score, job.applied_date])
```

---

## 🚨 Troubleshooting

### Email Not Sending

Check environment variables:
```bash
echo $SMTP_USERNAME
echo $SMTP_HOST
```

Test email manually:
```python
from src.applying.email_sender import ApplicationEmailer
emailer = ApplicationEmailer()
print(f"Email enabled: {emailer.enabled}")
```

### CVs Not Generated

Check logs:
```bash
tail -f logs/jobhunter.log
```

Verify auto-apply is enabled in `config/settings.yaml`:
```yaml
auto_apply:
  enabled: true
```

### Can't Find Job ID

```python
# Search by company name
session = db.get_session()
from src.database.models import Job
jobs = session.query(Job).filter(Job.company.like('%Cohere%')).all()

for job in jobs:
    print(f"ID: {job.id}, Title: {job.title}, Score: {job.fit_score}")
```

---

## 📝 Summary

**Complete workflow:**
1. ✅ Run JobHunter → Generates CVs automatically
2. ✅ Check email → Review jobs + attached CVs
3. ✅ Apply on company website → Use customized CV
4. ✅ Track in database → `mark_as_applied(job_id, "CV.pdf")`
5. ✅ Update status → Phone screen → Interview → Offer

**Key commands:**
```bash
# Run job hunt
python3 src/main.py

# Track applications
python3 -i manage_applications.py
>>> view_top_jobs(10)
>>> mark_as_applied(123, "CV.pdf", "linkedin")
>>> update_status(123, "interview")
>>> get_stats()
```

---

Good luck with your job search! 🚀
