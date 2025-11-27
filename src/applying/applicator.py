"""
Automated Job Applicator

Handles automated job applications by:
1. Checking if job meets application criteria (>=50% fit score)
2. Generating customized CV for the job
3. Storing application records and generating application materials
"""

import hashlib
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from profile import HARVEY_PROFILE
from .cv_generator import CVGenerator
from .gpt4_cover_letter import GPT4CoverLetterGenerator


class JobApplicator:
    """
    Manages automated job applications
    
    This class handles:
    - Checking application eligibility based on fit score
    - Generating customized CVs for eligible jobs
    - Tracking application status
    - Storing application materials
    """
    
    # Minimum fit score to consider applying (50%)
    MIN_FIT_SCORE = 50.0
    
    # Application output directory
    OUTPUT_DIR = 'applications'
    
    def __init__(
        self,
        min_fit_score: float = None,
        output_dir: str = None,
        cv_generator: CVGenerator = None
    ):
        """
        Initialize the job applicator
        
        Args:
            min_fit_score: Minimum fit score to apply (default: 50%)
            output_dir: Directory to store application materials
            cv_generator: Optional CVGenerator instance (will create if not provided)
        """
        self.min_fit_score = min_fit_score or self.MIN_FIT_SCORE
        self.output_dir = output_dir or self.OUTPUT_DIR
        self.cv_generator = cv_generator or CVGenerator()
        
        # Create output directory
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.output_path = os.path.join(root_dir, self.output_dir)
        os.makedirs(self.output_path, exist_ok=True)
        
        # Track applications in memory
        self.pending_applications = []
        self.completed_applications = []
        
        logger.info(f"JobApplicator initialized with min score: {self.min_fit_score}")
        logger.info(f"Application materials will be stored in: {self.output_path}")
    
    def should_apply(self, job_data: Dict[str, Any], score_result: Dict[str, Any]) -> bool:
        """
        Determine if we should apply to this job
        
        Args:
            job_data: Job listing data
            score_result: Scoring result from JobScorer
            
        Returns:
            True if job meets application criteria
        """
        fit_score = score_result.get('fit_score', 0)
        
        # Check minimum score threshold
        if fit_score < self.min_fit_score:
            logger.debug(f"Job below threshold ({fit_score} < {self.min_fit_score}): {job_data.get('title')}")
            return False
        
        # Check visa status - don't apply if explicitly excluded
        visa_status = score_result.get('visa_status', 'none')
        if visa_status == 'excluded':
            logger.debug(f"Job excluded due to visa: {job_data.get('title')}")
            return False
        
        # Check seniority
        if not score_result.get('seniority_ok', True):
            logger.debug(f"Job too senior: {job_data.get('title')}")
            return False
        
        # Check location
        if not score_result.get('location_ok', True):
            # Allow if score is very high (>=70)
            if fit_score < 70:
                logger.debug(f"Job location not ideal and score not high enough: {job_data.get('title')}")
                return False
        
        return True
    
    def prepare_application(
        self,
        job_data: Dict[str, Any],
        score_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare application materials for a job
        
        Args:
            job_data: Job listing data
            score_result: Scoring result from JobScorer
            
        Returns:
            Application package with customized CV and metadata, or None if not eligible
        """
        if not self.should_apply(job_data, score_result):
            return None
        
        job_title = job_data.get('title', 'Unknown Position')
        company = job_data.get('company', 'Unknown Company')
        # Use stable hash for job ID (hashlib.md5 is deterministic unlike hash())
        url_hash = hashlib.md5(job_data.get('url', '').encode()).hexdigest()[:12]
        job_id = job_data.get('id') or job_data.get('source_id') or url_hash
        
        logger.info(f"Preparing application for: {job_title} at {company}")
        
        # Generate customized CV
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        safe_company = self._sanitize_filename(company)
        safe_title = self._sanitize_filename(job_title)
        
        cv_filename = f"CV_{safe_company}_{safe_title}_{timestamp}.pdf"
        cv_path = os.path.join(self.output_path, cv_filename)
        
        # Generate the customized CV
        cv_result = self.cv_generator.generate_customized_cv(
            job_data,
            score_result,
            output_path=cv_path
        )
        
        # Build application package
        application = {
            'id': f"app_{timestamp}_{job_id}",
            'job': {
                'id': job_id,
                'title': job_title,
                'company': company,
                'url': job_data.get('url'),
                'location': job_data.get('location'),
                'source': job_data.get('source')
            },
            'score': {
                'fit_score': score_result.get('fit_score'),
                'breakdown': score_result.get('breakdown'),
                'reasoning': score_result.get('reasoning')
            },
            'cv': {
                'content': cv_result.get('content'),
                'pdf_path': cv_result.get('pdf_path'),
                'highlights': cv_result.get('highlights')
            },
            'cover_letter': self._generate_cover_letter(job_data, score_result),
            'applicant': {
                'name': HARVEY_PROFILE.get('name', 'Harvey J. Houlahan'),
                'email': HARVEY_PROFILE.get('email', 'harveyhoulahan@outlook.com'),
                'linkedin': HARVEY_PROFILE.get('linkedin')
            },
            'status': 'prepared',
            'prepared_at': datetime.now(timezone.utc).isoformat(),
            'applied_at': None
        }
        
        # Store in pending applications
        self.pending_applications.append(application)
        
        # Save application metadata
        self._save_application_metadata(application)
        
        logger.info(f"Application prepared: {application['id']}")
        return application
    
    def _generate_cover_letter(
        self,
        job_data: Dict[str, Any],
        score_result: Dict[str, Any]
    ) -> str:
        """Generate a customized cover letter using GPT-4 (with template fallback)"""
        
        # Try GPT-4 generation first
        try:
            gpt4_generator = GPT4CoverLetterGenerator()
            cover_letter = gpt4_generator.generate_cover_letter(
                job_data=job_data,
                score_data=score_result
            )
            logger.info(f"✨ Generated GPT-4 cover letter for {job_data.get('company', 'Unknown')}")
            return cover_letter
        except Exception as e:
            logger.warning(f"GPT-4 generation failed ({str(e)}), using template fallback")
            # Fall back to template-based generation
            return self._generate_template_cover_letter(job_data, score_result)
    
    def _generate_template_cover_letter(
        self,
        job_data: Dict[str, Any],
        score_result: Dict[str, Any]
    ) -> str:
        """Generate a customized cover letter using template (fallback method)"""
        from datetime import datetime
        
        job_title = job_data.get('title', 'the position')
        company = job_data.get('company', 'your company')
        location = job_data.get('location', 'New York, NY')
        description = job_data.get('description', '').lower()
        
        # Get the AI-generated reasoning for personalization
        reasoning = score_result.get('reasoning', '')
        
        # Extract key technologies/skills from description
        tech_stack = []
        if 'python' in description:
            tech_stack.append('Python')
        if any(kw in description for kw in ['machine learning', 'ml', 'ai']):
            tech_stack.append('ML/AI')
        if any(kw in description for kw in ['llm', 'gpt', 'language model']):
            tech_stack.append('LLMs')
        if any(kw in description for kw in ['aws', 'cloud', 'kubernetes']):
            tech_stack.append('cloud infrastructure')
        if any(kw in description for kw in ['api', 'rest', 'backend']):
            tech_stack.append('backend systems')
        if any(kw in description for kw in ['data pipeline', 'etl', 'spark']):
            tech_stack.append('data pipelines')
        
        tech_mention = f" with {', '.join(tech_stack[:3])}" if tech_stack else ""
        
        # Craft opening paragraph based on role type and reasoning
        if any(kw in job_title.lower() for kw in ['machine learning', 'ml engineer', 'ai engineer', 'applied ai']):
            opening = f"I am writing to express my strong interest in the {job_title} role at {company}. Having built production ML systems at FibreTrace that process millions of data points{tech_mention}, I'm eager to bring that experience to your team's AI initiatives."
        elif any(kw in job_title.lower() for kw in ['backend', 'software engineer', 'platform']):
            opening = f"I am writing to express my interest in the {job_title} position at {company}. My experience building scalable backend systems and data-processing pipelines at FibreTrace and Friday Technologies{tech_mention} aligns well with your technical requirements."
        elif any(kw in job_title.lower() for kw in ['data engineer', 'data scientist', 'analytics']):
            opening = f"I am excited to apply for the {job_title} role at {company}. At FibreTrace, I developed enterprise-scale data pipelines trusted by Target and Cargill{tech_mention}, and I'm eager to apply that experience to your data platform."
        elif any(kw in job_title.lower() for kw in ['full stack', 'fullstack', 'frontend']):
            opening = f"I am writing to express my interest in the {job_title} position at {company}. My experience spans full-stack development, from production mobile apps at Friday Technologies to enterprise backend systems at FibreTrace{tech_mention}."
        else:
            opening = f"I am writing to apply for the {job_title} role at {company}. My background in building production systems{tech_mention} positions me well to contribute to your engineering team."
        
        # Build middle paragraph highlighting specific relevant experience
        middle = ""
        if any(kw in description for kw in ['ml', 'machine learning', 'ai', 'llm', 'deep learning']):
            middle = "At FibreTrace, I developed ML-driven traceability systems that integrated physical-world tracking with digital analytics at enterprise scale. At Friday Technologies, I architected semantic search and AI-powered backend services using modern ML frameworks. I thrive in environments where experimentation, iteration, and production-ready code intersect to create real-world impact."
        elif any(kw in description for kw in ['backend', 'api', 'microservices', 'distributed']):
            middle = "At FibreTrace, I built backend systems that handle enterprise-level data processing for clients like Target and Cargill. At Friday Technologies, I designed and deployed scalable APIs and services that power production applications. I excel at writing clean, maintainable code that balances performance with reliability."
        elif any(kw in description for kw in ['data', 'pipeline', 'etl', 'analytics', 'warehouse']):
            middle = "At FibreTrace, I constructed data-processing pipelines that transform raw sensor data into actionable insights at scale. This work required careful attention to data quality, pipeline reliability, and performance optimization. I'm comfortable working across the full data stack, from ingestion to visualization."
        else:
            middle = "At FibreTrace, I developed systems that integrated hardware sensors with cloud analytics, requiring deep technical expertise across the stack. At Friday Technologies, I built production mobile and web applications with AI integration. I'm passionate about writing robust, well-tested code that solves real problems."
        
        # Add company-specific touch if possible (look for keywords)
        company_touch = ""
        if 'wordpress' in description or 'automattic' in company.lower():
            company_touch = f"\n\n{company}'s commitment to open-source and distributed work resonates with my engineering philosophy. I've contributed to open-source projects and thrive in collaborative, remote-friendly environments."
        elif 'startup' in description or 'founding' in job_title.lower():
            company_touch = f"\n\nI'm particularly drawn to {company}'s early-stage environment where individual contributors can have outsized impact. I've worked in both startups and enterprise settings, and I bring that versatility to fast-moving teams."
        
        cover_letter = f"""Harvey Houlahan
harveyhoulahan@outlook.com
www.hjhportfolio.com
{datetime.now().strftime('%B %d, %Y')}

Hiring Manager
{company}
{location}

Dear {company} Hiring Team,


{opening}


{middle}{company_touch}


As an Australian citizen, I'm authorized to work in the U.S. under the E-3 visa—a streamlined process that doesn't require H-1B sponsorship and only needs a Labor Condition Application (LCA). I'm based in New York and ready to start immediately.


Thank you for considering my application. I'd welcome the opportunity to discuss how my experience building production ML and backend systems could contribute to {company}'s goals.


Best regards,

Harvey J. Houlahan"""
        return cover_letter
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as filename"""
        # Use translate() for efficient character removal
        invalid_chars = '<>:"/\\|?*'
        translation_table = str.maketrans('', '', invalid_chars)
        result = name.translate(translation_table)
        # Replace spaces with underscores
        result = result.replace(' ', '_')
        # Limit length
        return result[:50]
    
    def _save_application_metadata(self, application: Dict[str, Any]) -> None:
        """Save application metadata to JSON file"""
        import json
        
        metadata_file = os.path.join(self.output_path, f"{application['id']}_metadata.json")
        
        # Create a serializable copy (exclude large content)
        metadata = {
            'id': application['id'],
            'job': application['job'],
            'score': application['score'],
            'cv_pdf_path': application['cv'].get('pdf_path'),
            'cv_highlights': application['cv'].get('highlights'),
            'applicant': application['applicant'],
            'status': application['status'],
            'prepared_at': application['prepared_at']
        }
        
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.debug(f"Saved application metadata: {metadata_file}")
            
            # Also save cover letter as separate text file for easy viewing
            cover_letter_file = metadata_file.replace('_metadata.json', '_cover_letter.txt')
            with open(cover_letter_file, 'w') as f:
                f.write(application.get('cover_letter', ''))
            logger.debug(f"Saved cover letter: {cover_letter_file}")
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def process_jobs(
        self,
        jobs: List[Dict[str, Any]],
        score_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a batch of jobs and prepare applications for eligible ones
        
        Args:
            jobs: List of job data dictionaries
            score_results: Dict mapping job URLs/IDs to their score results
            
        Returns:
            Summary of processing results
        """
        stats = {
            'total_jobs': len(jobs),
            'eligible': 0,
            'applications_prepared': 0,
            'skipped_low_score': 0,
            'skipped_visa': 0,
            'skipped_seniority': 0,
            'skipped_other': 0,
            'applications': []  # Add list of prepared applications
        }
        
        for job in jobs:
            job_key = job.get('url') or job.get('source_id')
            if not job_key:
                continue
            
            score_result = score_results.get(job_key, {})
            if not score_result:
                continue
            
            fit_score = score_result.get('fit_score', 0)
            
            # Track why jobs are skipped
            if fit_score < self.min_fit_score:
                stats['skipped_low_score'] += 1
                continue
            
            if score_result.get('visa_status') == 'excluded':
                stats['skipped_visa'] += 1
                continue
            
            if not score_result.get('seniority_ok', True):
                stats['skipped_seniority'] += 1
                continue
            
            stats['eligible'] += 1
            
            # Prepare application
            application = self.prepare_application(job, score_result)
            if application:
                stats['applications_prepared'] += 1
                stats['applications'].append(application)  # Collect applications
            else:
                stats['skipped_other'] += 1
        
        logger.info(f"Processed {stats['total_jobs']} jobs, prepared {stats['applications_prepared']} applications")
        return stats
    
    def get_pending_applications(self) -> List[Dict[str, Any]]:
        """Get list of pending applications"""
        return self.pending_applications
    
    def mark_applied(self, application_id: str) -> bool:
        """Mark an application as submitted"""
        for app in self.pending_applications:
            if app['id'] == application_id:
                app['status'] = 'applied'
                app['applied_at'] = datetime.now(timezone.utc).isoformat()
                self.completed_applications.append(app)
                self.pending_applications.remove(app)
                
                # Update metadata file
                self._save_application_metadata(app)
                
                logger.info(f"Marked as applied: {application_id}")
                return True
        
        return False
    
    def get_application_stats(self) -> Dict[str, Any]:
        """Get statistics about applications"""
        return {
            'pending': len(self.pending_applications),
            'completed': len(self.completed_applications),
            'total': len(self.pending_applications) + len(self.completed_applications),
            'output_directory': self.output_path
        }


def auto_apply_to_jobs(
    jobs: List[Dict[str, Any]],
    scorer,
    min_fit_score: float = 50.0
) -> Dict[str, Any]:
    """
    Convenience function to automatically prepare applications for eligible jobs
    
    Args:
        jobs: List of job data dictionaries
        scorer: JobScorer instance
        min_fit_score: Minimum fit score to apply
        
    Returns:
        Stats dictionary with application results
    """
    applicator = JobApplicator(min_fit_score=min_fit_score)
    
    # Score jobs and collect results
    score_results = {}
    for job in jobs:
        job_key = job.get('url') or job.get('source_id')
        if job_key:
            score_results[job_key] = scorer.score_job(job)
    
    # Process and prepare applications
    stats = applicator.process_jobs(jobs, score_results)
    stats['applications'] = applicator.get_pending_applications()
    
    return stats


if __name__ == "__main__":
    # Test the applicator
    from scoring.engine import JobScorer
    
    # Initialize
    scorer = JobScorer()
    applicator = JobApplicator()
    
    # Test job that should pass
    good_job = {
        'title': 'Machine Learning Engineer',
        'company': 'FashionTech Inc',
        'url': 'https://example.com/job/ml-engineer',
        'description': '''
        We're looking for an ML Engineer with Python, AWS, and NLP experience.
        Build AI systems for our fashion tech platform. E-3 visa sponsorship available.
        2-3 years experience required.
        ''',
        'location': 'New York, NY',
        'source': 'linkedin'
    }
    
    # Test job that should fail (too senior)
    senior_job = {
        'title': 'Senior Staff Engineer',
        'company': 'BigTech Corp',
        'url': 'https://example.com/job/senior-staff',
        'description': '''
        10+ years experience required. Lead a team of engineers.
        Must have authorization to work in US (no sponsorship).
        ''',
        'location': 'San Francisco, CA',
        'source': 'linkedin'
    }
    
    # Score and check
    good_score = scorer.score_job(good_job)
    senior_score = scorer.score_job(senior_job)
    
    print("=" * 60)
    print("GOOD JOB TEST")
    print("=" * 60)
    print(f"Score: {good_score['fit_score']}")
    print(f"Should apply: {applicator.should_apply(good_job, good_score)}")
    
    print("\n" + "=" * 60)
    print("SENIOR JOB TEST")
    print("=" * 60)
    print(f"Score: {senior_score['fit_score']}")
    print(f"Should apply: {applicator.should_apply(senior_job, senior_score)}")
    
    # Prepare application for good job
    print("\n" + "=" * 60)
    print("PREPARING APPLICATION")
    print("=" * 60)
    
    application = applicator.prepare_application(good_job, good_score)
    if application:
        print(f"Application ID: {application['id']}")
        print(f"CV PDF Path: {application['cv'].get('pdf_path', 'Not generated')}")
        print(f"Status: {application['status']}")
        print("\nCover Letter Preview:")
        print(application['cover_letter'][:500] + "...")
    else:
        print("Application not prepared (job didn't meet criteria)")
    
    print("\n" + "=" * 60)
    print("APPLICATION STATS")
    print("=" * 60)
    print(applicator.get_application_stats())
