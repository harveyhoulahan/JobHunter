"""
GPT-4 Powered Cover Letter Generator
Uses OpenAI's GPT-4 to create compelling, highly personalized cover letters
that showcase Harvey's unique value proposition for each role.
"""

import os
from typing import Dict, Any, Optional
from loguru import logger
from openai import OpenAI

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from profile import HARVEY_PROFILE


class GPT4CoverLetterGenerator:
    """
    Elite cover letter generation using GPT-4-turbo
    Creates compelling narratives that connect Harvey's experience to each role
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GPT-4 generator
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY environment variable)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info("GPT-4 Cover Letter Generator initialized")
    
    def generate_cover_letter(
        self,
        job_data: Dict[str, Any],
        score_data: Dict[str, Any],
        tone: str = "professional_enthusiastic"
    ) -> str:
        """
        Generate a compelling cover letter using GPT-4
        
        Args:
            job_data: Job posting details (title, company, description, etc.)
            score_data: AI scoring analysis (fit_score, reasoning, matches)
            tone: Writing style - professional_enthusiastic, technical, storytelling
        
        Returns:
            Beautifully written cover letter
        """
        
        # Build comprehensive context for GPT-4
        prompt = self._build_prompt(job_data, score_data, tone)
        
        try:
            logger.info(f"Generating GPT-4 cover letter for {job_data.get('company')} - {job_data.get('title')}")
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",  # Most capable model
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,  # Creative but focused
                max_tokens=1000,  # ~700 word cover letter
                top_p=0.95,
                frequency_penalty=0.3,  # Reduce repetition
                presence_penalty=0.4    # Encourage diverse language
            )
            
            cover_letter = response.choices[0].message.content.strip()
            
            logger.info(f"Generated {len(cover_letter)} character cover letter")
            return cover_letter
            
        except Exception as e:
            logger.error(f"GPT-4 generation failed: {e}")
            # Fallback to template-based generation
            return self._generate_fallback(job_data, score_data)
    
    def _get_system_prompt(self) -> str:
        """System prompt that defines GPT-4's role and style"""
        return """You write cover letters for a senior software engineer who knows his worth but doesn't need to prove it.

The vibe:
- Cool, calm, collected. You're not desperate, you're selective.
- Written like a human, not a corporate drone or AI bot
- No buzzwords, no fluff, no "passionate about technology" garbage
- Confident but never arrogant. You've done the work, the results speak.
- Natural language. Like you're explaining why this role makes sense over coffee.

What makes a good letter:
- Gets to the point. No rambling intros.
- Shows don't tell. Built X that did Y for Z company. Numbers matter.
- Makes it clear why THIS role at THIS company, not just any job
- Reads like Harvey actually wrote it, not a template generator
- 3 tight paragraphs, maybe 4. Under 400 words.

What to avoid:
- Corporate speak ("synergize", "leverage", "passionate")
- Begging energy ("I would be honored", "I hope to hear from you")
- Generic praise ("your company is amazing!")
- Fake enthusiasm with exclamation marks
- Robotic formatting or overly formal tone
- Any clichés about being a "team player" or "fast learner"

Format:
- Skip the address header and date stuff. Just start.
- Open with why you're interested, straight up.
- Middle paragraph: what you've built that's relevant
- Close: why it's a good fit, both ways
- Sign off: "Best, Harvey Houlahan" (no "regards" or "sincerely")
"""
    
    def _build_prompt(
        self,
        job_data: Dict[str, Any],
        score_data: Dict[str, Any],
        tone: str
    ) -> str:
        """Build detailed prompt with all context GPT-4 needs"""
        
        company = job_data.get('company', 'the company')
        title = job_data.get('title', 'this role')
        description = job_data.get('description', '')[:3000]  # Limit to avoid token overflow
        
        # Extract key insights from scoring
        fit_score = score_data.get('fit_score', 0)
        reasoning = score_data.get('reasoning', '')
        tech_matches = score_data.get('matches', {}).get('tech', [])
        role_matches = score_data.get('matches', {}).get('role', [])
        company_research = score_data.get('company_research', {})
        
        # Build Harvey's profile summary
        profile_summary = f"""
CANDIDATE: Harvey Houlahan
EDUCATION: {HARVEY_PROFILE['education']['degree']} from {HARVEY_PROFILE['education']['university']}

KEY EXPERIENCE:
{self._format_experience()}

TECHNICAL SKILLS:
{self._format_skills()}

ACHIEVEMENTS:
{self._format_achievements()}
"""
        
        # Build company insights if available
        company_insights = ""
        if company_research and company_research.get('insights'):
            company_insights = "\n\nCOMPANY RESEARCH INSIGHTS:\n" + "\n".join(
                f"- {insight}" for insight in company_research['insights'][:3]
            )
        
        # Build matching analysis
        match_analysis = f"""
FIT ANALYSIS (AI Score: {fit_score}%):
{reasoning}

Technical Alignment: {', '.join(tech_matches[:5]) if tech_matches else 'General tech stack'}
Role Alignment: {', '.join(role_matches[:3]) if role_matches else 'Software engineering'}
"""
        
        prompt = f"""Write a compelling cover letter for this job application:

ROLE: {title}
COMPANY: {company}
{company_insights}

JOB DESCRIPTION:
{description}

{profile_summary}

{match_analysis}

INSTRUCTIONS:
1. Open with a strong hook that connects Harvey's unique background to {company}'s mission or this specific role
2. In 2-3 paragraphs, weave together:
   - Specific examples from Harvey's FibreTrace ML work (supply chain ML, production systems, PyTorch)
   - Relevant iOS/mobile experience from Friday Technologies if applicable
   - Technical depth that shows he can handle the role's challenges
   - Metrics and impact where possible (e.g., "deployed models processing 100K+ daily transactions")
3. Show genuine interest in {company} specifically (use company research insights if provided)
4. Address visa situation naturally if relevant (E-3 visa eligible, similar to H1B but faster)
5. Close with enthusiasm and clear call to action

TONE: {tone}
LENGTH: 300-400 words (3-4 paragraphs)
STYLE: Confident, specific, metric-driven, genuinely enthusiastic

Write the cover letter now:"""
        
        return prompt
    
    def _format_experience(self) -> str:
        """Format Harvey's work experience for context"""
        exp_parts = []
        for job in HARVEY_PROFILE['experience']:
            exp_parts.append(
                f"- {job['title']} at {job['company']} ({job['period']}): "
                f"{', '.join(job['highlights'][:2])}"
            )
        return "\n".join(exp_parts)
    
    def _format_skills(self) -> str:
        """Format technical skills"""
        skills = []
        for category, items in HARVEY_PROFILE['skills'].items():
            skills.append(f"{category.title()}: {', '.join(items[:5])}")
        return "\n".join(skills)
    
    def _format_achievements(self) -> str:
        """Format key achievements"""
        return "\n".join(f"- {ach}" for ach in HARVEY_PROFILE['achievements'][:4])
    
    def _generate_fallback(self, job_data: Dict[str, Any], score_data: Dict[str, Any]) -> str:
        """Fallback template if GPT-4 fails"""
        company = job_data.get('company', 'your company')
        title = job_data.get('title', 'this role')
        
        return f"""I'm writing to express my strong interest in the {title} position at {company}.

With my background in machine learning engineering at FibreTrace, where I built production ML pipelines processing supply chain data at scale, I'm excited about the opportunity to bring my experience in PyTorch, Python, and scalable ML systems to your team.

At FibreTrace, I designed and deployed ML models handling 100,000+ daily predictions, built real-time feature engineering pipelines, and collaborated across teams to deliver production systems that created measurable business impact. This hands-on experience with the full ML lifecycle—from data processing to model deployment—aligns well with the challenges outlined in your job description.

I'm particularly drawn to {company} because of your work in this space. As an E-3 visa eligible candidate, I can start quickly and am excited to contribute to your mission.

I'd love to discuss how my experience building production ML systems can add value to your team. Thank you for considering my application.

Best regards,
Harvey Houlahan"""


# Convenience function for easy import
def generate_gpt4_cover_letter(
    job_data: Dict[str, Any],
    score_data: Dict[str, Any],
    api_key: Optional[str] = None
) -> str:
    """
    Generate a GPT-4 powered cover letter
    
    Args:
        job_data: Job details
        score_data: AI scoring results
        api_key: OpenAI API key (optional, uses env var if not provided)
    
    Returns:
        Cover letter text
    """
    generator = GPT4CoverLetterGenerator(api_key=api_key)
    return generator.generate_cover_letter(job_data, score_data)
