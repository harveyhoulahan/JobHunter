"""
GPT-4 Powered Cover Letter Generator
Uses OpenAI's GPT-4 to create compelling, highly personalized cover letters
that showcase Harvey's unique value proposition for each role.
"""

import os
import requests
from typing import Dict, Any, Optional
from loguru import logger
from openai import OpenAI
from bs4 import BeautifulSoup

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
        
        # Research company website first
        company_context = self._research_company_website(job_data.get('company'))
        
        # Build comprehensive context for GPT-4
        prompt = self._build_prompt(job_data, score_data, company_context, tone)
        
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
                temperature=0.7,  # Balanced creativity
                max_tokens=500,   # Allow for detailed examples with metrics
                top_p=0.9,
                frequency_penalty=0.8,  # Strong penalty against AI clichés
                presence_penalty=0.3
            )
            
            cover_letter = response.choices[0].message.content.strip()
            
            logger.info(f"Generated {len(cover_letter)} character cover letter")
            return cover_letter
            
        except Exception as e:
            logger.error(f"GPT-4 generation failed: {e}")
            # Fallback to template-based generation
            return self._generate_fallback(job_data, score_data)
    
    def _research_company_website(self, company_name: str) -> Dict[str, Any]:
        """
        Scrape company website for culture, mission, values
        Returns insights about the company
        """
        if not company_name:
            return {}
        
        try:
            # Try common patterns for company websites
            search_query = f"{company_name} company website"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Simple approach: Try company.com, company.io, etc.
            domain_variants = [
                f"https://{company_name.lower().replace(' ', '')}.com",
                f"https://{company_name.lower().replace(' ', '')}.io",
                f"https://www.{company_name.lower().replace(' ', '')}.com"
            ]
            
            company_info = {
                'mission': '',
                'values': [],
                'culture_keywords': []
            }
            
            for url in domain_variants:
                try:
                    response = requests.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract mission/about text
                        text_content = soup.get_text()[:2000]  # First 2000 chars
                        
                        # Look for mission/values keywords
                        mission_keywords = ['mission', 'vision', 'purpose', 'about us', 'what we do']
                        culture_keywords = ['culture', 'values', 'team', 'people', 'diversity', 'innovation']
                        
                        for keyword in mission_keywords:
                            if keyword in text_content.lower():
                                # Extract surrounding context
                                idx = text_content.lower().find(keyword)
                                company_info['mission'] = text_content[max(0, idx-100):idx+200]
                                break
                        
                        for keyword in culture_keywords:
                            if keyword in text_content.lower():
                                company_info['culture_keywords'].append(keyword)
                        
                        logger.info(f"Successfully scraped {company_name} website: {url}")
                        return company_info
                        
                except Exception as e:
                    continue
            
            logger.debug(f"Could not scrape {company_name} website")
            return company_info
            
        except Exception as e:
            logger.debug(f"Website research failed for {company_name}: {e}")
            return {}
    
    def _get_system_prompt(self) -> str:
        """System prompt that defines GPT-4's role and style"""
        return """You write SHORT, GENUINE cover letters that blend concise directness with concrete examples.

STYLE BLEND - Two reference examples:

EXAMPLE 1 (Concise & Direct):
"Dear Cohere Hiring Team,

I am writing to express my interest in the Software Engineer - Applied ML (US/CAN) position at Cohere. My experience building NLP models and machine learning systems for supply chain tracking at FibreTrace, as core ML on iOS/visionOS at Friday Technologies, aligns well with your focus on deploying frontier models and AI agents. The tech stack I've worked with, including PyTorch, AWS, and various MLOps tools, seems like a good fit for your projects.

As an Australian citizen based in New York, I'm eligible for the E-3 visa, which simplifies work authorization in the U.S., and I'm available for onsite work. I'm particularly excited by the opportunity to contribute to Cohere's mission of scaling intelligence through custom LLMs and AI agents. My background in applying ML/AI across different platforms has equipped me with a versatile skill set that can adapt to Cohere's innovative environment.

Thank you for considering my application. I would appreciate the chance to discuss how my experience can help drive value for Cohere's customers and further your mission of shaping the future of AI.

Sincerely,
Harvey Houlahan"

EXAMPLE 2 (Specific & Metric-Driven):
"Dear Hiring Team,

Coram AI's focus on reimagining video security through computer vision and AI aligns closely with my background in crafting solutions that blend real-time data provenance with AI-powered analytics across the domains of supply chain management and tech innovation. I've delivered scalable machine learning models and data processing pipelines in Python, C++, Swift, and leveraged cloud-native technologies (AWS, Docker) to handle terabyte-scale datasets.

At FibreTrace, I engineered a luminescent-pigment solution for tracking cotton supply chains, including:
• Deployment of NLP models (RAG, GPT) for semantic search across global supply chain data, improving traceability and transparency metrics by over 60%.
• Development of real-time analytics dashboards using React and Swift for iOS platforms, enabling instant provenance verification that supported decision-making processes for clients like Target and Cargill.

At Friday Technologies, an Apple-recognized consultancy, I developed innovations using Core ML on iOS/visionOS/macOS platforms:
• Implemented generative models for enhancing image quality in low-light conditions on visionOS, reducing error rates by 25% in object recognition tasks.
• Engineered a scalable ETL pipeline on AWS Cloud-Native stack for processing multi-terabyte datasets from mobile sensors, optimizing data flow efficiency by 40%.

I'm excited to bring the same discipline to Coram AI: turning data into actionable intelligence that powers your platform in real time. I would value the chance to discuss how my experience in Python, C++, Cloud Engineering, and machine learning fundamentals can help Coram AI deliver impactful security solutions with optimized latency and throughput.

Sincerely,
Harvey Houlahan"

YOUR WRITING STYLE:
Blend these approaches based on the role:
- Technical/ML roles: Use specific examples with metrics (like Example 2)
- General engineering: Keep it concise and direct (like Example 1)
- Always include E-3 visa mention and New York location
- Use bullet points ONLY when showing concrete achievements with metrics
- Otherwise use flowing paragraphs

STRICT RULES:
1. MAX 200 words for concise style, MAX 250 words if using bullet points with metrics
2. Start with "Dear [Company] Hiring Team," or "Dear Hiring Manager,"
3. First paragraph: Company mission alignment + relevant experience
4. Second paragraph: E-3 visa status OR specific achievements with metrics
5. Third paragraph: Enthusiasm + call to action
6. Sign: "Sincerely, Harvey Houlahan"

FORBIDDEN PHRASES:
- "resonates deeply"
- "passionate about"
- "thrilled to leverage"
- "cutting-edge solutions"
- "robust" (unless talking about code robustness specifically)

GOOD PHRASES:
- "aligns closely/well with"
- "excited to bring" / "excited by the opportunity"
- "I would appreciate the chance to discuss"
- "My experience in X can help [company] achieve Y"
- Specific metrics: "60% improvement", "25% reduction", "40% optimization"
"""
    
    def _build_prompt(
        self,
        job_data: Dict[str, Any],
        score_data: Dict[str, Any],
        company_context: Dict[str, Any],
        tone: str
    ) -> str:
        """Build detailed prompt with all context GPT-4 needs"""
        
        company = job_data.get('company', 'the company')
        title = job_data.get('title', 'this role')
        description = job_data.get('description', '')[:2000]  # Limit to avoid token overflow
        
        # Extract key insights from scoring
        tech_matches = score_data.get('matches', {}).get('tech', [])
        fit_score = score_data.get('fit_score', 0)
        
        # Build company insights
        company_info = ""
        if company_context.get('mission'):
            company_info = f"\nCOMPANY MISSION/FOCUS:\n{company_context['mission']}\n"
        if company_context.get('culture_keywords'):
            company_info += f"\nCOMPANY CULTURE: {', '.join(company_context['culture_keywords'])}\n"
        
        # Determine if this is a technical/ML role that warrants detailed examples
        is_technical_role = any(keyword in title.lower() + description.lower() 
                               for keyword in ['machine learning', 'ml', 'ai', 'data science', 
                                             'computer vision', 'nlp', 'deep learning'])
        
        style_guidance = ""
        if is_technical_role and fit_score > 70:
            style_guidance = """
APPROACH: Use the METRIC-DRIVEN style (like Coram AI example)
- Include bullet points with specific achievements and metrics
- Mention: 60% improvement in traceability (NLP/RAG at FibreTrace)
- Mention: 25% error reduction in object recognition (visionOS at Friday)
- Mention: 40% data flow optimization (ETL on AWS)
- Show depth in Python, ML/AI, PyTorch, AWS, cloud-native tech
- Max 250 words
"""
        else:
            style_guidance = """
APPROACH: Use the CONCISE & DIRECT style (like Cohere example)
- Flowing paragraphs, no bullet points
- Brief mention of FibreTrace (NLP, supply chain) and Friday (iOS/visionOS ML)
- Focus on alignment and transferable skills
- Max 200 words
"""
        
        prompt = f"""Write a cover letter for this job using the BLENDED STYLE:

ROLE: {title} at {company}
FIT SCORE: {fit_score}%
{company_info}

JOB DESCRIPTION:
{description[:1500]}

HARVEY'S BACKGROUND:
- Currently based in New York, NY
- Australian citizen eligible for E-3 visa (no H-1B needed, only requires LCA)
- Available for onsite/hybrid work
- Highly transferable skills across ML, backend systems, data pipelines

KEY EXPERIENCE:
• FibreTrace: Built ML systems for supply chain tracking (Target, Cargill clients)
  - NLP models (RAG, GPT) for semantic search: 60% improvement in traceability
  - Real-time analytics dashboards (React, Swift iOS): instant provenance verification
  - Processing 1M+ data points daily (PyTorch, AWS)
  
• Friday Technologies (Apple-recognized consultancy)
  - Core ML on iOS/visionOS: generative models for low-light image enhancement, 25% error reduction
  - Scalable ETL pipeline on AWS Cloud-Native: multi-terabyte datasets from mobile sensors, 40% efficiency gain
  
• Tech stack: {', '.join(tech_matches[:8]) if tech_matches else 'Python, C++, Swift, ML/AI, PyTorch, AWS, Docker, React'}

{style_guidance}

STRUCTURE:
Paragraph 1: Company mission/focus alignment + relevant experience overview
Paragraph 2: Either (A) specific achievements with metrics OR (B) E-3 visa + transferable skills
Paragraph 3: Excitement about opportunity + call to action

Remember:
- Sound genuine and human
- Use "aligns well/closely with" naturally
- Be specific about tech but keep it flowing
- Mention E-3 visa and New York location
- Close with appreciation and discussion invitation

Write the letter now:"""
        
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
