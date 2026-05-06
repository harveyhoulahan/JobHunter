#!/usr/bin/env python3
"""
JobHunter Web Dashboard
Simple web interface for managing job applications
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for
from sqlalchemy import desc
from src.database.models import Database, Job, SearchHistory
from datetime import datetime
from loguru import logger
import threading
import os
import json

app = Flask(__name__)
db = Database()
scrape_lock = threading.Lock()
scrape_running = False
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')


def _read_json_file(path: str, default_value):
    """Read JSON file safely with fallback."""
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed reading JSON file {path}: {e}")
    return default_value


def _write_json_file(path: str, data) -> None:
    """Write JSON file safely."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


@app.route('/')
def index():
    """Main dashboard - shows all jobs"""
    session = db.get_session()
    try:
        # Get jobs grouped by priority tiers
        # Only show NEW jobs (not applied) by default
        all_jobs = session.query(Job)\
            .filter(Job.applied == False)\
            .order_by(Job.fit_score.desc(), Job.created_at.desc())\
            .limit(200)\
            .all()
        
        # Group jobs by score tiers (fit_score is already a float, not a SQLAlchemy column at this point)
        top_matches = []
        great_matches = []
        good_matches = []
        
        for j in all_jobs:
            score = float(j.fit_score) if j.fit_score is not None else 0.0
            if score >= 70:
                top_matches.append(j)
            elif score >= 60:
                great_matches.append(j)
            elif score >= 50:
                good_matches.append(j)
        
        # Get stats
        stats = db.get_application_stats()
        
        # Last scrape info
        last_run = session.query(SearchHistory).filter(SearchHistory.source == 'all').order_by(desc(SearchHistory.timestamp)).first()
        last_scrape = None
        if last_run:
            last_scrape = {
                'timestamp': last_run.timestamp,
                'jobs_found': last_run.jobs_found,
                'jobs_new': last_run.jobs_new,
                'duration': last_run.duration_seconds
            }
        
        return render_template('dashboard.html', 
                             top_matches=top_matches,
                             great_matches=great_matches,
                             good_matches=good_matches,
                             all_jobs=all_jobs,
                             stats=stats, 
                             last_scrape=last_scrape)
    finally:
        session.close()


@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    """Job detail page"""
    session = db.get_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            return "Job not found", 404
        
        return render_template('job_detail.html', job=job)
    finally:
        session.close()


