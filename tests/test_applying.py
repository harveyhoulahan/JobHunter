"""
Test suite for the AI Automated Applying Module
"""
import pytest
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from applying.cv_generator import CVGenerator
from applying.applicator import JobApplicator
from scoring.engine import JobScorer


class TestCVGenerator:
    """Test the CV generator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = CVGenerator()
    
    def test_initialization(self):
        """Test CV generator initializes correctly"""
        assert self.generator is not None
        summary = self.generator.get_resume_summary()
        assert 'profile_skills_count' in summary
        assert summary['profile_skills_count'] > 0
    
    def test_generate_customized_cv(self):
        """Test generating a customized CV"""
        job = {
            'title': 'Machine Learning Engineer',
            'company': 'AI Startup',
            'description': '''
                Looking for an ML Engineer with Python, AWS, and LLM experience.
                Build NLP systems. 2-3 years experience required.
            ''',
            'location': 'New York, NY'
        }
        
        score_result = {
            'fit_score': 85,
            'matches': {
                'tech': ['Python', 'AWS', 'ML', 'NLP', 'LLM'],
                'industry': ['AI/ML', 'Tech'],
                'role': ['ML Engineer']
            }
        }
        
        result = self.generator.generate_customized_cv(job, score_result)
        
        assert 'content' in result
        assert 'highlights' in result
        assert 'customized_for' in result
        assert result['customized_for']['job_title'] == 'Machine Learning Engineer'
        assert result['customized_for']['company'] == 'AI Startup'
        assert len(result['content']) > 500  # Should have substantial content
    
    def test_cv_contains_key_sections(self):
        """Test that generated CV contains key sections"""
        job = {
            'title': 'Backend Engineer',
            'company': 'Tech Co',
            'description': 'Python, SQL, AWS backend engineer needed.',
            'location': 'NYC'
        }
        
        score_result = {
            'fit_score': 75,
            'matches': {
                'tech': ['Python', 'SQL', 'AWS'],
                'industry': ['Tech'],
                'role': ['Backend Engineer']
            }
        }
        
        result = self.generator.generate_customized_cv(job, score_result)
        content = result['content']
        
        # Check for key sections
        assert 'HARVEY J. HOULAHAN' in content
        assert 'PROFESSIONAL SUMMARY' in content
        assert 'TECHNICAL SKILLS' in content
        assert 'PROFESSIONAL EXPERIENCE' in content
        assert 'EDUCATION' in content
    
    def test_cv_highlights_relevant_skills(self):
        """Test that CV highlights skills matched to job"""
        job = {
            'title': 'iOS Engineer',
            'company': 'Mobile Startup',
            'description': 'Swift, SwiftUI, iOS development. CoreML experience a plus.',
            'location': 'Remote'
        }
        
        score_result = {
            'fit_score': 80,
            'matches': {
                'tech': ['Swift', 'SwiftUI', 'iOS', 'CoreML'],
                'industry': ['Mobile', 'Consumer Apps'],
                'role': ['iOS Engineer']
            }
        }
        
        result = self.generator.generate_customized_cv(job, score_result)
        
        # Check that matched skills appear in highlights
        highlights = result['highlights']
        assert 'skills' in highlights
        assert len(highlights['skills']) > 0


class TestJobApplicator:
    """Test the job applicator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.applicator = JobApplicator(min_fit_score=50.0)
        self.scorer = JobScorer()
    
    def test_should_apply_good_job(self):
        """Test that we should apply to a good job"""
        job = {
            'title': 'Machine Learning Engineer',
            'company': 'AI Startup',
            'description': '''
                Looking for an ML Engineer with Python, AWS, and NLP experience.
                Build AI systems. E-3 visa sponsorship available.
                2-3 years experience required.
            ''',
            'location': 'New York, NY'
        }
        
        score_result = self.scorer.score_job(job)
        
        # Good job should be eligible
        should_apply = self.applicator.should_apply(job, score_result)
        assert score_result['fit_score'] >= 50
        assert should_apply
    
    def test_should_not_apply_senior_job(self):
        """Test that we should NOT apply to senior jobs"""
        job = {
            'title': 'Senior Staff ML Engineer',
            'company': 'BigTech',
            'description': '''
                10+ years experience required. Lead a team of engineers.
                Senior leadership role. Python, ML, AWS.
            ''',
            'location': 'New York, NY'
        }
        
        score_result = self.scorer.score_job(job)
        
        # Senior job should be rejected
        should_apply = self.applicator.should_apply(job, score_result)
        assert not should_apply
    
    def test_should_not_apply_no_sponsorship(self):
        """Test that we should NOT apply to jobs without sponsorship"""
        job = {
            'title': 'ML Engineer',
            'company': 'Startup',
            'description': '''
                ML Engineer needed. Python, ML, AWS.
                Must be authorized to work in US. No sponsorship available.
            ''',
            'location': 'New York, NY'
        }
        
        score_result = self.scorer.score_job(job)
        
        # No sponsorship should be rejected
        should_apply = self.applicator.should_apply(job, score_result)
        assert not should_apply
    
    def test_should_not_apply_low_score(self):
        """Test that we should NOT apply to low-scoring jobs"""
        job = {
            'title': 'Accountant',
            'company': 'Finance Co',
            'description': '''
                CPA required. 5 years accounting experience.
                Excel, QuickBooks. No tech background needed.
            ''',
            'location': 'New York, NY'
        }
        
        score_result = self.scorer.score_job(job)
        
        # Low score job should be rejected
        should_apply = self.applicator.should_apply(job, score_result)
        assert score_result['fit_score'] < 50
        assert not should_apply
    
    def test_prepare_application(self):
        """Test preparing an application"""
        job = {
            'title': 'ML Engineer',
            'company': 'AI Co',
            'url': 'https://example.com/job/ml',
            'description': '''
                Python, ML, AWS engineer. E-3 sponsorship available.
                2-3 years experience.
            ''',
            'location': 'NYC',
            'source': 'linkedin'
        }
        
        score_result = self.scorer.score_job(job)
        
        # Only proceed if score is high enough
        if score_result['fit_score'] >= 50:
            application = self.applicator.prepare_application(job, score_result)
            
            assert application is not None
            assert 'id' in application
            assert 'job' in application
            assert 'cv' in application
            assert 'cover_letter' in application
            assert application['status'] == 'prepared'
            assert application['job']['title'] == 'ML Engineer'
    
    def test_cover_letter_generation(self):
        """Test that cover letter is generated correctly"""
        job = {
            'title': 'ML Engineer',
            'company': 'FashionTech Inc',
            'url': 'https://example.com/job',
            'description': 'Python ML engineer for fashion tech platform.',
            'location': 'NYC',
            'source': 'linkedin'
        }
        
        score_result = {
            'fit_score': 80,
            'matches': {
                'tech': ['Python', 'ML'],
                'industry': ['Fashion Tech'],
                'role': ['ML Engineer']
            },
            'visa_status': 'none',
            'seniority_ok': True,
            'location_ok': True
        }
        
        application = self.applicator.prepare_application(job, score_result)
        
        if application:
            cover_letter = application['cover_letter']
            
            # Cover letter should mention key elements
            assert 'Harvey' in cover_letter or 'Houlahan' in cover_letter
            assert 'FashionTech Inc' in cover_letter
            assert 'ML Engineer' in cover_letter
    
    def test_application_stats(self):
        """Test getting application statistics"""
        stats = self.applicator.get_application_stats()
        
        assert 'pending' in stats
        assert 'completed' in stats
        assert 'total' in stats
        assert 'output_directory' in stats


