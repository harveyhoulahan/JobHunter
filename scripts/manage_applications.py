#!/usr/bin/env python3
"""
Application Management Helper
Use this to track your job applications
"""
from src.database.models import Database
from datetime import datetime

db = Database()

def mark_as_applied(job_id: int, cv_version: str, application_method: str = "linkedin"):
    """
    Mark a job as applied
    
    Example:
        mark_as_applied(123, "ML_Engineer_v2.pdf", "linkedin")
    """
    db.mark_applied(
        job_id=job_id,
        cv_version=cv_version,
        cover_letter_version=f"cover_letter_{cv_version}",
        application_method=application_method,
        notes=f"Applied on {datetime.now().strftime('%Y-%m-%d')}"
    )
    print(f"✓ Marked job {job_id} as applied with CV: {cv_version}")


def update_status(job_id: int, status: str, notes: str = None):
    """
    Update job status
    
    Valid statuses: new, applied, phone_screen, interview, offer, rejected, withdrawn
    
    Example:
        update_status(123, "phone_screen", "Scheduled for next Tuesday")
    """
    db.update_job_status(job_id, status, notes)
    print(f"✓ Updated job {job_id} to status: {status}")


def add_interview(job_id: int, interview_type: str, notes: str = None):
    """
    Add interview round
    
    Example:
        add_interview(123, "technical", "Went well, discussed ML architecture")
    """
    db.add_interview_round(job_id, interview_type, notes=notes)
    print(f"✓ Added {interview_type} interview for job {job_id}")


def get_stats():
    """Get application statistics"""
    stats = db.get_application_stats()
    
    print("\n" + "=" * 60)
    print("APPLICATION STATISTICS")
    print("=" * 60)
    print(f"Total jobs in database: {stats['total_jobs']}")
    print(f"Applications sent:      {stats['applied']}")
    print(f"Phone screens:          {stats['phone_screens']}")
    print(f"Interviews:             {stats['interviews']}")
    print(f"Offers:                 {stats['offers']}")
    print(f"Rejections:             {stats['rejected']}")
    print(f"Response rate:          {stats['response_rate']:.1f}%")
    print("=" * 60 + "\n")


def view_top_jobs(limit: int = 10):
    """View top-scoring jobs"""
    session = db.get_session()
    try:
        from src.database.models import Job
        jobs = session.query(Job).order_by(Job.fit_score.desc()).limit(limit).all()
        
        print(f"\n🎯 Top {limit} Jobs:")
        print("=" * 90)
        for i, job in enumerate(jobs, 1):
            status_emoji = {
                'new': '🆕',
                'applied': '📤',
                'phone_screen': '📞',
                'interview': '🎤',
                'offer': '🎉',
                'rejected': '❌',
                'withdrawn': '🚫'
            }.get(job.status or 'new', '🆕')
            
            print(f"{i}. [{job.fit_score:.1f}] {status_emoji} {job.title}")
            print(f"   {job.company} - {job.location or 'Remote'}")
            print(f"   ID: {job.id}")  # Show job ID for marking as applied
            if job.cv_version:
                print(f"   📄 Applied with: {job.cv_version}")
            print(f"   🔗 {job.url}")
            print()
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("JobHunter Application Manager")
    print("=" * 60)
    
    # Show available commands
    print("\nAvailable commands:")
    print("  get_stats()                      - View application statistics")
    print("  view_top_jobs(10)                - View top 10 jobs")
    print("  mark_as_applied(job_id, 'cv.pdf') - Mark job as applied")
    print("  update_status(job_id, 'interview') - Update job status")
    print("  add_interview(job_id, 'technical') - Log interview")
    print("\nExample usage:")
    print("  python3 -i manage_applications.py")
    print("  >>> get_stats()")
    print("  >>> view_top_jobs(5)")
    print("  >>> mark_as_applied(123, 'ML_Engineer_Resume_v3.pdf')")
    print()
    
    # Show current stats
    get_stats()
    view_top_jobs(5)
