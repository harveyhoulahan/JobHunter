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
        return """You write technical cover letters for a software engineer. Use this EXACT style:

REFERENCE EXAMPLE:
"Centene's mission in improving health outcomes with technology resonates with my background building high-reliability software across data-heavy domains (energy systems, supply chains, and consumer apps). I've delivered production modules spanning service interfaces, business logic, UI, and data access layers in Python, C, and C#; I also work comfortably with Java/Go stacks and modern front-ends (React) on AWS.

At the Australian Energy Market Operator (AEMO), I engineered end-to-end data flows over large market datasets (MMS/NEM/NEMWeb), including:
• High-throughput C parsers for telemetry/market files (streaming validation, memory-mapped I/O), with Python bindings feeding ETL and analytics dashboards used in real-time operations.
• C# microservices interfacing with MMS schemas/APIs and SQL stores (retryable jobs, schema-aware transforms, RBAC/audit), reducing reporting latency and improving reliability for PASA/dispatch workflows.

I'm excited to bring the same discipline to Centene: implementing well-factored services and process flows, shaping designs that meet functional/non-functional requirements, and contributing to secure, testable code that scales."

STRUCTURE (3 paragraphs):
1. Opening: "[Company]'s mission/focus in [X] resonates with my background building [Y] across [domains]. I've delivered [specific tech/systems] in [languages/stack]."

2. Experience bullets: "At [Company], I [built/engineered/developed] [system], including:
   • [Specific technical achievement with metrics/tech stack]
   • [Another achievement with technical details]"

3. Close: "I'm excited to bring the same discipline to [Company]: [what you'll do]. I would value the chance to discuss how my experience in [tech stack] can help [Company] [achieve X]."

KEY STYLE POINTS:
- Technical density: mention specific frameworks, patterns, metrics
- Bullet points with parenthetical tech details: "(streaming validation, memory-mapped I/O)"
- Action verbs: engineered, built, delivered, shipped, implemented
- Concrete outcomes: "reducing latency", "improving reliability", "used in real-time operations"
- Sign off: "Sincerely, Harvey Houlahan" (NOT "Best")

FORBIDDEN:
- Do NOT use: "drawn to", "aligns", "honed", "spearheaded", "robust", "leveraging", "passionate", "innovative", "cutting-edge"
- Do NOT be casual or flowery
- Do NOT sound like marketing copy
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
        
        prompt = f"""Write a technical cover letter for this job using the EXACT style from the reference example:

ROLE: {title}
COMPANY: {company}
{company_insights}

JOB DESCRIPTION (key excerpts):
{description[:2000]}

{profile_summary}

{match_analysis}

INSTRUCTIONS:
Follow the reference example structure EXACTLY:

Paragraph 1: "{company}'s [mission/focus] in [what they do] resonates with my background building [relevant systems] across [domains]. I've delivered [specific modules/systems] in [tech stack list]."

Paragraph 2: "At [FibreTrace or Friday Technologies], I [engineered/built/developed] [specific system], including:
• [Technical achievement with parenthetical details about tech/metrics]
• [Another achievement with technical depth]
• [Optional third bullet]"

Add second company if relevant with similar format.

Paragraph 3: "I'm excited to bring the same discipline to {company}: [what you'll contribute]. I would value the chance to discuss how my experience in [list tech stack] can help {company} [achieve their goal]."

Sign off: "Sincerely, Harvey Houlahan"

CRITICAL: Match the technical density and parenthetical style: "(PyTorch, real-time inference)", "(streaming validation, memory-mapped I/O)", etc.

Write the cover letter:"""
        
        return prompt
    
    def _generate_fallback(self, job_data: Dict[str, Any], score_data: Dict[str, Any]) -> str:
        """Fallback template if GPT-4 fails"""
        company = job_data.get('company', 'your company')
        title = job_data.get('title', 'this role')
        
        return f"""I'm writing to express my interest in the {title} position at {company}.

At FibreTrace, I built production ML systems that process supply chain data at enterprise scale for clients like Target and Cargill. The work included:
• ML-powered analytics platform handling 1M+ data points daily (PyTorch, real-time inference)
• Scalable data pipelines for traceability tracking (Python, AWS Lambda, S3)
• Production model deployment with monitoring and observability

At Friday Technologies, I developed iOS applications with Core ML integration, delivering Apple-recognized products combining device capabilities with intelligent features.

I'm excited to bring the same technical discipline to {company}. I would value the chance to discuss how my experience in Python, PyTorch, AWS, and production ML systems can help {company} achieve its goals.

Sincerely,
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
