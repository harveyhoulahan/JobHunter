# 🌐 JobHunter Web Dashboard

Friendly web interface for managing your job applications - no command line needed!

## 🚀 Quick Start

### 1. Install Flask

```bash
pip3 install flask
```

### 2. Start the Dashboard

```bash
python3 web_app.py
```

### 3. Open in Browser

Visit: **http://localhost:5001**

---

## 📱 Features

### Main Dashboard
- **View all jobs** sorted by match score
- **See status** at a glance (new, applied, interview, etc.)
- **One-click apply** - mark jobs as applied
- **Quick stats** - total jobs, applications, offers, response rate

### My Applications
- **Track progress** for all jobs you've applied to
- **View history** with application dates
- **Update status** as you progress through interviews

### Statistics
- **Response rate** - how many applications lead to responses
- **Conversion metrics** - phone screens → interviews → offers
- **Status breakdown** - jobs by current status

---

## 💡 How to Use

### After Receiving Email with CVs

1. **Open dashboard**: `http://localhost:5001`
2. **Browse jobs** - sorted by match score (highest first)
3. **Click "View Job"** to open posting
4. **Apply on company website** with your customized CV
5. **Click "Mark as Applied"** in dashboard
   - Enter CV filename (e.g., `Cohere_ML_Engineer_Resume.pdf`)
   - Select method (LinkedIn, company site, email)
   - Submit!

### Track Interview Progress

1. Go to **My Applications**
2. Click **"Update Status"** on any job
3. Select new status:
   - Phone Screen
   - Interview
   - Offer
   - Rejected
4. Add notes (optional)

### View Your Stats

1. Click **Statistics** in nav
2. See:
   - Total applications sent
   - Response rate
   - Interview conversion
   - Jobs by status

---

## 🎯 Workflow Example

### Morning: Check Dashboard

```bash
python3 web_app.py
# Open http://localhost:5001
```

**Dashboard shows:**
- 27 new jobs matched
- Top job: Cohere ML Engineer (91.2%)
- Quick stats: 5 applied, 2 interviews, 0 offers

### Apply to Top Job

1. Click **"View Job"** → Opens Cohere posting
2. Upload `Cohere_ML_Engineer_Resume.pdf` from email/applications folder
3. Submit application on Cohere's site
4. Back in dashboard, click **"Mark as Applied"**
5. Fill in:
   - CV: `Cohere_ML_Engineer_Resume.pdf`
   - Method: LinkedIn
6. Click **Submit**

### Week Later: Got Phone Screen

1. Go to **My Applications**
2. Find Cohere job
3. Click **"Update Status"**
4. Select: **Phone Screen**
5. Add note: "30min call scheduled for Friday 2pm"

### After Interview

1. Update status to **Interview**
2. Add note: "Technical round - discussed ML pipelines"

### Got Offer!

1. Update status to **Offer**
2. Add note: "$95k base + equity, starts July 1"

---

## 🛠️ Technical Details

### Backend
- **Flask** web framework
- **SQLAlchemy** database (same as main JobHunter)
- **REST API** for async updates

### Frontend
- **No frameworks** - pure HTML/CSS/JS
- **Responsive design** - works on mobile
- **Modern UI** - purple gradient, clean cards

### Data
Uses the same `data/jobhunter.db` as the main JobHunter app, so all your jobs and applications are synced.

---

## 🔧 Configuration

### Change Port

Edit `web_app.py`:

```python
app.run(debug=True, port=5001, host='0.0.0.0')
#                        ^^^^
# Change to any port you want
```

### Run in Production

For production use (not just local):

```bash
# Install gunicorn
pip3 install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 web_app:app
```

### Auto-Start on Boot

Create a systemd service or use PM2:

```bash
# Install PM2
npm install -g pm2

# Start dashboard
pm2 start web_app.py --name jobhunter-dashboard --interpreter python3

# Save to auto-start
pm2 save
pm2 startup
```

---

## 📊 API Endpoints

The dashboard exposes a simple REST API:

### Mark Job as Applied
```bash
POST /api/mark_applied
{
  "job_id": 123,
  "cv_version": "Cohere_ML_Engineer_Resume.pdf",
  "method": "linkedin"
}
```

### Update Job Status
```bash
POST /api/update_status
{
  "job_id": 123,
  "status": "interview",
  "notes": "Technical round scheduled"
}
```

### Add Interview Round
```bash
POST /api/add_interview
{
  "job_id": 123,
  "interview_type": "technical",
  "notes": "Went well - discussed ML architecture"
}
```

---

## 🚨 Troubleshooting

### Port Already in Use

If port 5001 is taken:

```bash
# Change port in web_app.py
app.run(debug=True, port=8080, host='0.0.0.0')
```

### Database Not Found

Make sure you're in the JobHunter directory:

```bash
cd /Users/harveyhoulahan/Desktop/JobHunter
python3 web_app.py
```

### No Jobs Showing

Run the main JobHunter first to populate database:

```bash
python3 src/main.py
```

---

## 🎨 Customization

### Change Colors

Edit `static/style.css`:

```css
/* Main gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
/* Change to your colors */
```

### Add More Pages

Create new route in `web_app.py`:

```python
@app.route('/my-page')
def my_page():
    return render_template('my_page.html')
```

---

## ✨ Tips

- **Keep dashboard open** while job hunting
- **Refresh after applying** to see updated stats
- **Use notes field** to track important details
- **Check stats weekly** to monitor progress

---

Enjoy your user-friendly job hunting! 🎉