@app.route('/api/mark_applied', methods=['POST'])
def mark_applied():
    """Mark a job as applied"""
    try:
        data = request.get_json(silent=True) or {}
        job_id = data.get('job_id')
        cv_version = data.get('cv_version', 'Unknown')
        method = data.get('method', 'linkedin')
        
        if not job_id:
            return jsonify({'success': False, 'error': 'Job ID required'}), 400
        
        db.mark_applied(
            job_id=job_id,
            cv_version=cv_version,
            application_method=method,
            notes=f"Applied on {datetime.now().strftime('%Y-%m-%d')}"
        )
        return jsonify({'success': True, 'message': 'Marked as applied'})
    except Exception as e:
        logger.error(f"Error in mark_applied: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/update_status', methods=['POST'])
def update_status():
    """Update job status"""
    data = request.json
    job_id = data.get('job_id')
    status = data.get('status')
    notes = data.get('notes', '')
    
    try:
        db.update_job_status(job_id, status, notes)
        return jsonify({'success': True, 'message': f'Updated to {status}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/add_interview', methods=['POST'])
def add_interview():
    """Add interview round"""
    data = request.json
    job_id = data.get('job_id')
    interview_type = data.get('interview_type')
    notes = data.get('notes', '')
    
    try:
        db.add_interview_round(job_id, interview_type, notes=notes)
        return jsonify({'success': True, 'message': 'Interview added'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/cover_letter/<int:job_id>')
def get_cover_letter(job_id):
    """Get cover letter for a job"""
    try:
        # First get the job details from database to find source_id
        session = db.get_session()
        try:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            source_id = job.source_id
            company = job.company
            title = job.title
        finally:
            session.close()
        
        applications_dir = os.path.join(os.path.dirname(__file__), 'applications')
        
        # Strategy: Look through metadata files to find the matching job
        cover_letter_files = []
        
        for filename in os.listdir(applications_dir):
            if not filename.endswith('_metadata.json'):
                continue
            
            metadata_path = os.path.join(applications_dir, filename)
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Check if this metadata matches our job
                # Match by source_id, company name, or job title
                job_data = metadata.get('job', {})
                meta_source_id = job_data.get('id') or job_data.get('job_id')
                meta_company = job_data.get('company', '')
                meta_title = job_data.get('title', '')
                
                # Match if source_id matches OR (company and title match)
                is_match = False
                if source_id is not None and meta_source_id and str(source_id) == str(meta_source_id):
                    is_match = True
                elif company.lower() in meta_company.lower() and title.lower() in meta_title.lower():
                    is_match = True
                
                if is_match:
                    # Found a match! Get the corresponding cover letter
                    cover_letter_file = metadata_path.replace('_metadata.json', '_cover_letter.txt')
                    if os.path.exists(cover_letter_file):
                        cover_letter_files.append((cover_letter_file, os.path.getmtime(cover_letter_file)))
                        
            except Exception as e:
                logger.debug(f"Error reading metadata {filename}: {e}")
                continue
        
        if not cover_letter_files:
            return jsonify({'success': False, 'error': 'No cover letter found for this job'}), 404
        
        # Get the most recent one if multiple matches
        latest_file = max(cover_letter_files, key=lambda x: x[1])[0]
        
        with open(latest_file, 'r') as f:
            cover_letter_text = f.read()
        
        return jsonify({
            'success': True,
            'cover_letter': cover_letter_text,
            'filename': os.path.basename(latest_file)
        })
    except Exception as e:
        logger.error(f"Error in get_cover_letter: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/applied')
def applied_jobs():
    """View all applied jobs"""
    session = db.get_session()
    try:
        jobs = session.query(Job).filter(
            Job.status.in_(['applied', 'phone_screen', 'interview', 'offer'])
        ).order_by(Job.applied_date.desc()).all()
        
        return render_template('applied.html', jobs=jobs)
    finally:
        session.close()


@app.route('/stats')
def stats():
    """Statistics page"""
    stats = db.get_application_stats()
    
    session = db.get_session()
    try:
        # Get jobs by status
        status_counts = {}
        for status in ['new', 'applied', 'phone_screen', 'interview', 'offer', 'rejected']:
            count = session.query(Job).filter(Job.status == status).count()
            status_counts[status] = count
        
        return render_template('stats.html', stats=stats, status_counts=status_counts)
    finally:
        session.close()


@app.route('/settings')
def settings():
    """Settings page for managing scrape locations and job boards"""
    return render_template('settings.html')


# ── Setup / Onboarding ────────────────────────────────────────────────────────
@app.route('/setup')
def setup():
    """First-time setup wizard — upload CV and build user profile."""
    return render_template('setup.html')


@app.route('/api/setup/ingest_cv', methods=['POST'])
def setup_ingest_cv():
    """Parse uploaded CV PDF and extract a structured profile via Kimi."""
    import tempfile
    try:
        f = request.files.get('cv')
        if not f or not f.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Please upload a PDF file'}), 400

        # Save to temp file and parse
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name

        # Extract raw text from PDF
        cv_text = ''
        try:
            import pdfplumber
            with pdfplumber.open(tmp_path) as pdf:
                cv_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        except Exception:
            try:
                import pypdf
                reader = pypdf.PdfReader(tmp_path)
                cv_text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            except Exception as e:
                return jsonify({'success': False, 'error': f'Could not parse PDF: {e}'}), 400
        finally:
            import os as _os; _os.unlink(tmp_path)

        if len(cv_text.strip()) < 100:
            return jsonify({'success': False, 'error': 'Could not extract enough text from PDF. Try a text-based PDF.'}), 400

        # Call Kimi to extract structured profile
        from src.scoring.ai_scorer import _kimi_client, KIMI_AVAILABLE
        if not KIMI_AVAILABLE or not _kimi_client:
            return jsonify({'success': False, 'error': 'Kimi AI not configured (check KIMI_API_KEY)'}), 503

        system_prompt = """You are a CV parser. Extract structured information from the CV text below and return ONLY a valid JSON object — no markdown, no explanation.

The JSON must have these keys:
{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+1 555 000 0000",
  "linkedin": "https://linkedin.com/in/...",
  "portfolio": "https://...",
  "location": "City, Country",
  "summary": "2-3 sentence professional summary derived from the CV",
  "skills": {
    "core": ["skill1", "skill2", ...],
    "strong": ["skill3", "skill4", ...],
    "familiar": []
  },
  "roles": ["Target Role 1", "Target Role 2"],
  "industries": ["Industry 1", "Industry 2"],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "period": "2023 – present",
      "location": "City, Country",
      "bullets": ["Achievement 1", "Achievement 2", "Achievement 3"]
    }
  ],
  "education": {
    "degree": "B.S. Computer Science",
    "university": "University Name",
    "graduation": "2023",
    "gpa": ""
  },
  "visa_notes": "Citizen / PR / requires sponsorship",
  "min_salary": 0
}

Infer roles and industries from the experience and skills. Keep bullets specific and technical. Return ONLY the JSON."""

        response = _kimi_client.chat.completions.create(
            model='moonshot-v1-32k',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user',   'content': f'CV TEXT:\n\n{cv_text[:12000]}'},
            ],
            temperature=0.1,
            max_tokens=2500,
        )
        raw = (response.choices[0].message.content or '').strip()

        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = '\n'.join(raw.split('\n')[1:])
        if raw.endswith('```'):
            raw = raw[:raw.rfind('```')]

        import json as _json
        profile = _json.loads(raw.strip())
        return jsonify({'success': True, 'profile': profile})

    except Exception as e:
        logger.error(f'setup_ingest_cv error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/setup/save_profile', methods=['POST'])
def setup_save_profile():
    """Save the reviewed profile JSON to config/user_profile.json."""
    import json as _json
    try:
        profile = request.get_json(silent=True) or {}
        if not profile.get('name'):
            return jsonify({'success': False, 'error': 'Profile must include at least a name'}), 400

        profile_path = os.path.join(CONFIG_DIR, 'user_profile.json')
        with open(profile_path, 'w', encoding='utf-8') as fh:
            _json.dump(profile, fh, indent=2, ensure_ascii=False)

        logger.info(f'User profile saved to {profile_path}')
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f'setup_save_profile error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/update_locations', methods=['POST'])
def update_locations():
    """Update scraping locations"""
    try:
        data = request.get_json(silent=True) or {}
        locations = data.get('locations', [])
        
        # Store locations in a config file
        config_path = os.path.join(CONFIG_DIR, 'locations.json')
        _write_json_file(config_path, locations)
        
        return jsonify({'success': True, 'message': 'Locations updated'})
    except Exception as e:
        logger.error(f"Error updating locations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_locations', methods=['GET'])
def get_locations():
    """Get current scraping locations"""
    try:
        config_path = os.path.join(CONFIG_DIR, 'locations.json')
        # Return default locations
        defaults = [
            {'name': 'New York, NY', 'country': 'US', 'enabled': False},
            {'name': 'Los Angeles, CA', 'country': 'US', 'enabled': False},
            {'name': 'San Francisco, CA', 'country': 'US', 'enabled': False},
            {'name': 'Seattle, WA', 'country': 'US', 'enabled': False},
            {'name': 'Austin, TX', 'country': 'US', 'enabled': False},
            {'name': 'Boston, MA', 'country': 'US', 'enabled': False},
            {'name': 'Remote', 'country': 'US', 'enabled': True},
            {'name': 'Freelance', 'country': 'GLOBAL', 'enabled': True},
            {'name': 'Melbourne VIC', 'country': 'AU', 'enabled': True},
            {'name': 'Sydney NSW', 'country': 'AU', 'enabled': True},
            {'name': 'Brisbane QLD', 'country': 'AU', 'enabled': True},
            {'name': 'Gold Coast QLD', 'country': 'AU', 'enabled': True}
        ]
        locations = _read_json_file(config_path, defaults)
        
        return jsonify({'success': True, 'locations': locations})
    except Exception as e:
        logger.error(f"Error getting locations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/update_auto_submit', methods=['POST'])
def update_auto_submit():
    """Update auto-submit settings"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Store settings in config file
        config_path = os.path.join(CONFIG_DIR, 'auto_submit.json')
        _write_json_file(config_path, data)
        
        logger.info(f"Auto-submit settings updated: {data}")
        return jsonify({'success': True, 'message': 'Auto-submit settings updated'})
    except Exception as e:
        logger.error(f"Error updating auto-submit settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_auto_submit', methods=['GET'])
def get_auto_submit():
    """Get current auto-submit settings"""
    try:
        config_path = os.path.join(CONFIG_DIR, 'auto_submit.json')
        # Return default settings
        defaults = {
            'enabled': False,
            'reviewMode': True,
            'platforms': {
                'greenhouse': True,
                'lever': True,
                'email': True,
                'workday': False
            }
        }
        settings = _read_json_file(config_path, defaults)
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error getting auto-submit settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auto_submit', methods=['POST'])
def auto_submit_job_endpoint():
    """
    Trigger auto-submit for a specific job application
    Can be called from email link or dashboard button
    """
    try:
        # Get app_id from query params or POST body
        if request.method == 'GET':
            app_id = request.args.get('app_id')
        else:
            data = request.get_json(silent=True) or {}
            app_id = data.get('app_id')
        
        if not app_id:
            return jsonify({'success': False, 'error': 'app_id required'}), 400
        
        # Find the application metadata
        applications_dir = os.path.join(os.path.dirname(__file__), 'applications')
        metadata_file = os.path.join(applications_dir, f"{app_id}_metadata.json")
        
        if not os.path.exists(metadata_file):
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Load application data
        with open(metadata_file, 'r') as f:
            app_data = json.load(f)
        
        # Find CV and cover letter files
        cv_file = os.path.join(applications_dir, f"{app_id}_resume.pdf")
        cover_letter_file = os.path.join(applications_dir, f"{app_id}_cover_letter.txt")
        
        if not os.path.exists(cv_file):
            return jsonify({'success': False, 'error': 'CV file not found'}), 404
        
        # Import auto-submit module
        from src.applying.auto_submit import AutoSubmitManager
        
        # Get auto-submit settings
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'auto_submit.json')
        review_mode = True  # Default to review mode for safety
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                settings = json.load(f)
                review_mode = settings.get('reviewMode', True)
        
        # Initialize auto-submitter
        submitter = AutoSubmitManager(review_mode=review_mode)
        
        # Submit application
        job_data = app_data.get('job', {})
        result = submitter.submit_application(
            job_data,
            cv_file,
            cover_letter_file if os.path.exists(cover_letter_file) else None
        )
        
        # If successful, mark as applied in database
        if result.get('success'):
            job_id = app_data.get('job', {}).get('id')
            if job_id:
                db.mark_applied(
                    job_id=job_id,
                    cv_version=os.path.basename(cv_file),
                    application_method=result.get('method', 'auto_submit'),
                    notes=f"Auto-submitted via {result.get('method')} on {datetime.now().strftime('%Y-%m-%d')}"
                )
        
        # Return result (for GET requests, show HTML page; for POST, return JSON)
        if request.method == 'GET':
            # Return HTML page with result
            status = result.get('status', 'unknown')
            method = result.get('method', 'unknown')
            
            if status == 'submitted':
                message = f"✅ Application successfully submitted via {method}!"
                color = "#10b981"
            elif status == 'ready_for_review':
                message = f"⚠️ Application filled out and ready for your review via {method}"
                color = "#f59e0b"
            else:
                message = f"❌ Auto-submit failed: {result.get('error', 'Unknown error')}"
                color = "#ef4444"
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Auto-Submit Result</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: #f3f4f6;
        }}
        .container {{
            background: white;
            padding: 48px;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-width: 500px;
            text-align: center;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 24px;
        }}
        .message {{
            font-size: 20px;
            font-weight: 600;
            color: {color};
            margin-bottom: 24px;
        }}
        .details {{
            color: #6b7280;
            margin-bottom: 32px;
        }}
        .btn {{
            background: #2563eb;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{'✅' if status == 'submitted' else '⚠️' if status == 'ready_for_review' else '❌'}</div>
        <div class="message">{message}</div>
        <div class="details">
            <strong>Job:</strong> {job_data.get('title', 'Unknown')}<br>
            <strong>Company:</strong> {job_data.get('company', 'Unknown')}<br>
            <strong>Method:</strong> {method}<br>
            <strong>CV:</strong> {os.path.basename(cv_file)}
        </div>
        <a href="http://localhost:5002" class="btn">← Back to Dashboard</a>
    </div>
</body>
</html>
            """
            return html
        else:
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in auto_submit_job: {e}")
        if request.method == 'GET':
            return f"<h1>Error</h1><p>{str(e)}</p>", 500
        else:
            return jsonify({'success': False, 'error': str(e)}), 500


def _start_scrape_job():
    """Kick off a background scrape run if none is running"""
    global scrape_running
    with scrape_lock:
        if scrape_running:
            return False
        scrape_running = True
    
    def runner():
        global scrape_running
        try:
            from src.main import JobHunter
            hunter = JobHunter()
            hunter.run()
        finally:
            with scrape_lock:
                scrape_running = False
    
    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return True


@app.route('/api/run_scrape', methods=['POST'])
def run_scrape():
    """Trigger a background scrape run"""
    started = _start_scrape_job()
    if not started:
        return jsonify({'success': False, 'error': 'Scrape already running'}), 409
    return jsonify({'success': True, 'message': 'Scrape started'}), 202


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status for mobile remote"""
    try:
        stats = db.get_application_stats()
        return jsonify({
            'success': True,
            'online': True,
            'stats': stats,
            'scrape_running': scrape_running
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/jobs/recent', methods=['GET'])
def get_recent_jobs():
    """Get recent jobs for mobile remote"""
    session = db.get_session()
    try:
        jobs = session.query(Job).order_by(Job.created_at.desc()).limit(10).all()
        return jsonify({
            'success': True,
            'jobs': [{
                'id': j.id,
                'title': j.title,
                'company': j.company,
                'fit_score': j.fit_score,
                'created_at': j.created_at.isoformat() if j.created_at else None
            } for j in jobs]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/get_search_preferences', methods=['GET'])
def get_search_preferences():
    """Get search preferences for work type toggles."""
    try:
        config_path = os.path.join(CONFIG_DIR, 'search_preferences.json')
        defaults = {
            'work_types': {
                'remote': True,
                'onsite': True,
                'hybrid': True
            }
        }
        prefs = _read_json_file(config_path, defaults)
        return jsonify({'success': True, 'preferences': prefs})
    except Exception as e:
        logger.error(f"Error getting search preferences: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/update_search_preferences', methods=['POST'])
def update_search_preferences():
    """Update search preferences for work type toggles."""
    try:
        data = request.get_json(silent=True) or {}
        work_types = data.get('work_types', {})
        normalized = {
            'work_types': {
                'remote': bool(work_types.get('remote', True)),
                'onsite': bool(work_types.get('onsite', True)),
                'hybrid': bool(work_types.get('hybrid', True))
            }
        }
        # Ensure at least one work type is active.
        if not any(normalized['work_types'].values()):
            return jsonify({'success': False, 'error': 'At least one work type must be enabled'}), 400

        config_path = os.path.join(CONFIG_DIR, 'search_preferences.json')
        _write_json_file(config_path, normalized)
        return jsonify({'success': True, 'message': 'Search preferences updated', 'preferences': normalized})
    except Exception as e:
        logger.error(f"Error updating search preferences: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Generate CV for a specific job ────────────────────────────────────────────
@app.route('/api/generate_cv/<int:job_id>', methods=['POST'])
def generate_cv_for_job(job_id):
    """Trigger CV + cover letter generation for a single job."""
    try:
        from src.database.models import Job
        from src.applying.applicator import JobApplicator

        session = db.get_session()
        try:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404

            job_data = {
                'id':          job.id,
                'title':       job.title,
                'company':     job.company,
                'url':         job.url,
                'description': job.description or '',
                'location':    job.location or '',
                'source':      job.source or '',
                'source_id':   job.source_id or '',
            }
            score_result = {
                'fit_score':    float(job.fit_score or 0),
                'visa_status':  job.visa_status or 'none',
                'seniority_ok': True,
                'location_ok':  True,
                'reasoning':    job.reasoning or '',
            }
        finally:
            session.close()

        applicator = JobApplicator()
        application = applicator.prepare_application(job_data, score_result)
        if not application:
            return jsonify({'success': False, 'error': 'prepare_application returned None — score too low or not eligible'}), 400

        return jsonify({
            'success': True,
            'message': f"CV generated for {job_data['title']} @ {job_data['company']}",
            'cover_letter_preview': (application.get('cover_letter') or '')[:300],
        })

    except Exception as e:
        logger.error(f"generate_cv_for_job error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Application Q&A Assistant ─────────────────────────────────────────────────
@app.route('/api/application_assistant', methods=['POST'])
def application_assistant():
    """
    Kimi-powered chatbot that answers application questions in Harvey's voice.
    POST body: { job_title, job_company, job_description, question }
    """
    try:
        data = request.get_json(silent=True) or {}
        question      = (data.get('question') or '').strip()
        job_title     = (data.get('job_title') or '').strip()
        job_company   = (data.get('job_company') or '').strip()
        job_desc      = (data.get('job_description') or '')[:3000]

        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400

        # Build profile context once
        from src.profile import HARVEY_PROFILE
        from src.scoring.ai_scorer import _kimi_client, KIMI_AVAILABLE

        if not KIMI_AVAILABLE or not _kimi_client:
            return jsonify({'success': False, 'error': 'Kimi AI not configured (check KIMI_API_KEY)'}), 503

        # Construct Harvey's background blurb
        profile = HARVEY_PROFILE
        exp_lines = []
        for e in profile.get('experience', [])[:4]:
            bullets = ' '.join(e.get('bullets', [])[:2])
            exp_lines.append(f"- {e['title']} at {e['company']} ({e.get('period','')}): {bullets[:200]}")

        skills_flat = []
        for cat in profile.get('skills', {}).values():
            skills_flat.extend(cat)

        profile_text = f"""Candidate: Harvey Houlahan
Location: Byron Bay, NSW, Australia (AU citizen — no visa issues for AU/EU/CA/Remote; E-3 for US)
Summary: {profile.get('summary', '')}

Experience:
{chr(10).join(exp_lines)}

Key skills: {', '.join(skills_flat[:40])}
Industries: {', '.join(profile.get('industries', [])[:12])}
"""

        system_prompt = f"""You are Harvey Houlahan's personal application assistant.

Your ONLY job is to write first-person answers to job application questions, in Harvey's voice —
confident, technically precise, concise (2–4 sentences per answer unless more is asked), and genuine.

Never be generic. Ground every answer in Harvey's actual experience below.
Never use phrases like "As an AI" or "I don't have personal experience".
Write as if you ARE Harvey answering directly.

HARVEY'S PROFILE:
{profile_text}

JOB CONTEXT:
Title: {job_title}
Company: {job_company}
Description excerpt: {job_desc[:1000]}
"""

        user_msg = f"Application question: {question}\n\nWrite Harvey's answer:"

        response = _kimi_client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.6,
            max_tokens=500,
        )
        answer = (response.choices[0].message.content or '').strip()
        return jsonify({'success': True, 'answer': answer})

    except Exception as e:
        logger.error(f"Application assistant error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 JobHunter Web Dashboard Starting...")
    print("=" * 60)
    print("\nOpen in your browser:")
    print("👉 http://localhost:5002")
    print("\nPress Ctrl+C to stop\n")
    
    # Use environment variable for port (Vercel compatibility)
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=False, port=port, host='0.0.0.0')

# Vercel serverless handler
handler = app
