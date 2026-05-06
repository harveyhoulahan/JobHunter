#!/usr/bin/env python3
"""
Test Auto-Submit with a Greenhouse Job
Tests the full workflow: detect platform → auto-fill → pause for review
"""

from src.applying.auto_submit import AutoSubmitManager
import os

# Create a test job (Greenhouse format)
test_greenhouse_job = {
    'title': 'Machine Learning Engineer',
    'company': 'Stripe',
    'url': 'https://boards.greenhouse.io/stripe/jobs/123456',  # Example Greenhouse URL
    'description': '''
    We're looking for an ML Engineer with Python, AWS, and production ML experience.
    You'll build AI-powered payment fraud detection systems.
    
    Requirements:
    - 2+ years Python experience
    - ML/AI production experience
    - AWS or cloud platform experience
    ''',
    'location': 'San Francisco, CA',
    'source': 'greenhouse',
    'source_id': '123456'
}

# Create a test job (Lever format)
test_lever_job = {
    'title': 'Senior Backend Engineer',
    'company': 'Netflix',
    'url': 'https://jobs.lever.co/netflix/abc123',  # Example Lever URL
    'description': '''
    Join Netflix's streaming infrastructure team.
    Build scalable microservices handling millions of requests.
    
    Requirements:
    - Python, Java, or Go
    - Distributed systems experience
    - Cloud infrastructure (AWS/GCP)
    ''',
    'location': 'Los Gatos, CA',
    'source': 'lever',
    'source_id': 'abc123'
}

# Create a test email application job
test_email_job = {
    'title': 'AI Researcher',
    'company': 'Small AI Startup',
    'url': 'https://example.com/job/ai-researcher',
    'description': '''
    We're a stealth AI startup looking for an AI researcher.
    
    To apply, please email your resume to: jobs@aistartp.com
    Include "AI Researcher Application" in the subject line.
    ''',
    'location': 'New York, NY',
    'source': 'email',
    'source_id': 'email-001'
}

def test_platform_detection():
    """Test that AutoSubmitManager correctly detects job platforms"""
    print("\n" + "=" * 80)
    print("TEST 1: Platform Detection")
    print("=" * 80)
    
    submitter = AutoSubmitManager(review_mode=True)
    
    # Test Greenhouse detection
    result = submitter.submit_application(
        test_greenhouse_job,
        resume_path='applications/test_resume.pdf',  # Would need to exist
        cover_letter_path='applications/test_cover_letter.pdf'
    )
    print(f"\n✓ Greenhouse job detected: {result.get('method')}")
    print(f"  Status: {result.get('status')}")
    
    # Test Lever detection
    result = submitter.submit_application(
        test_lever_job,
        resume_path='applications/test_resume.pdf',
        cover_letter_path='applications/test_cover_letter.pdf'
    )
    print(f"\n✓ Lever job detected: {result.get('method')}")
    print(f"  Status: {result.get('status')}")
    
    # Test Email detection
    result = submitter.submit_application(
        test_email_job,
        resume_path='applications/test_resume.pdf',
        cover_letter_path='applications/test_cover_letter.pdf'
    )
    print(f"\n✓ Email job detected: {result.get('method')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message', result.get('error'))}")


def test_with_real_job():
    """Test with an actual job from database"""
    print("\n" + "=" * 80)
    print("TEST 2: Real Job from Database")
    print("=" * 80)
    
    from src.database.models import Database, Job
    db = Database()
    session = db.get_session()
    
    try:
        # Find a high-scoring BuiltIn job
        job = session.query(Job).filter(
            Job.source != 'linkedin',
            Job.fit_score >= 50,
            Job.applied == False
        ).order_by(Job.fit_score.desc()).first()
        
        if not job:
            print("⚠️  No suitable test jobs found in database")
            return
        
        print(f"\n📋 Testing with: {job.title}")
        print(f"   Company: {job.company}")
        print(f"   Source: {job.source}")
        print(f"   Score: {job.fit_score}%")
        print(f"   URL: {job.url}")
        
        # Check if we have a generated CV for this job
        import glob
        cv_files = glob.glob(f'applications/*{job.source_id}*.pdf')
        
        if not cv_files:
            print("\n⚠️  No CV found for this job. Need to generate one first.")
            print("   Run: python3 src/main.py (to generate CVs)")
            return
        
        cv_path = cv_files[0]
        print(f"\n✓ Found CV: {cv_path}")
        
        # Create job data dict
        job_data = {
            'title': job.title,
            'company': job.company,
            'url': job.url,
            'description': job.description,
            'location': job.location,
            'source': job.source,
            'source_id': job.source_id
        }
        
        # Test auto-submit
        print("\n🚀 Testing auto-submit...")
        submitter = AutoSubmitManager(review_mode=True)
        result = submitter.submit_application(job_data, cv_path)
        
        print(f"\n📊 Result:")
        print(f"   Method: {result.get('method')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Success: {result.get('success')}")
        if result.get('error'):
            print(f"   Error: {result.get('error')}")
        if result.get('message'):
            print(f"   Message: {result.get('message')}")
        
    finally:
        session.close()


def test_api_endpoint():
    """Test the /api/auto_submit endpoint"""
    print("\n" + "=" * 80)
    print("TEST 3: API Endpoint")
    print("=" * 80)
    
    import requests
    
    # Find a job ID
    from src.database.models import Database, Job
    db = Database()
    session = db.get_session()
    
    try:
        job = session.query(Job).filter(
            Job.source != 'linkedin',
            Job.fit_score >= 50,
            Job.applied == False
        ).first()
        
        if not job:
            print("⚠️  No test job found")
            return
        
        print(f"\n📋 Testing API with job: {job.title}")
        print(f"   Job ID: {job.id}")
        
        # Call API
        response = requests.post(
            'http://localhost:5002/api/auto_submit',
            json={'job_id': job.id}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ API Response:")
            print(f"   Success: {data.get('success')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Method: {data.get('method')}")
            if data.get('error'):
                print(f"   Error: {data.get('error')}")
        else:
            print(f"\n❌ API Error: {response.status_code}")
            print(f"   {response.text}")
    
    finally:
        session.close()


if __name__ == "__main__":
    print("\n" + "🧪 " * 20)
    print("AUTO-SUBMIT TESTING SUITE")
    print("🧪 " * 20)
    
    print("\n⚠️  NOTE: This will test auto-submit detection and routing.")
    print("   For actual form filling, you need real Greenhouse/Lever URLs.")
    print("   LinkedIn jobs are intentionally excluded (ToS compliance).")
    
    # Run tests
    test_platform_detection()
    test_with_real_job()
    test_api_endpoint()
    
    print("\n" + "=" * 80)
    print("✅ Testing Complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Visit http://localhost:5002 to see dashboard")
    print("2. Click green 'Auto-Submit' button on any non-LinkedIn job")
    print("3. Confirm the dialog to test the full workflow")
    print("4. For Greenhouse/Lever jobs, browser will open and auto-fill")
    print("5. Review the pre-filled form and submit manually")
