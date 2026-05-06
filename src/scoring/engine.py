"""
Job scoring and matching engine
Evaluates job listings against Harvey's profile
NOW WITH AI-POWERED SEMANTIC SCORING!
"""
import re
import sys
import os
from typing import Dict, List, Tuple, Any
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from profile import HARVEY_PROFILE

# Try to import AI scorer
try:
    from .ai_scorer import get_ai_scorer
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class JobScorer:
    """
    Scores job listings on a 0-100 scale based on:
    - AI Semantic Match (35%) - AI understanding with keyword validation
    - Technical stack match (25%) - Concrete skills matching
    - Industry match (15%) - Domain alignment (priority sectors boosted)
    - Role match (12%) - Position type fit
    - Eligibility match (10%) - Requirements met (boosted importance)
    - Visa friendliness (3%) - E-3 availability
    """
    
    # Scoring weights (must sum to 100)
    # Balanced approach: AI + concrete matching
    WEIGHTS = {
        'ai_semantic': 35,  # DOWN from 50 - AI can be wrong, don't over-trust
        'technical': 25,    # UP from 20 - Concrete skills are important
        'industry': 15,     # UP from 12 - Harvey prioritizes certain sectors
        'role': 12,         # UP from 10 - Role alignment matters
        'eligibility': 10,  # UP from 5 - Meeting requirements is critical
        'visa': 3           # SAME - E-3 is relatively easy
    }
    
    # Section headers that indicate eligibility requirements
    REQUIREMENT_HEADERS = [
        'requirements', 'qualifications', 'required qualifications',
        'minimum qualifications', 'about you', 'you have', 'you are',
        'what we\'re looking for', 'what you\'ll need', 'must have',
        'basic qualifications', 'experience required', 'skills required'
    ]
    
    def __init__(self):
        # Flatten all skills for matching
        self.all_skills = []
        for category in HARVEY_PROFILE['skills'].values():
            self.all_skills.extend([s.lower() for s in category])
        self.all_skills = list(set(self.all_skills))  # Remove duplicates
        
        # Prepare other matching data
        self.industries = [i.lower() for i in HARVEY_PROFILE['industries']]
        self.roles = [r.lower() for r in HARVEY_PROFILE['roles']]
        
        self.visa_positive = [k.lower() for k in HARVEY_PROFILE['visa']['positive_keywords']]
        self.visa_negative = [k.lower() for k in HARVEY_PROFILE['visa']['negative_keywords']]
        
        # Initialize AI scorer
        self.ai_scorer = None
        if AI_AVAILABLE:
            try:
                self.ai_scorer = get_ai_scorer()
            except Exception as e:
                logger.warning(f"Could not initialize AI scorer: {e}")
        
        # Initialize company researcher (for 75%+ matches)
        self.company_researcher = None
        try:
            from research.company_researcher import CompanyResearcher
            self.company_researcher = CompanyResearcher()
            logger.info("Company researcher initialized for deep research on top matches")
        except Exception as e:
            logger.warning(f"Company researcher not available: {e}")
    
    def score_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a job listing and return detailed results
        NOW WITH AI SEMANTIC UNDERSTANDING!
        
        Args:
            job_data: Dictionary with 'title', 'company', 'description', 'location'
            
        Returns:
            Dictionary with score, breakdown, and reasoning
        """
        title = job_data.get('title', '').lower()
        description = job_data.get('description', '').lower()
        location = job_data.get('location', '').lower()
        company = job_data.get('company', '')
        combined_text = f"{title} {description}"
        
        # Extract eligibility sections for focused analysis
        eligibility_text = self._extract_eligibility_sections(description)
        
        # AI SEMANTIC SCORING (NEW!)
        ai_active = bool(self.ai_scorer and description and len(description) > 50)
        ai_score = 0.0  # Neutral if AI not available
        ai_details = {'method': 'disabled' if not self.ai_scorer else 'not_available'}
        if ai_active:
            ai_score, ai_details = self.ai_scorer.score_job_ai(job_data)
        
        # Adjust weights if AI is unavailable
        weights = dict(self.WEIGHTS)
        if not ai_active and 'ai_semantic' in weights:
            weights.pop('ai_semantic', None)
            total = sum(weights.values()) or 1
            for k in list(weights.keys()):
                weights[k] = weights[k] * 100 / total
        
        # Calculate each component
        tech_score, tech_matches = self._score_technical(combined_text, eligibility_text)
        industry_score, industry_matches = self._score_industry(combined_text)
        role_score, role_matches = self._score_role(title, description)
        eligibility_score, eligibility_matches = self._score_eligibility(eligibility_text)
        visa_score, visa_status, visa_keywords = self._score_visa(combined_text)
        
        # Apply weights (NEW: AI gets 40% weight!)
        base_score = (
            (ai_score * weights.get('ai_semantic', 0) / 100) +
            (tech_score * weights.get('technical', 0) / 100) +
            (industry_score * weights.get('industry', 0) / 100) +
            (role_score * weights.get('role', 0) / 100) +
            (eligibility_score * weights.get('eligibility', 0) / 100) +
            (visa_score * weights.get('visa', 0) / 100)
        )
        
        # 🔍 DEEP COMPANY RESEARCH FOR TOP MATCHES (65%+ base score, BEFORE penalties)
        # Check base score before location/seniority penalties to catch great jobs anywhere!
        company_research = None
        if base_score >= 65 and self.company_researcher:
            logger.info(f"🎯 High match detected ({base_score:.1f}%) - researching {company}...")
            try:
                company_research = self.company_researcher.research_company(
                    company_name=company,
                    company_url=job_data.get('company_url')
                )
                
                # Apply research-based score adjustment to BASE score
                if company_research.get('fit_score_adjustment'):
                    adjustment = company_research['fit_score_adjustment']
                    logger.info(f"  Adjusting score by {adjustment:+.1f}% based on company research")
                    base_score = max(0, min(100, base_score + adjustment))
            except Exception as e:
                logger.warning(f"Company research failed for {company}: {e}")
        
        # NOW apply penalties to the (potentially research-boosted) base score
        total_score = base_score
        
        # Check location (GREATLY reduced penalty for high-scoring jobs)
        location_ok, location_penalty, location_flag = self._assess_location(location)
        # For exceptional jobs (65%+), location matters less - worth relocating!
        if not location_ok and total_score >= 65:
            # Reduce penalty: only 5% reduction for great fits instead of 25%
            location_penalty = 0.95
            logger.info(f"  Reducing location penalty for high-scoring job ({total_score:.1f}%)")
        total_score *= location_penalty
        
        # Check seniority
        seniority_ok, seniority_flag, seniority_penalty = self._assess_seniority(title, description)
        total_score *= seniority_penalty
        
        # Generate reasoning WITH BREAKDOWN SCORES
        breakdown_scores = {
            'ai_semantic': round(ai_score, 1),
            'technical': round(tech_score, 1),
            'industry': round(industry_score, 1),
            'role': round(role_score, 1),
            'eligibility': round(eligibility_score, 1),
            'visa': round(visa_score, 1)
        }
        reasoning = self._generate_reasoning(
            tech_matches, industry_matches, role_matches, eligibility_matches,
            visa_status, location_ok, seniority_ok, total_score, ai_score, ai_details,
            breakdown_scores  # Pass the scores!
        )
        
        # Enhance reasoning with company research insights (for 75%+ matches)
        if company_research and self.company_researcher:
            reasoning = self.company_researcher.enhance_reasoning_with_research(
                reasoning, company_research
            )
        
        return {
            'fit_score': round(total_score, 1),
            'breakdown': {
                'ai_semantic': round(ai_score, 1),
                'technical': round(tech_score, 1),
                'industry': round(industry_score, 1),
                'role': round(role_score, 1),
                'eligibility': round(eligibility_score, 1),
                'visa': round(visa_score, 1)
            },
            'matches': {
                'tech': tech_matches[:10],  # Top 10 matches
                'industry': industry_matches,
                'role': role_matches,
                'eligibility': eligibility_matches,
                'visa_keywords': visa_keywords
            },
            'ai_details': ai_details,
            'company_research': company_research,  # Include research data
            'visa_status': visa_status,
            'location_ok': location_ok,
            'location_flag': location_flag,
            'seniority_ok': seniority_ok,
            'seniority_flag': seniority_flag,
            'reasoning': reasoning
        }
    
    def _score_technical(self, text: str, eligibility_text: str = "") -> Tuple[float, List[str]]:
        """
        Score technical stack match (0-100)
        Prioritizes matches found in eligibility/requirements sections
        """
        matches = []
        eligibility_matches = []
        
        for skill in self.all_skills:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(skill) + r'\b'
            
            # Check if in eligibility section (higher value)
            if eligibility_text and re.search(pattern, eligibility_text, re.IGNORECASE):
                eligibility_matches.append(skill)
                matches.append(skill)
            # Check in general text
            elif re.search(pattern, text, re.IGNORECASE):
                matches.append(skill)
        
        # Calculate score based on number of matches
        # Bonus for eligibility section matches (actual requirements)
        if not matches:
            return 0.0, []
        
        num_matches = len(matches)
        num_eligibility = len(eligibility_matches)
        
        # Base score: logarithmic scale
        if num_matches >= 10:
            score = 100
        elif num_matches >= 6:
            score = 80 + (num_matches - 6) * 5
        elif num_matches >= 3:
            score = 50 + (num_matches - 3) * 10
        else:
            score = 30 + num_matches * 10
        
        # BONUS: +10 points if 3+ skills match in eligibility sections
        if num_eligibility >= 3:
            score = min(100, score + 10)
        
        return min(score, 100), matches
    
    def _score_industry(self, text: str) -> Tuple[float, List[str]]:
        """
        Score industry match (0-100)
        PRIORITY: Med Tech, Ag Tech, Fashion Tech get bonus points
        """
        matches = []
        has_priority_industry = False
        text_lower = text.lower()
        
        # Priority industries (Med Tech, Ag Tech, Fashion Tech)
        priority_keywords = [
            'medical', 'medtech', 'healthcare', 'healthtech', 'health tech',
            'clinical', 'medical device', 'diagnostics', 'digital health',
            'agriculture', 'agtech', 'ag tech', 'agricultural', 'farm tech',
            'livestock', 'precision agriculture', 'smart farming',
            'fashion tech', 'fashiontech', 'apparel tech', 'textile tech',
            'fashion ai', 'fashion technology', 'retail tech'
        ]
        
        for industry in self.industries:
            pattern = r'\b' + re.escape(industry) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(industry)
                
                # Check if this is a priority industry
                if any(pri in industry.lower() for pri in priority_keywords) or any(pri in text_lower for pri in priority_keywords):
                    has_priority_industry = True
        
        if not matches:
            return 0.0, []
        
        # Calculate base score
        num_matches = len(matches)
        if num_matches >= 3:
            score = 95
        elif num_matches == 2:
            score = 75
        else:
            score = 55
        
        # BONUS: +15 points for priority industries (Med/Ag/Fashion Tech)
        if has_priority_industry:
            score = min(100, score + 15)
        
        return score, matches
    
    def _score_role(self, title: str, description: str) -> Tuple[float, List[str]]:
        """
        Score role match (0-100)
        Weights description MORE than title to avoid misleading title-only matches
        
        Harvey is qualified for: ML Engineer, Data Scientist, Backend Engineer, AI Engineer,
        Software Engineer, MLOps Engineer, Data Engineer, iOS Engineer, Full Stack
        """
        title_matches = []
        description_matches = []
        
        # Check both title AND description
        combined = f"{title} {description}".lower()
        
        for role in self.roles:
            role_lower = role.lower()
            
            # Title match
            if role_lower in title.lower():
                title_matches.append(role)
            
            # Description match (more important - shows actual work)
            pattern = r'\b' + re.escape(role_lower) + r'\b'
            if re.search(pattern, description, re.IGNORECASE):
                description_matches.append(role)
        
        # Combine matches (description weighted higher)
        all_matches = list(set(title_matches + description_matches))
        
        if not all_matches:
            return 0.0, []
        
        # Score calculation - favor description matches
        # Description match: strong signal of actual responsibilities
        # Title-only match: weaker signal (could be mislabeled)
        base_score = 0
        if description_matches:
            # Description mentions = strong signal
            # Multiple matches = even stronger (e.g., "ML Engineer" + "Data Scientist" work)
            base_score = 95 if len(description_matches) >= 2 else 85
        elif title_matches:
            # Title only = moderate signal
            base_score = 70
        
        return base_score, all_matches
    
    def _extract_eligibility_sections(self, description: str) -> str:
        """
        Extract eligibility/requirements sections from job description
        These sections contain the actual criteria for evaluating candidates
        """
        if not description:
            return ""
        
        eligibility_text = []
        lines = description.split('\n')
        capture_mode = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if line is a requirement header
            is_header = any(header in line_lower for header in self.REQUIREMENT_HEADERS)
            
            if is_header:
                capture_mode = True
                eligibility_text.append(line)
                continue
            
            # Capture lines after header until we hit another section or empty lines
            if capture_mode:
                # Stop if we hit another major section header
                stop_keywords = ['responsibilities', 'what you\'ll do', 'about us', 
                               'benefits', 'perks', 'our company', 'the role',
                               'why join', 'what we offer']
                if any(stop in line_lower for stop in stop_keywords):
                    capture_mode = False
                    continue
                
                # Stop after multiple empty lines
                if not line.strip():
                    # Allow one empty line
                    if i + 1 < len(lines) and not lines[i + 1].strip():
                        capture_mode = False
                    continue
                
                eligibility_text.append(line)
        
        return ' '.join(eligibility_text)
    
    def _score_eligibility(self, eligibility_text: str) -> Tuple[float, Dict[str, Any]]:
        """
        Score based on explicit eligibility criteria (0-100)
        Focuses on required years of experience and must-have skills
        
        Harvey's Experience Context:
        - New grad (graduating Nov 2025) BUT with substantial internship experience
        - FibreTrace: Production ML pipelines, IoT sensor data processing
        - Friday Technologies: iOS/visionOS development, CoreML integration
        - Strong project portfolio: RAG systems, predictive analytics, NLP
        - Technical depth: Python, AWS, ML frameworks, backend systems
        
        Scoring Logic:
        - New grad/entry-level roles: 100% (perfect match)
        - 0-2 years experience: 90% (Harvey qualifies with internship experience)
        - 2-3 years experience: 80% (Harvey's depth compensates for formal years)
        - 3-4 years experience: 60% (stretch but feasible with strong portfolio)
        - 5+ years experience: 20% (too senior, unlikely to be considered)
        """
        if not eligibility_text:
            return 70.0, {'status': 'no_requirements_found'}  # Slightly positive if unclear
        
        matches = {
            'experience_match': False,
            'experience_level': 'unknown',
            'skills_in_requirements': [],
            'concerns': []
        }
        
        # Check for new grad / entry-level indicators (BEST match for Harvey)
        new_grad_patterns = [
            r'\bnew grad\b', r'\bnew graduate\b', r'\brecent graduate\b',
            r'\bentry[- ]level\b', r'\bentry level\b',
            r'\b2025 grad\b', r'\b2026 grad\b',
            r'\bgraduat(e|ing) (in |from )?20(25|26)\b',
            r'\bbachelor\'?s degree required\b', r'\bbs in computer science\b',
            r'\b0[- ]1 year', r'\b0[- ]2 year', r'\b1[- ]2 year'
        ]
        
        for pattern in new_grad_patterns:
            if re.search(pattern, eligibility_text.lower()):
                matches['experience_match'] = True
                matches['experience_level'] = 'new_grad'
                break
        
        # Check experience requirements
        exp_patterns = [
            r'(\d+)\s*[-–to]+\s*(\d+)\s*years',  # Range: 2-5 years
            r'(\d+)\+?\s*years'  # Minimum: 3+ years
        ]
        
        for pattern in exp_patterns:
            matches_found = re.findall(pattern, eligibility_text.lower())
            for match in matches_found:
                if isinstance(match, tuple):
                    # Range match (e.g., "2-5 years")
                    min_years = int(match[0])
                    max_years = int(match[1]) if match[1] else min_years
                    
                    # Harvey: new grad with ~2 years internship experience
                    if min_years == 0 or (min_years <= 2 and max_years <= 3):
                        # 0-2 years, 1-3 years = excellent match
                        matches['experience_match'] = True
                        matches['experience_level'] = '0-2_years'
                    elif min_years <= 2 and max_years <= 4:
                        # 2-4 years = good match (Harvey's depth compensates)
                        matches['experience_match'] = True
                        matches['experience_level'] = '2-3_years'
                    elif min_years <= 3 and max_years <= 5:
                        # 3-5 years = stretch but possible
                        matches['experience_match'] = True
                        matches['experience_level'] = '3-4_years'
                    elif min_years >= 5:
                        # 5+ years = too senior
                        matches['concerns'].append(f'requires_{min_years}-{max_years}_years')
                        matches['experience_level'] = '5+_years'
                else:
                    # Single number match (e.g., "3+ years")
                    years = int(match)
                    
                    if years <= 2:
                        # 2+ years or less = great match
                        matches['experience_match'] = True
                        matches['experience_level'] = '0-2_years'
                    elif years == 3:
                        # 3+ years = good match (Harvey can compete)
                        matches['experience_match'] = True
                        matches['experience_level'] = '2-3_years'
                    elif years == 4:
                        # 4+ years = stretch
                        matches['experience_match'] = True
                        matches['experience_level'] = '3-4_years'
                    elif years >= 5:
                        # 5+ years = too senior
                        matches['concerns'].append(f'requires_{years}+_years')
                        matches['experience_level'] = '5+_years'
        
        # Check for Harvey's skills in requirements (demonstrates capability)
        for skill in self.all_skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, eligibility_text, re.IGNORECASE):
                matches['skills_in_requirements'].append(skill)
        
        # Calculate score based on experience level match
        if matches['experience_level'] == 'new_grad':
            score = 100  # Perfect match - Harvey is a new grad
        elif matches['experience_level'] == '0-2_years':
            score = 90  # Excellent match - Harvey has ~2 years internship experience
        elif matches['experience_level'] == '2-3_years':
            score = 80  # Good match - Harvey's depth and portfolio compensate
        elif matches['experience_level'] == '3-4_years':
            score = 60  # Stretch but feasible with strong technical background
        elif matches['experience_level'] == '5+_years':
            score = 20  # Too senior - unlikely to be competitive
        else:
            # No clear experience requirement found
            score = 70  # Assume entry/mid-level if not specified
        
        # Boost for skills match (shows Harvey meets technical requirements)
        if len(matches['skills_in_requirements']) >= 5:
            score = min(100, score + 10)  # +10% for strong skills alignment
        elif len(matches['skills_in_requirements']) >= 3:
            score = min(100, score + 5)   # +5% for decent skills alignment
        
        # Penalty for explicit concerns (e.g., "must have 7+ years")
        score -= len(matches['concerns']) * 30
        
        return max(0, min(100, score)), matches
    
    def _score_visa(self, text: str) -> Tuple[float, str, List[str]]:
        """
        Score visa friendliness (0-100)
        
        Returns:
            (score, status, keywords_found)
            status: 'explicit', 'possible', 'excluded', 'none'
        """
        positive_found = []
        negative_found = []
        ambiguous_found = []
        
        ambiguous_negatives = {
            'must be authorized', 'authorized to work', 'already authorized',
            'currently authorized', 'require current work authorization',
            'must already have work authorization'
        }
        
        for keyword in self.visa_positive:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                positive_found.append(keyword)
        
        for keyword in self.visa_negative:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                if keyword.lower() in ambiguous_negatives:
                    ambiguous_found.append(keyword)
                else:
                    negative_found.append(keyword)
        
        # Determine status and score
        if negative_found:
            return 0.0, 'excluded', negative_found
        elif positive_found:
            # E-3 or explicit sponsorship mentioned
            if any('e-3' in k or 'e3' in k for k in positive_found):
                return 100.0, 'explicit', positive_found
            else:
                return 80.0, 'explicit', positive_found
        elif ambiguous_found:
            # Ambiguous "authorized" wording - treat as neutral
            return 50.0, 'none', ambiguous_found
        else:
            # No mention - neutral
            return 50.0, 'none', []
    
    def _assess_location(self, location: str) -> Tuple[bool, float, str]:
        """
        Assess location and return (is_ok, penalty_multiplier, flag)
        Flags: preferred (nyc/remote), nearby, outside
        """
        if not location:
            return True, 1.0, 'unknown'
        
        location_lower = location.lower()
        
        nyc_keywords = ['new york', 'nyc', 'manhattan', 'brooklyn', 'queens']
        if any(kw in location_lower for kw in nyc_keywords):
            return True, 1.0, 'preferred'
        
        remote_keywords = ['remote', 'work from home', 'wfh', 'anywhere']
        if any(kw in location_lower for kw in remote_keywords):
            return True, 1.0, 'remote'
        
        nearby_keywords = ['jersey city', 'hoboken', 'newark', 'stamford', 'philadelphia', 'philly', 'boston']
        if any(kw in location_lower for kw in nearby_keywords):
            return True, 0.9, 'nearby'
        
        return False, 0.75, 'outside'
    
    def _assess_seniority(self, title: str, description: str) -> Tuple[bool, str, float]:
        """
        Assess seniority; return (ok_to_pursue, flag, penalty_multiplier)
        Flags: ok, senior_title, senior_years, lead, manager, exec
        """
        combined = f"{title} {description}".lower()
        
        # Hard filters for leadership/exec roles
        leadership_keywords = ['staff', 'principal', 'lead', 'director', 'head', 'chief', 'cto', 'vp', 'manager', 'engineering manager']
        for keyword in leadership_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, combined):
                return False, 'leadership', 0.5
        
        # Experience-based signals
        exp_pattern = r'(\d+)\+?\s*years'
        exp_matches = re.findall(exp_pattern, combined)
        max_years = max([int(y) for y in exp_matches], default=0)
        if max_years >= 8:
            return False, 'years_8_plus', 0.5
        if max_years >= 6:
            return False, 'years_6_plus', 0.6
        if max_years == 5:
            # Slight penalty for 5+ but still acceptable
            return True, 'years_5_plus', 0.85
        
        # Senior title handling
        if re.search(r'\bsenior\b', combined):
            return False, 'senior_title', 0.6
        
        return True, 'ok', 1.0
    
    def _check_location(self, location: str) -> bool:
        """Check if location is acceptable (legacy compatibility)"""
        ok, _, _ = self._assess_location(location)
        return ok
    
    def _check_seniority(self, title: str, description: str) -> bool:
        """
        Check if seniority level is appropriate for Harvey's 3-4 years experience
        Returns False if role is too senior (6+ years or senior titles)
        """
        ok, _, _ = self._assess_seniority(title, description)
        return ok
    
    def _generate_reasoning(
        self,
        tech_matches: List[str],
        industry_matches: List[str],
        role_matches: List[str],
        eligibility_matches: Dict[str, Any],
        visa_status: str,
        location_ok: bool,
        seniority_ok: bool,
        total_score: float,
        ai_score: float = 50.0,
        ai_details: Dict[str, Any] = None,
        breakdown_scores: Dict[str, float] = None
    ) -> str:
        """
        Generate concise, analytical reasoning in 4-5 sentences max.
        Focus on what matters: tech fit, domain relevance, and key requirements.
        """
        
        if breakdown_scores is None:
            breakdown_scores = {}
        if ai_details is None:
            ai_details = {}
        
        sentences = []
        
        # Sentence 1: Overall assessment with key matches
        if total_score >= 75:
            intro = f"Strong match at {total_score:.0f}%"
        elif total_score >= 60:
            intro = f"Solid fit at {total_score:.0f}%"
        else:
            intro = f"Moderate fit at {total_score:.0f}%"
        
        # Add primary reason
        if tech_matches:
            intro += f" - {len(tech_matches)} technical matches including {', '.join(tech_matches[:3])}"
        elif role_matches:
            intro += f" - role aligns as {', '.join(role_matches[:2])}"
        
        sentences.append(intro + ".")
        
        # Sentence 2: Industry/Domain relevance (if applicable)
        if industry_matches:
            priority_industries = ['healthcare', 'healthtech', 'medtech', 'agtech', 'agriculture', 'fashion tech', 'sustainability']
            has_priority = any(ind.lower() in [i.lower() for i in industry_matches] for ind in priority_industries)
            if has_priority:
                sentences.append(f"Priority industry ({', '.join(industry_matches[:2])}) aligns with target sectors.")
            else:
                sentences.append(f"Industry experience applicable: {', '.join(industry_matches[:2])}.")
        
        # Sentence 3: Visa/Location/Seniority concerns (if any)
        concerns = []
        if visa_status == 'excluded':
            concerns.append("visa sponsorship explicitly excluded")
        elif visa_status == 'explicit':
            concerns.append("offers visa sponsorship")
        
        if not location_ok:
            concerns.append("not in NYC/remote")
        
        if not seniority_ok:
            concerns.append("senior-level position")
        
        if concerns:
            sentences.append(f"Note: {', '.join(concerns)}.")
        
        # Sentence 4: Requirements gap (if significant)
        if eligibility_matches:
            missing_reqs = eligibility_matches.get('missing', [])
            if missing_reqs and len(missing_reqs) >= 2:
                sentences.append(f"May need to emphasize transferable skills for: {', '.join(missing_reqs[:2])}.")
        
        # Sentence 5: AI semantic assessment (only if very relevant)
        if ai_details and ai_details.get('method') == 'sentence_transformer':
            similarity = ai_details.get('similarity', 0)
            if similarity >= 0.7:
                sentences.append(f"Strong semantic alignment detected (similarity: {similarity:.2f}).")
            elif similarity < 0.4 and total_score < 60:
                sentences.append(f"Limited semantic overlap - review job description carefully.")
        
        # Return max 5 sentences
        return " ".join(sentences[:5])
    
    def _parse_title_seniority(self, title: str) -> str:
        """Parse job title to determine seniority level"""
def score_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score a job listing"""
    scorer = JobScorer()
    return scorer.score_job(job_data)


if __name__ == "__main__":
    # Test the scorer
    test_job = {
        'title': 'Machine Learning Engineer',
        'company': 'FashionTech Startup',
        'description': '''
        We're looking for an ML Engineer to build LLM-powered features for our 
        sustainable fashion marketplace. You'll work with Python, AWS, and modern 
        ML frameworks. Experience with NLP and computer vision is a plus.
        
        We offer visa sponsorship including E-3 visas.
        
        Requirements:
        - 2-3 years experience with Python and machine learning
        - Strong understanding of NLP and LLMs
        - AWS experience preferred
        ''',
        'location': 'New York, NY'
    }
    
    result = score_job(test_job)
    print(f"Fit Score: {result['fit_score']}/100")
    print(f"\nBreakdown:")
    for category, score in result['breakdown'].items():
        print(f"  {category}: {score}")
    print(f"\nReasoning: {result['reasoning']}")
