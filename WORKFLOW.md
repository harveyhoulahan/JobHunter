# JobHunter - Complete Workflow

## 🚀 Features

### 1. **Optimized Job Scraping** (5 min vs 10 min)
- Checks database for duplicates **BEFORE** fetching descriptions
- Only fetches descriptions for new jobs
- Saves ~5-7 minutes per run

### 2. **AI-Powered Scoring**
- Semantic matching using sentence transformers
- Analyzes job title + description + company
- Scores 0-100 based on profile fit

### 3. **Auto-Apply CV Generation** ✨ NEW
- Automatically generates customized CVs for jobs with score >= 50%
- Creates personalized cover letters
- Highlights relevant skills and experience per job
- Stores in `applications/` directory

### 4. **Application Tracking**
- Track which CV/cover letter you used
- Monitor interview rounds and status
- Record offer details
- Get application statistics

## 📊 Quick Start

### Run the complete workflow:
```bash
python3 src/main.py
```

Or test it first:
```bash
python3 test_full_workflow.py
```

### Manage your applications:
```bash
python3 -i manage_applications.py
>>> get_stats()           # View application statistics
>>> view_top_jobs(10)     # See top-scoring jobs
```

### Track applications:
```python
# When you apply to a job
mark_as_applied(job_id, "ML_Resume_v3.pdf", "linkedin")

# When you get a phone screen
update_status(job_id, "phone_screen", "Scheduled for Tuesday 2pm")

# Log interview rounds
add_interview(job_id, "technical", "Discussed ML pipelines, went well")
```

## ⚙️ Configuration

Edit `src/main.py` to customize:

```python
'auto_apply': {
    'enabled': True,      # Enable CV generation
    'min_score': 50.0     # Minimum score to generate CV (50%)
}
```

## 📁 Directory Structure

```
JobHunter/
├── applications/              # Generated CVs and cover letters (auto-created)
├── src/
│   ├── main.py               # Main workflow orchestrator
│   ├── applying/             # Auto-apply module
│   │   ├── applicator.py     # Job application logic
│   │   └── cv_generator.py   # CV customization
│   ├── scoring/              # AI scoring engine
│   ├── scrapers/             # Job board scrapers
│   └── database/             # Database models
├── manage_applications.py    # Application management CLI
├── migrate_database.py       # Database migration tool
├── test_full_workflow.py     # Complete workflow test
└── NY RESUME.pdf            # Your base resume
```

## 🎯 Workflow Steps

1. **Scrape** - Get jobs from LinkedIn & BuiltIn NYC (~585 jobs)
2. **Filter** - Check database for duplicates (~530 duplicates)
3. **Fetch** - Get descriptions only for new jobs (~55 new)
4. **Score** - AI scoring using semantic matching
5. **Alert** - Send email for high matches (>70%)
6. **Auto-apply** - Generate CVs for jobs >= 50%
7. **Track** - Log everything to database

## 📈 Performance

- **Before optimization**: ~10 minutes per run
- **After optimization**: ~5 minutes per run
- **Time saved**: ~50% faster
- **CVs generated**: Automatic for all jobs >= 50%

## 🔧 Database Migration

If you need to update the database schema:
```bash
python3 migrate_database.py
```

This adds the new application tracking columns.

## 📝 Notes

- Auto-apply is **enabled by default** but only generates CVs (doesn't submit)
- All generated materials are stored in `applications/`
- Database automatically tracks application status
- Scores are based on your profile in `src/profile.py`
