# 🛠️ How to Use VS Code Extensions for JobHunter

Quick guide for the extensions you just installed.

---

## 📊 1. SQLite Viewer - Inspect Your Job Database

**What it does:** View your job database visually - no SQL needed!

### How to Use:

1. **Open the database:**
   - Press `Cmd+P` (Quick Open)
   - Type: `jobhunter.db`
   - Select: `src/data/jobhunter.db`
   - Click the database file

2. **View tables:**
   - You'll see a visual spreadsheet view
   - Tables available:
     - `jobs` - All scraped jobs
     - `search_history` - Your search runs
     - `alerts` - Email alerts sent

3. **Browse jobs:**
   - Click the `jobs` table
   - See all columns: title, company, fit_score, status, etc.
   - Sort by clicking column headers
   - Filter/search in real-time

4. **Check which jobs you applied to:**
   - Look for `status = 'applied'`
   - See `applied_date`, `cv_version`
   - Track interview progress

**Quick Action:**
```
Cmd+P → type "jobhunter.db" → Enter
```

---

## 🌐 2. Live Server - Real-time Dashboard Preview

**What it does:** Auto-refreshes your web dashboard when you edit HTML/CSS

### How to Use:

1. **Start Live Server:**
   - Right-click any file in `templates/` folder
   - Select: "Open with Live Server"
   - OR click "Go Live" in bottom-right status bar

2. **Edit dashboard styling:**
   - Open `static/style.css`
   - Change colors, fonts, spacing
   - Browser auto-refreshes instantly!

3. **Customize dashboard:**
   - Edit `templates/dashboard.html`
   - See changes live without restarting Flask

**Example Edit:**
```css
/* In static/style.css */
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    /* Change to your favorite colors! */
}
```

**Note:** For Flask app changes (Python), you still need to restart `web_app.py`

---

## 📓 3. Jupyter Notebooks - Interactive ML Testing

**What it does:** Test your AI scoring logic interactively

### How to Use:

1. **Create a test notebook:**
   - Press `Cmd+Shift+P`
   - Type: "Create New Jupyter Notebook"
   - Save as `test_scoring.ipynb`

2. **Test job scoring:**
   ```python
   # Cell 1: Import
   from src.scoring.engine import JobScorer
   from src.database.models import Database
   
   db = Database()
   scorer = JobScorer()
   
   # Cell 2: Load a job
   session = db.get_session()
   from src.database.models import Job
   job = session.query(Job).first()
   
   print(f"Job: {job.title} at {job.company}")
   print(f"Score: {job.fit_score}%")
   print(f"Match: {job.reasoning}")
   
   # Cell 3: Test different descriptions
   test_job = {
       'title': 'ML Engineer',
       'company': 'Test Corp',
       'description': 'We need Python, ML, AWS experience...'
   }
   
   result = scorer.score_job(test_job)
   print(f"Test Score: {result['fit_score']}%")
   ```

3. **Experiment with AI models:**
   - Test different embeddings
   - Adjust scoring thresholds
   - Debug match logic

**Run a cell:** `Shift+Enter`

---

## 🔍 4. GitLens - See Code History

**What it does:** Shows who changed what, when, and why (blame annotations)

### How to Use:

1. **Inline blame:**
   - Open any Python file
   - You'll see gray text at end of each line
   - Shows last commit message & author
   - Hover to see full commit details

2. **File history:**
   - Right-click any file
   - Select: "Open File History"
   - See all changes over time
   - Click to compare versions

3. **View recent changes:**
   - Click "GitLens" icon in sidebar (left)
   - See recent commits
   - View what changed in each commit

**Useful for:**
- "When did I add auto-apply feature?"
- "What changed in the last hour?"
- "How did I fix that bug before?"

---

## 🎨 5. Rainbow CSV - Pretty CSV Files

**What it does:** Makes CSV data readable with colors

### How to Use:

1. **Export job data:**
   ```python
   # In Python console or script
   from src.database.models import Database, Job
   import csv
   
   db = Database()
   session = db.get_session()
   jobs = session.query(Job).filter(Job.fit_score >= 50).all()
   
   with open('high_scoring_jobs.csv', 'w') as f:
       writer = csv.writer(f)
       writer.writerow(['Company', 'Title', 'Score', 'Status', 'URL'])
       for job in jobs:
           writer.writerow([job.company, job.title, job.fit_score, job.status, job.url])
   ```

2. **Open the CSV:**
   - Click `high_scoring_jobs.csv`
   - Each column has a different color
   - Easy to read and scan

