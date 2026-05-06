#!/usr/bin/env python3
"""
JobHunter Web Dashboard
Simple web interface for managing job applications
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from sqlalchemy import desc
from src.database.models import Database, Job, SearchHistory
from src.applying.cover_letter_pdf import CoverLetterPDFGenerator
from src.applying.gpt4_cover_letter import generate_gpt4_cover_letter
from src.scoring.goldcoast_scorer import GoldCoastJobScorer
from src.scrapers.seek import SeekScraper
from datetime import datetime
from loguru import logger
import threading
import os
import json

app = Flask(__name__)
db = Database()
scrape_lock = threading.Lock()
scrape_running = False
goldcoast_scorer = GoldCoastJobScorer()
seek_scraper = SeekScraper()  # Use existing Selenium-based Seek scraper


@app.route('/')
def index():
    """Main dashboard - shows all jobs"""
    session = db.get_session()
    mode = request.args.get('mode', 'tech')  # 'tech' or 'goldcoast'
    
    try:
        # Get jobs based on mode
        if mode == 'goldcoast':
            # Filter for Gold Coast jobs
            all_jobs = session.query(Job)\
                .filter(Job.applied == False)\
                .filter((Job.location.contains('Gold Coast')) | (Job.source == 'seek_goldcoast'))\
                .order_by(Job.fit_score.desc(), Job.created_at.desc())\
                .limit(200)\
                .all()
        else:
            # Tech jobs (existing logic)
            all_jobs = session.query(Job)\
                .filter(Job.applied == False)\
                .filter(Job.source != 'seek_goldcoast')\
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


@app.route('/api/job/<int:job_id>')
def get_job_details(job_id):
    """Get full details for a specific job"""
    try:
        session = db.get_session()
        try:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            job_details = {
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'url': job.url,
                'description': job.description,
                'location': job.location,
                'remote': job.remote,
                'fit_score': float(job.fit_score) if job.fit_score else 0.0,
                'reasoning': job.reasoning,
                'tech_matches': job.tech_matches,
                'industry_matches': job.industry_matches,
                'role_matches': job.role_matches,
                'posted_date': job.posted_date,
                'source': job.source
            }
            
            return jsonify({'success': True, 'job': job_details})
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error getting job details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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


@app.route('/api/cover_letter/<int:job_id>/pdf')
def download_cover_letter_pdf(job_id):
    """Download or preview cover letter as PDF"""
    try:
        # Check if specific filename is requested (for preview)
        filename = request.args.get('filename')
        applications_dir = os.path.join(os.path.dirname(__file__), 'applications')
        
        if filename:
            # Direct preview of specific PDF file
            pdf_path = os.path.join(applications_dir, filename)
            if os.path.exists(pdf_path):
                return send_file(
                    pdf_path,
                    mimetype='application/pdf',
                    as_attachment=False  # Display in browser instead of download
                )
            else:
                return jsonify({'success': False, 'error': 'PDF file not found'}), 404
        
        # Otherwise, find and generate PDF for this job
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
        
        # Read cover letter text
        with open(latest_file, 'r') as f:
            cover_letter_text = f.read()
        
        # Generate PDF
        pdf_generator = CoverLetterPDFGenerator()
        pdf_path = latest_file.replace('_cover_letter.txt', '_cover_letter.pdf')
        
        pdf_generator.generate_pdf(
            cover_letter_text=cover_letter_text,
            job_title=title,
            company_name=company,
            output_path=pdf_path
        )
        
        # Send the PDF file
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"cover_letter_{company.replace(' ', '_')}_{title.replace(' ', '_')[:30]}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF cover letter: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cover_letter/generate/<int:job_id>', methods=['POST'])
def generate_cover_letter(job_id):
    """Generate a new cover letter on-demand for a job"""
    try:
        # Get job details from database
        session = db.get_session()
        try:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            # Prepare job data for cover letter generation
            job_data = {
                'company': job.company,
                'title': job.title,
                'description': job.description or '',
                'location': job.location or '',
                'id': job.source_id or job.id
            }
            
            score_data = {
                'fit_score': float(job.fit_score) if job.fit_score else 0.0,
                'reasoning': job.reasoning or '',
                'matches': {
                    'tech': job.tech_matches or []
                }
            }
        finally:
            session.close()
        
        # Generate cover letter using GPT-4
        logger.info(f"Generating cover letter for job {job_id}: {job_data['company']} - {job_data['title']}")
        cover_letter_text = generate_gpt4_cover_letter(job_data, score_data)
        
        # Save cover letter to applications directory
        applications_dir = os.path.join(os.path.dirname(__file__), 'applications')
        os.makedirs(applications_dir, exist_ok=True)
        
        # Create filename using timestamp and job identifier
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_company = job_data['company'].replace(' ', '-').replace('/', '-')[:50]
        safe_title = job_data['title'].replace(' ', '-').replace('/', '-')[:50]
        identifier = f"{timestamp}_{job_data['id']}_{safe_company}_{safe_title}"
        
        cover_letter_file = os.path.join(applications_dir, f"app_{identifier}_cover_letter.txt")
        metadata_file = os.path.join(applications_dir, f"app_{identifier}_metadata.json")
        
        # Save cover letter text
        with open(cover_letter_file, 'w') as f:
            f.write(cover_letter_text)
        
        # Save metadata for matching later
        metadata = {
            'job': job_data,
            'generated_at': datetime.now().isoformat(),
            'type': 'cover_letter'
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved cover letter to {cover_letter_file}")
        
        return jsonify({
            'success': True,
            'cover_letter': cover_letter_text,
            'filename': os.path.basename(cover_letter_file),
            'message': 'Cover letter generated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error generating cover letter: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cover_letter/save/<int:job_id>', methods=['POST'])
def save_cover_letter(job_id):
    """Save edited cover letter text"""
    try:
        data = request.get_json()
        if not data or 'cover_letter' not in data:
            return jsonify({'success': False, 'error': 'No cover letter text provided'}), 400
        
        cover_letter_text = data['cover_letter']
        
        # Get job details from database
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
        
        # Find existing cover letter file or create new one
        applications_dir = os.path.join(os.path.dirname(__file__), 'applications')
        os.makedirs(applications_dir, exist_ok=True)
        
        # Look for existing cover letter file
        cover_letter_file = None
        for filename in os.listdir(applications_dir):
            if not filename.endswith('_metadata.json'):
                continue
            
            metadata_path = os.path.join(applications_dir, filename)
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
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
                    cover_letter_file = metadata_path.replace('_metadata.json', '_cover_letter.txt')
                    break
                    
            except Exception as e:
                logger.debug(f"Error reading metadata {filename}: {e}")
                continue
        
        # If no existing file, create new one
        if not cover_letter_file or not os.path.exists(cover_letter_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_company = company.replace(' ', '-').replace('/', '-')[:50]
            safe_title = title.replace(' ', '-').replace('/', '-')[:50]
            identifier = f"{timestamp}_{source_id or job_id}_{safe_company}_{safe_title}"
            
            cover_letter_file = os.path.join(applications_dir, f"app_{identifier}_cover_letter.txt")
            metadata_file = os.path.join(applications_dir, f"app_{identifier}_metadata.json")
            
            # Save metadata
            metadata = {
                'job': {
                    'id': source_id,
                    'company': company,
                    'title': title
                },
                'saved_at': datetime.now().isoformat(),
                'type': 'cover_letter'
            }
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        # Save the cover letter text
        with open(cover_letter_file, 'w') as f:
            f.write(cover_letter_text)
        
        logger.info(f"Saved edited cover letter to {cover_letter_file}")
        
        return jsonify({
            'success': True,
            'message': 'Cover letter saved successfully',
            'filename': os.path.basename(cover_letter_file)
        })
        
    except Exception as e:
        logger.error(f"Error saving cover letter: {e}")
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


@app.route('/api/update_locations', methods=['POST'])
def update_locations():
    """Update scraping locations"""
    try:
        data = request.get_json(silent=True) or {}
        locations = data.get('locations', [])
        
        # Store locations in a config file
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'locations.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(locations, f, indent=2)
        
        return jsonify({'success': True, 'message': 'Locations updated'})
    except Exception as e:
        logger.error(f"Error updating locations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_locations', methods=['GET'])
def get_locations():
    """Get current scraping locations"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'locations.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                locations = json.load(f)
        else:
            # Return default locations
            locations = [
                {'name': 'New York, NY', 'country': 'US', 'enabled': True},
                {'name': 'Los Angeles, CA', 'country': 'US', 'enabled': True},
                {'name': 'San Francisco, CA', 'country': 'US', 'enabled': True},
                {'name': 'Seattle, WA', 'country': 'US', 'enabled': True},
                {'name': 'Austin, TX', 'country': 'US', 'enabled': True},
                {'name': 'Boston, MA', 'country': 'US', 'enabled': True},
                {'name': 'Remote', 'country': 'US', 'enabled': True},
                {'name': 'Melbourne VIC', 'country': 'AU', 'enabled': False},
                {'name': 'Sydney NSW', 'country': 'AU', 'enabled': False},
                {'name': 'Brisbane QLD', 'country': 'AU', 'enabled': False}
            ]
        
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
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'auto_submit.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Auto-submit settings updated: {data}")
        return jsonify({'success': True, 'message': 'Auto-submit settings updated'})
    except Exception as e:
        logger.error(f"Error updating auto-submit settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_auto_submit', methods=['GET'])
def get_auto_submit():
    """Get current auto-submit settings"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'auto_submit.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                settings = json.load(f)
        else:
            # Return default settings
            settings = {
                'enabled': False,
                'reviewMode': True,
                'platforms': {
                    'greenhouse': True,
                    'lever': True,
                    'email': True,
                    'workday': False
                }
            }
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error getting auto-submit settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/prepare_application/<int:job_id>', methods=['POST'])
def prepare_application(job_id):
    """
    Prepare application for review before auto-submit
    1. Generate cover letter if needed
    2. Generate PDF
    3. Return PDF path for user review
    """
    try:
        session = db.get_session()
        try:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            # Prepare job and score data
            job_data = {
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'url': job.url
            }
            
            score_data = {
                'fit_score': float(job.fit_score) if job.fit_score else 0.0,
                'reasoning': job.reasoning,
                'matches': {
                    'tech': job.tech_matches.split(',') if job.tech_matches else []
                }
            }
        finally:
            session.close()
        
        # Check if cover letter already exists
        applications_dir = os.path.join(os.path.dirname(__file__), 'applications')
        os.makedirs(applications_dir, exist_ok=True)
        
        # Find existing cover letter or generate new one
        cover_letter_text = None
        cover_letter_files = []
        
        for filename in os.listdir(applications_dir):
            if filename.endswith('_cover_letter.txt') and str(job_id) in filename:
                cover_letter_files.append(filename)
        
        if cover_letter_files:
            # Use most recent cover letter
            cover_letter_files.sort(reverse=True)
            cover_letter_path = os.path.join(applications_dir, cover_letter_files[0])
            with open(cover_letter_path, 'r') as f:
                cover_letter_text = f.read()
            logger.info(f"Found existing cover letter: {cover_letter_files[0]}")
        else:
            # Generate new cover letter
            logger.info(f"Generating new cover letter for job {job_id}")
            from src.applying.gpt4_cover_letter import generate_gpt4_cover_letter
            
            cover_letter_text = generate_gpt4_cover_letter(job_data, score_data)
            
            # Save the generated cover letter
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            cover_letter_filename = f"app_{timestamp}_{job_id}_cover_letter.txt"
            cover_letter_path = os.path.join(applications_dir, cover_letter_filename)
            
            with open(cover_letter_path, 'w') as f:
                f.write(cover_letter_text)
            
            logger.info(f"Saved cover letter: {cover_letter_filename}")
        
        # Generate PDF
        from src.applying.cover_letter_pdf import CoverLetterPDFGenerator
        
        pdf_generator = CoverLetterPDFGenerator()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"app_{timestamp}_{job_id}_cover_letter.pdf"
        pdf_path = os.path.join(applications_dir, pdf_filename)
        
        pdf_generator.generate_pdf(
            cover_letter_text=cover_letter_text,
            company_name=job.company,
            job_title=job.title,
            output_path=pdf_path
        )
        
        logger.info(f"Generated PDF: {pdf_filename}")
        
        return jsonify({
            'success': True,
            'cover_letter': cover_letter_text,
            'pdf_filename': pdf_filename,
            'job': {
                'id': job_id,
                'title': job.title,
                'company': job.company
            }
        })
        
    except Exception as e:
        logger.error(f"Error preparing application: {e}")
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
    mode = request.args.get('mode', 'tech')  # 'tech' or 'goldcoast'
    
    if mode == 'goldcoast':
        # Run Gold Coast scraper
        started = _start_goldcoast_scrape()
    else:
        # Run regular tech job scraper
        started = _start_scrape_job()
    
    if not started:
        return jsonify({'success': False, 'error': 'Scrape already running'}), 409
    return jsonify({'success': True, 'message': f'{mode.title()} scrape started'}), 202


def _start_goldcoast_scrape():
    """Start Gold Coast job scraping in background thread"""
    global scrape_running
    
    if scrape_running:
        return False
    
    def scrape_goldcoast_jobs():
        global scrape_running
        scrape_running = True
        
        try:
            logger.info("Starting Gold Coast job scrape...")
            
            # Expanded Gold Coast lifestyle job search terms
            gold_coast_terms = [
                # Wellness & Retreats
                'wellness retreat',
                'spa therapist',
                'yoga instructor',
                'massage therapist',
                'wellness coordinator',
                'retreat coordinator',
                # Fitness & Sport
                'personal trainer',
                'fitness instructor',
                'pilates instructor',
                'tennis coach',
                'gym instructor',
                'hiking guide',
                'surf instructor',
                'sports coach',
                'recreation officer',
                # Boutique Hospitality
                'boutique hotel',
                'concierge casual',
                'guest services',
                'hotel casual',
                'reception casual',
                # Food & Beverage
                'barista casual',
                'cafe casual',
                'bartender casual',
                'waiter casual',
                'kitchen hand',
                # Lifestyle & Creative
                'gallery assistant',
                'events casual',
                'tourism casual',
                'outdoor guide',
                'beach club'
            ]
            
            # Expanded Gold Coast region locations (from Byron Bay down to Gold Coast)
            gold_coast_locations = [
                # Northern NSW (Byron area)
                "Byron Bay NSW",
                "Brunswick Heads NSW",
                "Suffolk Park NSW",
                "Bangalow NSW",
                # Northern Gold Coast
                "Tweed Heads NSW",
                "Kingscliff NSW",
                "Cabarita Beach NSW",
                # Gold Coast Hinterland
                "Tamborine Mountain QLD",
                "Mount Tamborine QLD",
                # Gold Coast Main Areas
                "Gold Coast QLD",
                "Burleigh Heads QLD",
                "Mermaid Beach QLD",
                "Broadbeach QLD",
                "Currumbin QLD",
                "Palm Beach QLD",
                "Coolangatta QLD"
            ]
            
            # Use existing SeekScraper with expanded terms and locations
            all_jobs = []
            
            # Search more locations with more terms (10 terms per location)
            for location in gold_coast_locations[:8]:  # Focus on top 8 locations
                logger.info(f"Searching {location}...")
                jobs = seek_scraper.search_jobs(gold_coast_terms[:10], location=location)
                all_jobs.extend(jobs)
                
                # Get more jobs - aim for 100-150 total
                if len(all_jobs) >= 150:
                    break
            
            jobs = all_jobs[:150]  # Limit to 150 total
            
            session = db.get_session()
            new_jobs_count = 0
            
            for job_data in jobs:
                try:
                    # Check if job already exists
                    existing = session.query(Job).filter(Job.url == job_data['url']).first()
                    if existing:
                        continue
                    
                    # Fetch full description for new jobs only (more efficient)
                    logger.debug(f"Fetching full description for: {job_data['title']}")
                    full_description = seek_scraper.fetch_single_job_description(job_data['url'])
                    
                    # Use full description if fetched, otherwise use snippet
                    description = full_description if full_description and len(full_description) > 100 else job_data['description']
                    
                    # Score the job with Gold Coast scorer using full description
                    result = goldcoast_scorer.score_job({
                        'title': job_data['title'],
                        'company': job_data['company'],
                        'description': description,
                        'location': job_data['location']
                    })
                    
                    # Create job entry
                    new_job = Job(
                        title=job_data['title'],
                        company=job_data['company'],
                        location=job_data['location'],
                        description=description,  # Use full description
                        url=job_data['url'],
                        source='seek_goldcoast',
                        source_id=job_data.get('source_id', job_data['url']),
                        fit_score=result['fit_score'],
                        reasoning=result['reasoning'],
                        remote=False,
                        applied=False
                    )
                    
                    session.add(new_job)
                    new_jobs_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing Gold Coast job: {e}")
                    continue
            
            session.commit()
            session.close()
            
            logger.info(f"Gold Coast scrape complete: {new_jobs_count} new jobs added")
            
        except Exception as e:
            logger.error(f"Gold Coast scrape failed: {e}")
        finally:
            scrape_running = False
    
    thread = threading.Thread(target=scrape_goldcoast_jobs, daemon=True)
    thread.start()
    return True


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
