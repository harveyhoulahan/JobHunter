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
                temperature=0.6,  # More controlled, less flowery
                max_tokens=500,   # Shorter letters (~350 words max)
                top_p=0.85,
                frequency_penalty=0.6,  # Strong penalty against AI clichés
                presence_penalty=0.2
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
        return """You write cover letters for a senior software engineer. The goal is concise, professional, and human.

Key principles:
- Get to the point. No fluff, no preamble.
- Write like a professional who's done the work, not trying to impress.
- Specific examples with numbers. "Built X that did Y" not "passionate about building."
- Natural language. How you'd explain it to another engineer, not HR.
- Short. 250-350 words max. 3 paragraphs.

What makes it good:
- Opens with why you're interested in THIS role at THIS company
- Middle paragraph: relevant work you've done with concrete details
- Close: why it's a fit, no begging

What to avoid:
- AI tells: "delve", "landscape", "leverage", "harness", "realm", "revolutionize"
- Flowery language: "eager to explore", "kindred spirit", "audacity"  
- Overly casual: "Hey there", "jumping in", "let's make it happen"
- Marketing speak: "cutting-edge", "innovative", "game-changing"
- Unnecessary adjectives and adverbs
- Opening questions or dramatic statements
- Any phrase that sounds like ChatGPT

Tone:
- Professional but direct
- Confident from competence, not hype
- Conversational without being casual
- Technical enough to show you know what you're talking about

Format:
- No address header or date
- Start with a clear opening sentence
- 3 paragraphs total
- Sign off: "Best, Harvey Houlahan"
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
        edu = HARVEY_PROFILE['education'][0]  # First education entry
        profile_summary = f"""
CANDIDATE: Harvey Houlahan
EDUCATION: {edu['degree']} from {edu['institution']}
LOCATION: {HARVEY_PROFILE['location']}

BACKGROUND:
{HARVEY_PROFILE['summary']}

CORE TECHNICAL SKILLS:
- AI/ML: {', '.join(HARVEY_PROFILE['skills']['ai_ml'][:8])}
- Backend: {', '.join(HARVEY_PROFILE['skills']['backend'][:8])}
- Full-stack: {', '.join(HARVEY_PROFILE['skills']['fullstack'][:6])}
- Cloud & Data: {', '.join(HARVEY_PROFILE['skills']['cloud'][:4])}, {', '.join(HARVEY_PROFILE['skills']['data'][:4])}
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
        
        prompt = f"""Write a cover letter for this job:

ROLE: {title}
COMPANY: {company}
{company_insights}

JOB DESCRIPTION (truncated):
{description[:2000]}

{profile_summary}

{match_analysis}

EXAMPLE OF GOOD WRITING:
"I want to work at {company} on {title} because you're building AI systems for IT management. I've built similar ML systems at scale.

At FibreTrace, I built an analytics platform that processes 1M+ data points daily from cotton supply chains. The system uses PyTorch for real-time tracking and predictive models, serving clients like Target and Cargill. At Friday Technologies, I developed iOS apps with Core ML integration for Apple-recognized products.

My experience with production ML systems, NLP, and LLMs fits what you need for this role."

BANNED WORDS - REWRITE IF YOU USE THESE:
"drawn", "aligns", "resonates", "honed", "spearheaded", "robust", "pivotal", "leveraging", "transforming", "excited", "passionate", "unique", "shaping", "redefining", "innovative", "cutting-edge", "matches", "ambitions"

Write like the example above. Direct, specific, no fluff:"""
        
        return prompt
    
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
