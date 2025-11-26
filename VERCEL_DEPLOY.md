# JobHunter Dashboard - Vercel Deployment Guide

## ✅ Changes Made

### 1. **Dashboard UX Improvements**
- ✅ Applied jobs now hidden by default (shows "New" jobs only)
- ✅ Full mobile responsiveness added
  - Full-width buttons on mobile
  - Larger touch targets (48px minimum)
  - Responsive modals (95% width on mobile)
  - Stacked layouts for small screens
  - Improved typography scaling

### 2. **Deployment Configuration**
- ✅ `vercel.json` - Vercel deployment config
- ✅ `requirements-vercel.txt` - Minimal dependencies for web dashboard
- ✅ `api/index.py` - Vercel serverless handler
- ✅ Updated `web_app.py` for production (PORT env variable)

## 🚀 Deploy to Vercel

### Step 1: Commit and Push to GitHub

```bash
cd /Users/harveyhoulahan/Desktop/JobHunter

# Add all changes
git add .

# Commit
git commit -m "feat: improve dashboard UX and add Vercel deployment

- Hide applied jobs by default (show only new jobs)
- Add comprehensive mobile responsiveness
- Full-width buttons and larger touch targets on mobile
- Responsive modals and stacked layouts
- Add Vercel deployment configuration
- Add YC Jobs scraper with 3 categories
- Optimize AI scoring weights (50% semantic)"

# Push to GitHub
git push origin main
```

### Step 2: Deploy on Vercel

1. Go to https://vercel.com
2. Sign in with your GitHub account
3. Click "Add New Project"
4. Import your `JobHunter` repository
5. Vercel will auto-detect the configuration from `vercel.json`
6. Click "Deploy"

### Step 3: Environment Variables (Important!)

After deployment, go to your project settings and add:

**Settings → Environment Variables:**
- No environment variables needed for read-only dashboard
- Database is local SQLite (read from repo)

### Step 4: Access on Mobile

Once deployed, you'll get a URL like:
```
https://job-hunter-xxx.vercel.app
```

Add this to your mobile browser and it will work beautifully!

## 📱 Mobile Features

- **Auto-hide applied jobs** - Only see jobs you haven't applied to
- **Full-width action buttons** - Easy to tap
- **Responsive modals** - Fit your screen perfectly
- **Stacked layouts** - No horizontal scrolling
- **Optimized typography** - Readable on small screens

## 🔄 Updates

To update the deployed site:
```bash
git add .
git commit -m "your changes"
git push origin main
```

Vercel auto-deploys on every push to `main` branch!

## ⚠️ Important Notes

1. **Read-Only Dashboard**: The Vercel deployment is best for viewing jobs. For "Mark Applied" to work, you need the database. Consider:
   - Using Vercel Postgres for production database
   - Or keep this as read-only viewer
   - Or deploy with Railway/Render for persistent database

2. **Database**: Currently uses local SQLite. For production:
   - Vercel Postgres (recommended)
   - Supabase
   - PlanetScale
   - Railway Postgres

## 🎯 Next Steps (Optional)

### Connect Production Database

1. Sign up for Vercel Postgres: https://vercel.com/storage/postgres
2. Create a database
3. Add environment variables:
   ```
   DATABASE_URL=postgresql://...
   ```
4. Update `src/database/models.py` to use DATABASE_URL env variable

### Make it Fully Functional

```python
# In src/database/models.py
import os

class Database:
    def __init__(self):
        db_url = os.environ.get('DATABASE_URL', 'sqlite:///data/jobhunter.db')
        self.engine = create_engine(db_url)
```

Then "Mark Applied" will work on mobile!