class TestIntegration:
    """Integration tests for the full application flow"""
    
    def test_full_application_flow(self):
        """Test the complete flow from job to application"""
        scorer = JobScorer()
        applicator = JobApplicator(min_fit_score=50.0)
        
        # Good job that should result in application
        job = {
            'title': 'Machine Learning Engineer',
            'company': 'AI Startup',
            'url': 'https://example.com/job/ml-engineer',
            'description': '''
                We're looking for an ML Engineer with Python, AWS, and NLP experience.
                Build AI-powered features. E-3 visa sponsorship available.
                2-3 years experience required. Fashion tech focus.
            ''',
            'location': 'New York, NY',
            'source': 'linkedin',
            'source_id': 'test-123'
        }
        
        # Score the job
        score_result = scorer.score_job(job)
        
        # Check if we should apply
        should_apply = applicator.should_apply(job, score_result)
        
        if should_apply:
            # Prepare application
            application = applicator.prepare_application(job, score_result)
            
            assert application is not None
            assert application['job']['company'] == 'AI Startup'
            assert len(application['cv']['content']) > 0
            assert len(application['cover_letter']) > 0
            
            # Check that pending applications increased
            pending = applicator.get_pending_applications()
            assert len(pending) > 0
    
    def test_batch_processing(self):
        """Test processing multiple jobs"""
        scorer = JobScorer()
        applicator = JobApplicator(min_fit_score=50.0)
        
        jobs = [
            {
                'title': 'ML Engineer',
                'company': 'Company A',
                'url': 'https://example.com/job/a',
                'description': 'Python ML AWS E-3 sponsorship. 2-3 years.',
                'location': 'NYC',
                'source': 'linkedin'
            },
            {
                'title': 'Senior Director',
                'company': 'Company B',
                'url': 'https://example.com/job/b',
                'description': '15+ years experience. VP level. No sponsorship.',
                'location': 'SF',
                'source': 'linkedin'
            },
            {
                'title': 'Backend Engineer',
                'company': 'Company C',
                'url': 'https://example.com/job/c',
                'description': 'Python SQL AWS. 3 years experience.',
                'location': 'Remote',
                'source': 'linkedin'
            }
        ]
        
        # Score all jobs
        score_results = {}
        for job in jobs:
            score_results[job['url']] = scorer.score_job(job)
        
        # Process batch
        stats = applicator.process_jobs(jobs, score_results)
        
        assert stats['total_jobs'] == 3
        # At least some should be skipped (senior job, no sponsorship)
        assert stats['skipped_seniority'] > 0 or stats['skipped_visa'] > 0 or stats['skipped_low_score'] > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