3. **Query CSV like SQL:**
   - Press `F1`
   - Type: "Rainbow CSV: Query"
   - Write SQL: `SELECT * FROM high_scoring_jobs WHERE Score > 80`
   - See results instantly

---

## 🏃 6. Code Runner - Quick Python Execution

**What it does:** Run Python scripts with one click (no terminal needed)

### How to Use:

1. **Run any Python file:**
   - Open a `.py` file
   - Click the "▶" play button (top-right)
   - OR press `Ctrl+Option+N`
   - Output appears in bottom panel

2. **Run selected code:**
   - Highlight some Python code
   - Press `Ctrl+Option+N`
   - Runs just that selection

**Example:**
```python
# Highlight this and press Ctrl+Option+N
from src.database.models import Database
db = Database()
stats = db.get_application_stats()
print(f"Applied to {stats['applied']} jobs!")
```

---

## 🎯 Most Useful Right Now

### For Daily Job Hunting:

1. **SQLite Viewer** - Check which jobs you've applied to
   - `Cmd+P` → `jobhunter.db` → View `jobs` table
   - Filter by `status = 'applied'`

2. **Live Server** - Customize dashboard colors/layout
   - Right-click `dashboard.html` → "Open with Live Server"
   - Edit `style.css` and see changes instantly

### For Development/Debugging:

3. **Jupyter Notebooks** - Test AI scoring
   - Create notebook: `Cmd+Shift+P` → "New Jupyter Notebook"
   - Test scoring logic interactively

4. **Code Runner** - Quick script testing
   - Select code → `Ctrl+Option+N`
   - Faster than switching to terminal

### For Understanding Changes:

5. **GitLens** - See what you changed
   - Automatically shows inline blame
   - Right-click file → "Open File History"

---

## 🎬 Quick Demo Workflow

**1. View Jobs in Database:**
```
Cmd+P → "jobhunter.db" → Click jobs table → Sort by fit_score
```

**2. Customize Dashboard:**
```
Open static/style.css → Change background color → Save
Right-click templates/dashboard.html → "Open with Live Server"
→ See live changes!
```

**3. Test Scoring Logic:**
```
Cmd+Shift+P → "New Jupyter Notebook"
→ Import scorer → Test job descriptions → Adjust thresholds
```

**4. Export to CSV:**
```python
# Run this with Code Runner (Ctrl+Option+N)
from src.database.models import Database, Job
import csv

db = Database()
session = db.get_session()
jobs = session.query(Job).order_by(Job.fit_score.desc()).limit(20).all()

with open('top_20_jobs.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Score', 'Company', 'Title', 'Status'])
    for job in jobs:
        writer.writerow([job.fit_score, job.company, job.title, job.status or 'new'])

print("✓ Exported top 20 jobs to top_20_jobs.csv")
```

Then open `top_20_jobs.csv` - Rainbow CSV makes it beautiful!

---

## ⚡ Keyboard Shortcuts Summary

| Action | Shortcut | What it does |
|--------|----------|--------------|
| Quick Open | `Cmd+P` | Find files fast |
| Command Palette | `Cmd+Shift+P` | Run any command |
| Run Code | `Ctrl+Option+N` | Execute Python |
| Run Cell | `Shift+Enter` | Run Jupyter cell |
| Toggle Terminal | `Ctrl+`` | Show/hide terminal |
| Open SQLite | `Cmd+P` → type DB name | View database |

---

## 🆘 Troubleshooting

**Q: SQLite Viewer not showing data?**
- Make sure database exists: `ls -la src/data/jobhunter.db`
- Run JobHunter first to populate: `python3 src/main.py`

**Q: Live Server won't start?**
- Flask app must be stopped first
- Or change Live Server port in settings

**Q: Jupyter notebook won't run?**
- Install ipykernel: `pip3 install ipykernel`
- Select Python interpreter: Click bottom-right → Choose Python 3.9+

**Q: Code Runner shows error?**
- Check Python path in settings
- Make sure you're in JobHunter directory

---

## 📚 Learn More

- **SQLite Viewer:** Click DB file, explore UI
- **Live Server:** Right-click HTML file → "Open with Live Server"
- **Jupyter:** `Cmd+Shift+P` → "Jupyter: Create New Notebook"
- **GitLens:** Click GitLens icon in sidebar (left)
- **Code Runner:** Click ▶ button (top-right of editor)

---

Enjoy your enhanced development experience! 🚀
