"""
Customized CV Generator

Generates tailored CVs/resumes for specific job applications by:
1. Parsing the base resume from the root folder
2. Extracting relevant skills, experiences based on job requirements
3. Generating a customized CV that highlights relevant qualifications
"""

import os
import re
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from profile import HARVEY_PROFILE

# Try to import PDF libraries
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pypdf not available - install with: pip install pypdf")

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available - install with: pip install reportlab")


class CVGenerator:
    """
    Generates customized CVs tailored to specific job postings
    """
    
    # Resume file names to look for in root folder
    RESUME_FILES = ['NY RESUME.pdf', 'RESUME1.pdf', 'resume.pdf', 'Resume.pdf']
    
    def __init__(self, resume_path: Optional[str] = None):
        """
        Initialize CV generator with base resume
        
        Args:
            resume_path: Optional path to resume PDF. If not provided,
                        will search for resume in project root.
        """
        self.resume_path = resume_path or self._find_resume()
        self.resume_text = ""
        self.resume_sections = {}
        
        if self.resume_path and PDF_AVAILABLE:
            self._parse_resume()
        elif not PDF_AVAILABLE:
            logger.info("PDF parsing not available, using profile data for CV generation")
        
        logger.info(f"CVGenerator initialized with resume: {self.resume_path}")
    
    def _find_resume(self) -> Optional[str]:
        """Find resume file in project root"""
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        for filename in self.RESUME_FILES:
            path = os.path.join(root_dir, filename)
            if os.path.exists(path):
                logger.info(f"Found resume: {path}")
                return path
        
        logger.warning("No resume PDF found in root directory")
        return None
    
    def _parse_resume(self) -> None:
        """Parse PDF resume and extract text"""
        if not self.resume_path or not PDF_AVAILABLE:
            return
        
        try:
            reader = PdfReader(self.resume_path)
            text_parts = []
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            self.resume_text = '\n'.join(text_parts)
            self._extract_sections()
            logger.info(f"Resume parsed: {len(self.resume_text)} characters extracted")
            
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            self.resume_text = ""
    
    def _extract_sections(self) -> None:
        """Extract key sections from resume text"""
        # Common section headers
        section_patterns = {
            'summary': r'(?:professional\s*)?summary|objective|profile',
            'experience': r'(?:work\s*)?experience|employment\s*history',
            'education': r'education|academic\s*background',
            'skills': r'skills|technical\s*skills|competencies',
            'projects': r'projects|portfolio',
            'certifications': r'certifications?|licenses?'
        }
        
        text_lower = self.resume_text.lower()
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                start_idx = match.end()
                # Find the next section header or end of text
                next_section_idx = len(self.resume_text)
                for other_pattern in section_patterns.values():
                    if other_pattern != pattern:
                        other_match = re.search(other_pattern, text_lower[start_idx:])
                        if other_match:
                            potential_end = start_idx + other_match.start()
                            if potential_end < next_section_idx:
                                next_section_idx = potential_end
                
                self.resume_sections[section_name] = self.resume_text[start_idx:next_section_idx].strip()
    
    def generate_customized_cv(
        self,
        job_data: Dict[str, Any],
        score_result: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a customized CV tailored to a specific job
        
        Args:
            job_data: Job listing data (title, company, description, etc.)
            score_result: Scoring result with tech matches, industry matches, etc.
            output_path: Optional path to save the generated CV
            
        Returns:
            Dict with:
                - content: The customized CV content (text/html)
                - highlights: Key skills/experiences highlighted
                - pdf_path: Path to generated PDF (if applicable)
        """
        job_title = job_data.get('title', 'Unknown Position')
        company = job_data.get('company', 'Unknown Company')
        description = job_data.get('description', '')
        
        # Get matched elements from scoring
        tech_matches = score_result.get('matches', {}).get('tech', [])
        industry_matches = score_result.get('matches', {}).get('industry', [])
        role_matches = score_result.get('matches', {}).get('role', [])
        
        logger.info(f"Generating customized CV for: {job_title} at {company}")
        logger.info(f"Tech matches to highlight: {tech_matches[:5]}")
        
        # Generate customized summary
        custom_summary = self._generate_custom_summary(
            job_title, company, tech_matches, industry_matches
        )
        
        # Prioritize relevant skills
        prioritized_skills = self._prioritize_skills(tech_matches, description)
        
        # Select relevant experience highlights
        relevant_experience = self._select_relevant_experience(
            job_title, tech_matches, industry_matches
        )
        
        # Generate the CV content
        cv_content = self._build_cv_content(
            custom_summary,
            prioritized_skills,
            relevant_experience,
            job_title,
            company
        )
        
        result = {
            'content': cv_content,
            'highlights': {
                'skills': prioritized_skills[:10],
                'tech_matches': tech_matches[:8],
                'industry_matches': industry_matches
            },
            'customized_for': {
                'job_title': job_title,
                'company': company
            },
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Generate PDF if path provided and library available
        if output_path and REPORTLAB_AVAILABLE:
            pdf_path = self._generate_pdf(cv_content, output_path, job_title, company)
            result['pdf_path'] = pdf_path
        
        return result
    
    def _generate_custom_summary(
        self,
        job_title: str,
        company: str,
        tech_matches: List[str],
        industry_matches: List[str]
    ) -> str:
        """Generate a customized professional summary"""
        # Base summary from profile
        base_summary = HARVEY_PROFILE.get('summary', '')
        
        # Key tech skills to mention (top 4)
        key_tech = tech_matches[:4] if tech_matches else ['Python', 'Machine Learning', 'AWS']
        tech_str = ', '.join(key_tech[:3])
        
        # Industry focus
        industry_focus = industry_matches[0] if industry_matches else 'technology'
        
        # Generate targeted summary
        custom_summary = f"""Results-driven engineer with expertise in {tech_str} and a strong background in {industry_focus}. 
Experienced in building scalable AI/ML solutions and data pipelines. Passionate about leveraging technology 
to solve complex problems and drive innovation. Seeking to bring technical excellence and collaborative spirit 
to the {job_title} role at {company}."""
        
        return custom_summary
    
    def _prioritize_skills(
        self,
        tech_matches: List[str],
        job_description: str
    ) -> List[str]:
        """Prioritize skills based on job requirements"""
        # Get all skills from profile
        all_skills = []
        for category, skills in HARVEY_PROFILE.get('skills', {}).items():
            all_skills.extend(skills)
        
        # Create a scoring system for skills
        skill_scores = {}
        description_lower = job_description.lower()
        
        for skill in all_skills:
            score = 0
            skill_lower = skill.lower()
            
            # High priority: matches in tech_matches (explicitly matched)
            if skill_lower in [t.lower() for t in tech_matches]:
                score += 100
            
            # Medium priority: appears in job description
            if skill_lower in description_lower:
                score += 50
            
            # Add some base score for core skills
            core_skills = ['python', 'machine learning', 'aws', 'sql', 'react']
            if skill_lower in core_skills:
                score += 25
            
            skill_scores[skill] = score
        
        # Sort by score and return
        sorted_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
        return [skill for skill, score in sorted_skills if score > 0]
    
    def _select_relevant_experience(
        self,
        job_title: str,
        tech_matches: List[str],
        industry_matches: List[str]
    ) -> List[Dict[str, Any]]:
        """Select and prioritize relevant experience from profile"""
        # Define experience based on Harvey's profile (from profile.py notable_companies and projects)
        experiences = [
            {
                'title': 'Software Engineer',
                'company': 'FibreTrace',
                'highlights': [
                    'Built AI-powered traceability systems trusted by Target and Cargill',
                    'Developed real-time supply chain transparency solutions',
                    'Implemented ML models for sustainability tracking'
                ],
                'tech': ['Python', 'AWS', 'Machine Learning', 'Data Pipelines'],
                'industry': ['Fashion Tech', 'Sustainability', 'Supply Chain']
            },
            {
                'title': 'Software Engineer',
                'company': 'Friday Technologies',
                'highlights': [
                    'Crafted iOS, visionOS, and macOS innovations with Core ML',
                    'Built generative AI features for Apple platforms',
                    'Developed production-grade mobile applications'
                ],
                'tech': ['Swift', 'SwiftUI', 'CoreML', 'iOS', 'visionOS'],
                'industry': ['Consumer Apps', 'Mobile', 'AI/ML']
            },
            {
                'title': 'ML Engineer',
                'company': 'AgrIQ',
                'highlights': [
                    'Designed smart ear tag IoT system for livestock monitoring',
                    'Built real-time data collection and analytics pipelines',
                    'Implemented predictive models for agricultural applications'
                ],
                'tech': ['Python', 'IoT', 'Machine Learning', 'Data Engineering'],
                'industry': ['AgTech', 'IoT', 'Precision Agriculture']
            }
        ]
        
        # Score each experience based on relevance
        scored_experiences = []
        for exp in experiences:
            score = 0
            
            # Tech match scoring
            for tech in exp['tech']:
                if tech.lower() in [t.lower() for t in tech_matches]:
                    score += 10
            
            # Industry match scoring
            for ind in exp['industry']:
                if ind.lower() in [i.lower() for i in industry_matches]:
                    score += 15
            
            # Role match scoring
            job_title_lower = job_title.lower()
            if 'ml' in job_title_lower or 'machine learning' in job_title_lower:
                if 'ML' in exp['tech'] or 'Machine Learning' in exp['tech']:
                    score += 20
            if 'ios' in job_title_lower or 'mobile' in job_title_lower:
                if 'iOS' in exp['tech'] or 'Swift' in exp['tech']:
                    score += 20
            
            scored_experiences.append((exp, score))
        
        # Sort by score and return top experiences
        scored_experiences.sort(key=lambda x: x[1], reverse=True)
        return [exp for exp, score in scored_experiences]
    
    def _build_cv_content(
        self,
        summary: str,
        skills: List[str],
        experiences: List[Dict[str, Any]],
        job_title: str,
        company: str
    ) -> str:
        """Build the CV content as formatted text"""
        # Header
        cv_parts = [
            "=" * 60,
            f"HARVEY J. HOULAHAN",
            "=" * 60,
            f"Email: {HARVEY_PROFILE.get('email', 'harveyhoulahan@outlook.com')}",
            f"LinkedIn: {HARVEY_PROFILE.get('linkedin', 'linkedin.com/in/harvey-houlahan-245642225')}",
            f"Location: {HARVEY_PROFILE.get('location', 'New York, NY')}",
            "",
            f"[Customized for: {job_title} at {company}]",
            "",
            "=" * 60,
            "PROFESSIONAL SUMMARY",
            "=" * 60,
            summary,
            "",
            "=" * 60,
            "TECHNICAL SKILLS",
            "=" * 60,
        ]
        
        # Group skills by category
        skill_categories = {
            'AI/ML': [],
            'Backend': [],
            'Frontend': [],
            'Cloud': [],
            'Tools': []
        }
        
        ai_keywords = ['ml', 'machine learning', 'ai', 'nlp', 'llm', 'pytorch', 'tensorflow', 'neural', 'deep learning']
        backend_keywords = ['python', 'java', 'sql', 'api', 'backend', 'server', 'database']
        frontend_keywords = ['react', 'swift', 'ios', 'javascript', 'typescript', 'frontend', 'ui']
        cloud_keywords = ['aws', 'cloud', 'docker', 'lambda', 'ec2', 's3']
        
        for skill in skills[:20]:  # Top 20 skills
            skill_lower = skill.lower()
            if any(kw in skill_lower for kw in ai_keywords):
                skill_categories['AI/ML'].append(skill)
            elif any(kw in skill_lower for kw in backend_keywords):
                skill_categories['Backend'].append(skill)
            elif any(kw in skill_lower for kw in frontend_keywords):
                skill_categories['Frontend'].append(skill)
            elif any(kw in skill_lower for kw in cloud_keywords):
                skill_categories['Cloud'].append(skill)
            else:
                skill_categories['Tools'].append(skill)
        
        for category, cat_skills in skill_categories.items():
            if cat_skills:
                cv_parts.append(f"{category}: {', '.join(cat_skills[:6])}")
        
        cv_parts.extend([
            "",
            "=" * 60,
            "PROFESSIONAL EXPERIENCE",
            "=" * 60,
        ])
        
        # Add experiences
        for exp in experiences[:3]:  # Top 3 most relevant
            cv_parts.extend([
                f"\n{exp['title']} | {exp['company']}",
                "-" * 40
            ])
            for highlight in exp['highlights'][:3]:
                cv_parts.append(f"  • {highlight}")
        
        cv_parts.extend([
            "",
            "=" * 60,
            "EDUCATION",
            "=" * 60,
        ])
        
        # Add education from profile
        for edu in HARVEY_PROFILE.get('education', [])[:1]:
            cv_parts.extend([
                f"{edu.get('degree', 'B.S. in Computer Science')}",
                f"{edu.get('institution', 'Monash University')} | {edu.get('graduation', '2025')}",
                f"GPA: {edu.get('gpa', '3.6/4.0')}"
            ])
        
        cv_parts.extend([
            "",
            "=" * 60,
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            "=" * 60,
        ])
        
        return '\n'.join(cv_parts)
    
    def _generate_pdf(
        self,
        content: str,
        output_path: str,
        job_title: str,
        company: str
    ) -> str:
        """Generate a PDF version of the CV"""
        if not REPORTLAB_AVAILABLE:
            logger.warning("reportlab not available, cannot generate PDF")
            return ""
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch
            )
            
            # Create styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=12
            )
            heading_style = ParagraphStyle(
                'Heading',
                parent=styles['Heading2'],
                fontSize=12,
                spaceAfter=6,
                spaceBefore=12
            )
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=4
            )
            
            # Build document content
            story = []
            
            # Title
            story.append(Paragraph("HARVEY J. HOULAHAN", title_style))
            story.append(Spacer(1, 6))
            
            # Contact info
            contact_info = f"""
            Email: {HARVEY_PROFILE.get('email', 'harveyhoulahan@outlook.com')} | 
            LinkedIn: {HARVEY_PROFILE.get('linkedin', '')} | 
            Location: {HARVEY_PROFILE.get('location', 'New York, NY')}
            """
            story.append(Paragraph(contact_info, normal_style))
            story.append(Spacer(1, 12))
            
            # Customization note
            story.append(Paragraph(
                f"<i>Customized for: {job_title} at {company}</i>",
                normal_style
            ))
            story.append(Spacer(1, 12))
            
            # Parse content sections and add to PDF
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('=') or line.startswith('-'):
                    continue
                
                # Check for section headers
                if line in ['PROFESSIONAL SUMMARY', 'TECHNICAL SKILLS', 'PROFESSIONAL EXPERIENCE', 'EDUCATION']:
                    current_section = line
                    story.append(Paragraph(line, heading_style))
                elif line.startswith('•'):
                    story.append(Paragraph(f"• {line[1:].strip()}", normal_style))
                elif '|' in line and current_section == 'PROFESSIONAL EXPERIENCE':
                    story.append(Paragraph(f"<b>{line}</b>", normal_style))
                else:
                    story.append(Paragraph(line, normal_style))
            
            # Build PDF
            doc.build(story)
            logger.info(f"Generated PDF: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return ""
    
    def get_resume_summary(self) -> Dict[str, Any]:
        """Get a summary of the parsed resume"""
        return {
            'path': self.resume_path,
            'text_length': len(self.resume_text),
            'sections_found': list(self.resume_sections.keys()),
            'profile_skills_count': sum(
                len(skills) for skills in HARVEY_PROFILE.get('skills', {}).values()
            )
        }


if __name__ == "__main__":
    # Test the CV generator
    generator = CVGenerator()
    
    print("Resume Summary:")
    print(generator.get_resume_summary())
    
    # Test job
    test_job = {
        'title': 'Machine Learning Engineer',
        'company': 'FashionTech Startup',
        'description': '''
        Looking for an ML Engineer with Python, AWS, and LLM experience.
        Build NLP systems for our fashion tech platform.
        2-3 years experience required.
        '''
    }
    
    test_score = {
        'fit_score': 85,
        'matches': {
            'tech': ['Python', 'AWS', 'ML', 'NLP', 'LLM'],
            'industry': ['Fashion Tech', 'AI/ML'],
            'role': ['ML Engineer']
        }
    }
    
    result = generator.generate_customized_cv(test_job, test_score)
    print("\nGenerated CV Content (first 1000 chars):")
    print(result['content'][:1000])
    print(f"\nHighlights: {result['highlights']}")
