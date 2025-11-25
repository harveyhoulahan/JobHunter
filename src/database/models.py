"""
Database models and schema for JobHunter
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()


class Job(Base):
    """Job listing model"""
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    
    # Basic info
    title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=False)
    url = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    posted_date = Column(String(50))
    
    # Source tracking
    source = Column(String(50), nullable=False)  # linkedin, indeed, etc.
    source_id = Column(String(255))  # Original ID from source
    
    # Scoring
    fit_score = Column(Float, default=0.0)
    reasoning = Column(Text)
    
    # Match details (stored as JSON)
    tech_matches = Column(JSON)  # ["Python", "AWS", "ML"]
    industry_matches = Column(JSON)  # ["AI/ML", "Fashion Tech"]
    role_matches = Column(JSON)  # ["ML Engineer"]
    
    # Visa information
    visa_status = Column(String(50))  # "explicit", "possible", "none", "excluded"
    visa_keywords_found = Column(JSON)  # ["E-3", "sponsorship available"]
    
    # Location
    location = Column(String(255))
    remote = Column(Boolean, default=False)
    
    # User actions
    clicked = Column(Boolean, default=False)
    applied = Column(Boolean, default=False)
    rejected = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    alerted_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}', score={self.fit_score})>"


class SearchHistory(Base):
    """Track search runs"""
    __tablename__ = 'search_history'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50), nullable=False)
    
    # Results
    jobs_found = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    jobs_duplicate = Column(Integer, default=0)
    
    # Performance
    duration_seconds = Column(Float)
    errors = Column(Text)
    success = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<SearchHistory(source='{self.source}', found={self.jobs_found}, new={self.jobs_new})>"


class Alert(Base):
    """Track sent alerts"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, nullable=False)
    
    # Alert details
    alert_type = Column(String(20))  # "immediate", "digest"
    channel = Column(String(20))  # "email", "sms"
    recipient = Column(String(255))
    
    # Status
    sent_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<Alert(job_id={self.job_id}, type='{self.alert_type}', channel='{self.channel}')>"


class Database:
    """Database manager"""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            # Default to SQLite in data directory
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'jobhunter.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            database_url = f'sqlite:///{db_path}'
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self.engine)
        
    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()
    
    def job_exists(self, url: str = None, source_id: str = None) -> bool:
        """
        Check if job already exists by URL or source_id
        Prioritizes source_id for better deduplication (avoids URL param differences)
        """
        session = self.get_session()
        try:
            if source_id:
                # Check by source_id first (more reliable for LinkedIn etc.)
                return session.query(Job).filter_by(source_id=source_id).first() is not None
            elif url:
                # Fallback to URL check
                # Clean URL of query parameters for better matching
                base_url = url.split('?')[0]
                existing = session.query(Job).filter(Job.url.like(f"{base_url}%")).first()
                return existing is not None
            return False
        finally:
            session.close()
    
    def add_job(self, job_data: dict) -> Job:
        """Add a new job listing"""
        session = self.get_session()
        try:
            job = Job(**job_data)
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_jobs_to_alert(self, threshold: float = 70.0, alerted: bool = False):
        """Get jobs that meet alert threshold and haven't been alerted"""
        session = self.get_session()
        try:
            query = session.query(Job).filter(Job.fit_score >= threshold)
            if not alerted:
                query = query.filter(Job.alerted_at.is_(None))
            return query.order_by(Job.fit_score.desc()).all()
        finally:
            session.close()
    
    def mark_alerted(self, job_id: int):
        """Mark job as alerted"""
        session = self.get_session()
        try:
            job = session.query(Job).filter_by(id=job_id).first()
            if job:
                job.alerted_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    
    def add_search_history(self, history_data: dict) -> SearchHistory:
        """Log a search run"""
        session = self.get_session()
        try:
            history = SearchHistory(**history_data)
            session.add(history)
            session.commit()
            return history
        finally:
            session.close()
    
    def add_alert(self, alert_data: dict) -> Alert:
        """Log an alert"""
        session = self.get_session()
        try:
            alert = Alert(**alert_data)
            session.add(alert)
            session.commit()
            return alert
        finally:
            session.close()


# Initialize database
def init_db(database_url: str = None):
    """Initialize the database"""
    db = Database(database_url)
    db.create_tables()
    return db


if __name__ == "__main__":
    # Test database creation
    db = init_db()
    print("Database initialized successfully!")
