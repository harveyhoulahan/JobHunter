"""
Test suite for JobHunter
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scoring.engine import JobScorer
from database.models import Database
from profile import HARVEY_PROFILE


class TestJobScorer:
    """Test the job scoring engine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scorer = JobScorer()
    
    def test_perfect_ml_job(self):
        """Test scoring for perfect ML job match"""
        job = {
            'title': 'Machine Learning Engineer',
            'company': 'AI Startup',
            'description': '''
                Looking for an ML Engineer with Python, AWS, and LLM experience.
                Build NLP systems for our fashion tech platform. We offer E-3 visa sponsorship.
                2-3 years experience required.
            ''',
            'location': 'New York, NY'
        }
        
        result = self.scorer.score_job(job)
        
        assert result['fit_score'] >= 80, "Should score highly for perfect match"
        assert 'python' in [m.lower() for m in result['matches']['tech']]
        assert result['visa_status'] == 'explicit'
        assert result['location_ok'] == True
    
    def test_senior_role_penalty(self):
        """Test that senior roles get penalized"""
        job = {
            'title': 'Senior Machine Learning Engineer',
            'company': 'AI Startup',
            'description': 'Senior ML role requiring 10+ years experience. Python, AWS, NLP.',
            'location': 'New York, NY'
        }
        
        result = self.scorer.score_job(job)
        
        assert result['seniority_ok'] == False, "Should detect senior role"
        # Score should be reduced
    
    def test_no_visa_sponsorship(self):
        """Test job with no visa sponsorship"""
        job = {
            'title': 'Machine Learning Engineer',
            'company': 'Startup',
            'description': '''
                ML Engineer needed. Python, ML frameworks.
                Must be authorized to work in US. No sponsorship available.
            ''',
            'location': 'New York, NY'
        }
        
        result = self.scorer.score_job(job)
        
        assert result['visa_status'] == 'excluded', "Should detect no sponsorship"
        assert result['fit_score'] < 50, "Should score low without sponsorship"
    
    def test_poor_location(self):
        """Test job in wrong location"""
        job = {
            'title': 'Machine Learning Engineer',
            'company': 'Company',
            'description': 'Python, ML, AWS',
            'location': 'San Francisco, CA'
        }
        
        result = self.scorer.score_job(job)
        
        assert result['location_ok'] == False, "Should detect wrong location"
    
    def test_remote_job(self):
        """Test remote job acceptance"""
        job = {
            'title': 'ML Engineer',
            'company': 'Remote Co',
            'description': 'Python ML engineer',
            'location': 'Remote'
        }
        
        result = self.scorer.score_job(job)
        
        assert result['location_ok'] == True, "Should accept remote jobs"


class TestDatabase:
    """Test database operations"""
    
    def setup_method(self):
        """Set up test database"""
        self.db = Database('sqlite:///:memory:')  # In-memory database
        self.db.create_tables()
    
    def test_add_job(self):
        """Test adding a job to database"""
        job_data = {
            'title': 'Test Engineer',
            'company': 'Test Co',
            'url': 'https://example.com/job1',
            'description': 'Test description',
            'source': 'test',
            'fit_score': 75.0
        }
        
        job = self.db.add_job(job_data)
        
        assert job.id is not None
        assert job.title == 'Test Engineer'
        assert job.fit_score == 75.0
    
    def test_duplicate_detection(self):
        """Test duplicate job detection"""
        job_data = {
            'title': 'Engineer',
            'company': 'Co',
            'url': 'https://example.com/job2',
            'description': 'Desc',
            'source': 'test',
            'fit_score': 50.0
        }
        
        # Add first time
        self.db.add_job(job_data)
        
        # Check if exists
        exists = self.db.job_exists('https://example.com/job2')
        assert exists == True
        
        # Different URL should not exist
        exists = self.db.job_exists('https://example.com/different')
        assert exists == False
    
    def test_get_jobs_to_alert(self):
        """Test getting jobs above threshold"""
        # Add jobs with different scores
        for score in [45, 55, 75, 85, 95]:
            self.db.add_job({
                'title': f'Job {score}',
                'company': 'Co',
                'url': f'https://example.com/job{score}',
                'description': 'Desc',
                'source': 'test',
                'fit_score': float(score)
            })
        
        # Get high-scoring jobs (>= 70)
        high_jobs = self.db.get_jobs_to_alert(threshold=70.0)
        
        assert len(high_jobs) == 3  # 75, 85, 95
        assert all(j.fit_score >= 70 for j in high_jobs)


class TestProfile:
    """Test Harvey's profile data"""
    
    def test_profile_has_skills(self):
        """Test that profile contains skills"""
        assert 'skills' in HARVEY_PROFILE
        assert len(HARVEY_PROFILE['skills']) > 0
    
    def test_profile_has_industries(self):
        """Test that profile contains industries"""
        assert 'industries' in HARVEY_PROFILE
        assert 'Fashion Tech' in HARVEY_PROFILE['industries']
        assert 'AI/ML' in HARVEY_PROFILE['industries']
    
    def test_profile_has_visa_requirements(self):
        """Test visa requirements"""
        assert 'visa' in HARVEY_PROFILE
        assert HARVEY_PROFILE['visa']['required'] == True
        assert HARVEY_PROFILE['visa']['type'] == 'E-3'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
