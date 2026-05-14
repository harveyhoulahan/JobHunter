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

from profile import HARVEY_PROFILE  # type: ignore[import-untyped]

# SCORE_DEBUG=true → logs every component score at DEBUG level per job
SCORE_DEBUG = os.getenv("SCORE_DEBUG", "").lower() in ("1", "true", "yes")

# Try to import AI scorer
_get_ai_scorer_fn = None
try:
    from .ai_scorer import get_ai_scorer as _get_ai_scorer_fn
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class JobScorer:
    """
    Scores job listings on a 0-100 scale based on:
    - AI Semantic Match (40%) — Kimi K2.5 deep contextual understanding
    - Technical stack match (20%) — skill keyword overlap (pure, no culture)
    - Culture fit (15%) — culture signal boosts/penalties (explicit component)
    - Role match (10%) — title/description role signal
    - Industry match (10%) — domain alignment
    - Eligibility match (2%) — experience years / requirements
    - Visa friendliness (3%) — sponsorship status

    When AI is unavailable (is_fallback=True), the 40% AI weight is
    redistributed proportionally across the remaining keyword components.
    """

    # Scoring weights (must sum to 100)
    WEIGHTS = {
        'ai_semantic': 40,  # Kimi K2.5 contextual score — dominant signal
        'technical':   20,  # Pure skill-keyword match (culture removed to own component)
        'culture':     15,  # Culture/environment fit — boost/penalise signals
        'role':        10,  # Role title + description match
        'industry':    10,  # Domain / industry alignment
        'eligibility':  2,  # Experience years match (unreliable — kept low)
        'visa':         3,  # Sponsorship / visa status
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
        
        # Support both old key names and new profile schema
        visa = HARVEY_PROFILE.get('visa', {})
        self.visa_positive = [k.lower() for k in (
            visa.get('sponsorship_keywords_positive') or visa.get('positive_keywords', [])
        )]
        self.visa_negative = [k.lower() for k in (
            visa.get('sponsorship_keywords_negative') or visa.get('negative_keywords', [])
        )]
        
        # Initialize AI scorer
        self.ai_scorer = None
        if AI_AVAILABLE and _get_ai_scorer_fn is not None:
            try:
                self.ai_scorer = _get_ai_scorer_fn()
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
    
    def score_title_only(self, job_data: Dict[str, Any]) -> float:
        """
        Cheap pre-filter score using only title + company — no DB, no embeddings, no AI.
        Returns 0.0–1.0. Jobs below 0.15 should be dropped before fetching descriptions.
        """
        title = (job_data.get('title') or '').lower()
        company = (job_data.get('company') or '').lower()
        combined = f"{title} {company}"

        kw_cfg = HARVEY_PROFILE.get("keywords", {})
        penalise_kws = [k.lower() for k in kw_cfg.get("penalise", [])]
        boost_kws = [k.lower() for k in kw_cfg.get("boost", [])]

        # Hard exclude: any penalise keyword in title → score = 0
        for kw in penalise_kws:
            if kw in title:
                return 0.0

        # Role match: does title contain any desired role?
        role_hit = any(r.lower() in title for r in HARVEY_PROFILE.get("roles", []))

        # Boost keyword hit in title+company
        boost_hit = any(kw in combined for kw in boost_kws)

        # Skill keyword hit in title (quick check using flattened skills)
        skill_hit = any(skill in title for skill in self.all_skills)

        # Build a simple score
        score = 0.0
        if role_hit:
            score += 0.6
        if skill_hit:
            score += 0.25
        if boost_hit:
            score += 0.15

        return min(score, 1.0)

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
        
        # ── AI SEMANTIC SCORING ───────────────────────────────────────────────
        ai_score = 0.0
        ai_details: Dict[str, Any] = {'method': 'disabled', 'is_fallback': True}
        if self.ai_scorer is not None and description and len(description) > 50:
            ai_score, ai_details = self.ai_scorer.score_job_ai(job_data)

        # ai_active = True only when Kimi returned a real score (not a fallback).
        # On fallback, set ai_active=False so the 40% weight is redistributed
        # to keyword components instead of polluting scores with a fake 50.
        ai_active = bool(
            self.ai_scorer is not None
            and description
            and len(description) > 50
            and not ai_details.get('is_fallback', True)
        )

        # Adjust weights if AI is unavailable / fallback
        weights: Dict[str, float] = {k: float(v) for k, v in self.WEIGHTS.items()}
        if not ai_active and 'ai_semantic' in weights:
            weights.pop('ai_semantic', None)
            total = sum(weights.values()) or 1.0
            for k in list(weights.keys()):
                weights[k] = weights[k] * 100.0 / total
        
        # ── KEYWORD COMPONENTS ────────────────────────────────────────────────
        tech_score, tech_matches = self._score_technical(combined_text, eligibility_text)
        culture_score = self._score_culture(combined_text)
        industry_score, industry_matches = self._score_industry(combined_text)
        role_score, role_matches = self._score_role(title, description)
        eligibility_score, eligibility_matches = self._score_eligibility(eligibility_text)
        visa_score, visa_status, visa_keywords = self._score_visa(combined_text, location=location)
        
        # ── WEIGHTED SUM ──────────────────────────────────────────────────────
        total_score = (
            (ai_score        * weights.get('ai_semantic', 0) / 100) +
            (tech_score      * weights.get('technical',   0) / 100) +
            (culture_score   * weights.get('culture',     0) / 100) +
            (industry_score  * weights.get('industry',    0) / 100) +
            (role_score      * weights.get('role',        0) / 100) +
            (eligibility_score * weights.get('eligibility', 0) / 100) +
            (visa_score      * weights.get('visa',        0) / 100)
        )
        
        # ── MULTIPLIERS ───────────────────────────────────────────────────────
        # Location: multiplicative penalty for non-preferred geography
        location_ok, location_penalty, location_flag = self._assess_location(location)
        total_score *= location_penalty
        
        # Seniority: HARD GATE for management/overly-senior roles
        seniority_ok, seniority_flag, seniority_penalty = self._assess_seniority(title, description)
        total_score *= seniority_penalty

        # SCORE_DEBUG: log every component for manual calibration
        if SCORE_DEBUG:
            logger.debug(
                f"[SCORE_DEBUG] {job_data.get('title', '?')} @ {company}\n"
                f"  ai={ai_score:.1f}(active={ai_active}, method={ai_details.get('method')}) "
                f"tech={tech_score:.1f} cult={culture_score:.1f} "
                f"ind={industry_score:.1f} role={role_score:.1f} "
                f"elig={eligibility_score:.1f} visa={visa_score:.1f}\n"
                f"  weights={weights}\n"
                f"  loc_penalty={location_penalty}({location_flag}) "
                f"snr_penalty={seniority_penalty}({seniority_flag})\n"
                f"  → TOTAL={total_score:.1f}"
            )
        
        # 🔍 DEEP COMPANY RESEARCH FOR TOP MATCHES (75%+)
        company_research = None
        if total_score >= 75 and self.company_researcher:
            logger.info(f"🎯 High match detected ({total_score:.1f}%) - researching {company}...")
            try:
                company_research = self.company_researcher.research_company(
                    company_name=company,
                    company_url=job_data.get('company_url')
                )
                
                # Apply research-based score adjustment
                if company_research.get('fit_score_adjustment'):
                    adjustment = company_research['fit_score_adjustment']
                    logger.info(f"  Adjusting score by {adjustment:+.1f}% based on company research")
                    total_score = max(0, min(100, total_score + adjustment))
            except Exception as e:
                logger.warning(f"Company research failed for {company}: {e}")
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            tech_matches, industry_matches, role_matches, eligibility_matches,
            visa_status, location_ok, seniority_ok, total_score, ai_score, ai_details
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
                'culture': round(culture_score, 1),
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
        Score technical stack match (0-100) — pure skill-keyword signal.
        Culture boost/penalty signals are handled separately in _score_culture().
        """
        matches = []
        eligibility_matches = []

        for skill in self.all_skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if eligibility_text and re.search(pattern, eligibility_text, re.IGNORECASE):
                eligibility_matches.append(skill)
                matches.append(skill)
            elif re.search(pattern, text, re.IGNORECASE):
                matches.append(skill)

        # Also check profile keyword boost list for extra signal
        kw_cfg = HARVEY_PROFILE.get("keywords", {})
        for kw in kw_cfg.get("boost", []):
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, text, re.IGNORECASE) and kw.lower() not in matches:
                matches.append(kw.lower())

        num_matches = len(matches)
        num_eligibility = len(eligibility_matches)

        if num_matches >= 10:
            score = 100
        elif num_matches >= 6:
            score = 80 + (num_matches - 6) * 5
        elif num_matches >= 3:
            score = 50 + (num_matches - 3) * 10
        elif num_matches > 0:
            score = 30 + num_matches * 10
        else:
            score = 0.0

        # Bonus for skills appearing in explicit requirements section
        if num_eligibility >= 3:
            score = min(100, score + 10)

        return float(min(score, 100)), matches

    def _score_culture(self, text: str) -> float:
        """
        Score culture / environment fit (0-100) as an explicit component.

        Base = 50 (neutral — no culture signal either way).
        Each boost keyword   → +8  (capped at 100)
        Each penalty keyword → -15 (floored at 0)

        Using 50 as neutral means jobs with zero culture signal score the
        middle of the range, which is appropriate — absence of startup/
        impact language is not a negative for all jobs.
        """
        culture_cfg = HARVEY_PROFILE.get("culture_signals", {})
        kw_cfg = HARVEY_PROFILE.get("keywords", {})

        boost_kws   = [k.lower() for k in culture_cfg.get("boost", [])]
        penalty_kws = [k.lower() for k in culture_cfg.get("penalise", [])]
        hard_excl   = [k.lower() for k in kw_cfg.get("penalise", [])]  # e.g. "10+ years"

        boost_hits = sum(
            1 for kw in boost_kws
            if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)
        )
        penalty_hits = sum(
            1 for kw in (penalty_kws + hard_excl)
            if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)
        )

        score = 50.0 + boost_hits * 8 - penalty_hits * 15
        return float(max(0.0, min(100.0, score)))

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
        # Description match: full points
        # Title-only match: reduced points
        base_score = 0
        if description_matches:
            # Description mentions = strong signal
            base_score = 90 if len(description_matches) >= 2 else 80
        elif title_matches:
            # Title only = weaker signal
            base_score = 60
        
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
        """
        if not eligibility_text:
            return 50.0, {'status': 'no_requirements_found'}  # Neutral if no requirements listed
        
        matches = {
            'experience_match': False,
            'skills_in_requirements': [],
            'concerns': []
        }
        
        # Check experience requirements
        # Harvey has 3-4 years, so look for: 2-5 years, 3+ years, 4+ years
        exp_patterns = [
            r'(\d+)\s*[-–to]+\s*(\d+)\s*years',  # Range: 2-5 years
            r'(\d+)\+?\s*years'  # Minimum: 3+ years
        ]
        
        for pattern in exp_patterns:
            matches_found = re.findall(pattern, eligibility_text.lower())
            for match in matches_found:
                if isinstance(match, tuple):
                    # Range match
                    min_years = int(match[0])
                    max_years = int(match[1]) if match[1] else min_years
                    
                    # Harvey has 3-4 years
                    if min_years <= 4 and max_years >= 3:
                        matches['experience_match'] = True
                    elif min_years >= 6:
                        matches['concerns'].append(f'requires_{min_years}+_years')
                else:
                    # Single number match
                    years = int(match)
                    if 2 <= years <= 5:
                        matches['experience_match'] = True
                    elif years >= 6:
                        matches['concerns'].append(f'requires_{years}+_years')
        
        # Check for Harvey's skills in requirements
        for skill in self.all_skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, eligibility_text, re.IGNORECASE):
                matches['skills_in_requirements'].append(skill)
        
        # Calculate score
        score = 50  # Base score
        
        # Experience match: +30 points
        if matches['experience_match']:
            score += 30
        
        # Skills in requirements: +20 points for 3+ matches
        if len(matches['skills_in_requirements']) >= 3:
            score += 20
        elif len(matches['skills_in_requirements']) >= 1:
            score += 10
        
        # Concerns: -40 points for each
        score -= len(matches['concerns']) * 40
        
        return max(0, min(100, score)), matches
    
    def _score_visa(self, text: str, location: str = '') -> Tuple[float, str, List[str]]:
        """
        Score visa friendliness (0-100).
        Branches on HARVEY_PROFILE["location"]["primary_market"]:
          - AU:   skip sponsorship checks — Harvey is an AU citizen in AU
          - US:   strict E-3/sponsorship filter
          - BOTH/GLOBAL: flag negative keywords but don't auto-exclude (0.85× multiplier)
        Returns: (score, status, keywords_found)
        """
        _loc_cfg = HARVEY_PROFILE.get("location", {})
        primary_market = (
            _loc_cfg.get("primary_market", "BOTH")
            if isinstance(_loc_cfg, dict)
            else "BOTH"
        )

        positive_found = []
        negative_found = []
        ambiguous_found = []

        ambiguous_negatives = {
            'must be authorized', 'authorized to work', 'already authorized',
            'currently authorized', 'require current work authorization',
            'must already have work authorization',
        }

        # AU citizen roles outside the US never need US visa sponsorship
        non_us_kw = [
            'australia', 'melbourne', 'sydney', 'brisbane', 'gold coast', 'canberra',
            'byron', 'united kingdom', 'london', 'ireland', 'dublin', 'netherlands',
            'amsterdam', 'germany', 'berlin', 'france', 'paris', 'portugal', 'lisbon',
            'spain', 'barcelona', 'canada', 'toronto', 'vancouver', 'singapore',
            'europe', 'remote',
            # Middle East
            'dubai', 'abu dhabi', 'united arab emirates', 'uae', 'tel aviv', 'israel',
            'middle east', 'mena',
            # Latin America
            'mexico', 'colombia', 'argentina', 'uruguay', 'medellin', 'buenos aires',
            'bogota', 'montevideo', 'latin america', 'latam',
            # EU expanded
            'stockholm', 'copenhagen', 'vienna', 'zurich', 'munich', 'brussels',
            'lisbon', 'barcelona',
        ]
        is_non_us = any(kw in (location or '').lower() for kw in non_us_kw)

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

        # --- Branch on primary_market ---
        if primary_market == 'AU' or is_non_us:
            # AU/EU/CA/SG — Harvey can work freely; sponsorship text irrelevant
            return 85.0, 'au_citizen_ok', []

        if primary_market == 'US':
            # Strict US filter
            if negative_found:
                return 0.0, 'excluded', negative_found
            if positive_found:
                score = 100.0 if any('e-3' in k or 'e3' in k for k in positive_found) else 80.0
                return score, 'explicit', positive_found
            if ambiguous_found:
                return 50.0, 'none', ambiguous_found
            return 50.0, 'none', []

        # BOTH / GLOBAL — flag but don't hard-exclude
        if negative_found:
            # Reduce score but don't zero out — worth verifying manually
            return 30.0, 'flagged', negative_found
        if positive_found:
            score = 100.0 if any('e-3' in k or 'e3' in k for k in positive_found) else 80.0
            return score, 'explicit', positive_found
        if ambiguous_found:
            return 55.0, 'ambiguous', ambiguous_found
        return 60.0, 'none', []

    def _assess_location(self, location: str) -> Tuple[bool, float, str]:
        """
        Assess location and return (is_ok, penalty_multiplier, flag).
        Tiers driven by HARVEY_PROFILE["location"]["preferred_regions"]:
          - index 0+1 (AU + Remote): 1.0 — no penalty
          - index 2+   (US, EU):     0.9 — small penalty
          - unknown geography:        0.75
        Also reads config/locations.json for specific city names.
        """
        if not location:
            return True, 1.0, 'unknown'

        location_lower = location.lower()

        # Remote always wins — digital nomad / anywhere keywords
        remote_keywords = ['remote', 'work from home', 'wfh', 'anywhere', 'distributed', 'worldwide', 'global']
        if any(kw in location_lower for kw in remote_keywords):
            return True, 1.0, 'remote'

        # Build city/region sets from profile preferred_regions
        tier1_terms: set = set()
        tier2_terms: set = set()
        tier3_terms: set = set()
        try:
            _loc_cfg = HARVEY_PROFILE.get("location", {})
            # Handle both dict-form (new profile) and legacy string
            if isinstance(_loc_cfg, dict):
                regions = _loc_cfg.get("preferred_regions", [])
            else:
                regions = []
            for i, region in enumerate(regions):
                region_name = region.get("region", "").lower()
                cities = [c.lower() for c in region.get("cities", [])]
                if i < 3:   # AU (0) + Remote (1) + EU (2) → tier 1
                    tier1_terms.add(region_name)
                    tier1_terms.update(cities)
                elif i < 6: # Middle East (3) + LatAm (4) + Asia Pacific (5) → tier 2
                    tier2_terms.add(region_name)
                    tier2_terms.update(cities)
                else:        # United States (6) → tier 3
                    tier3_terms.add(region_name)
                    tier3_terms.update(cities)
        except Exception:
            pass

        # Supplement with config/locations.json (specific LinkedIn-friendly city names)
        try:
            import json as _json
            _cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'locations.json')
            with open(_cfg_path) as _f:
                _locs = _json.load(_f)
            for _loc in _locs:
                if not _loc.get('enabled'):
                    continue
                name = _loc['name'].lower()
                t = _loc.get('tier', 3)
                if t == 1:
                    tier1_terms.add(name)
                elif t == 2:
                    tier2_terms.add(name)
                else:
                    tier3_terms.add(name)
        except Exception:
            pass

        # Tier-1 match → full score
        if any(t and (t in location_lower or location_lower in t) for t in tier1_terms):
            return True, 1.0, 'preferred_tier1'

        # Tier-2 match → 0.92 multiplier (Middle East / LatAm / Asia Pacific)
        if any(t and (t in location_lower or location_lower in t) for t in tier2_terms):
            return True, 0.92, 'preferred_tier2'

        # Tier-3 match → 0.82 multiplier (US cities — still worth seeing but lower priority)
        # BUT: if the job is freelance/contract/remote it gets bumped to tier-1 (handled above)
        if any(t and (t in location_lower or location_lower in t) for t in tier3_terms):
            return True, 0.82, 'preferred_tier3_us'

        # Country-level fallbacks so broad strings like "United Kingdom" still pass
        _country_kws = [
            (['australia', ' vic', ' nsw', ' qld', ' act', 'perth', 'adelaide'], 'au', 1.0),
            (['united kingdom', 'england', 'scotland', 'ireland', 'netherlands',
              'germany', 'france', 'spain', 'portugal', 'sweden', 'norway', 'denmark',
              'europe', 'amsterdam', 'berlin', 'london', 'dublin', 'lisbon', 'paris',
              'barcelona', 'zurich', 'munich', 'brussels', 'vienna', 'stockholm',
              'copenhagen'], 'eu', 1.0),
            (['dubai', 'abu dhabi', 'united arab emirates', 'uae', 'tel aviv', 'israel',
              'middle east', 'mena'], 'mena', 0.92),
            (['mexico', 'colombia', 'argentina', 'uruguay', 'brazil', 'chile', 'peru',
              'latin america', 'latam', 'south america', 'central america',
              'medellin', 'buenos aires', 'bogota', 'santiago', 'lima'], 'latam', 0.92),
            (['singapore', 'hong kong'], 'apac', 0.92),
            (['canada', 'ontario', 'british columbia', 'toronto', 'vancouver', 'montreal'], 'ca', 0.92),
            (['united states', ', us', ', usa', 'california', 'new york', 'san francisco',
              'seattle', 'chicago', 'boston', 'denver', 'atlanta', 'miami', 'portland'], 'us', 0.82),
        ]
        for kws, flag, multiplier in _country_kws:
            if any(kw in location_lower for kw in kws):
                return True, multiplier, flag

        return False, 0.75, 'outside'
    
    def _assess_seniority(self, title: str, description: str) -> Tuple[bool, str, float]:
        """
        Assess seniority; return (ok_to_pursue, flag, penalty_multiplier).

        HARD GATE (multiplier = 0.0) — title-level checks only (low false-positive risk):
          - Explicit management/leadership title keywords in the JOB TITLE
        SOFT PENALTY:
          - Experience requirement of 8+ years in a clear requirements context → 0.3
          - Experience requirement of 6–7 years → 0.85
          - "Senior" IC title in title → 1.0 (Harvey is already operating here)
        NOTE: Management keywords are intentionally checked against the TITLE only.
        Descriptions routinely say "report to engineering manager" or "work alongside
        a VP" — matching those would incorrectly gate perfectly good IC roles.
        """
        title_lower = title.lower()
        combined    = f"{title} {description}".lower()

        # ── HARD GATE: management title keywords (title-only) ─────────────────
        _profile_exclude = [e.lower() for e in HARVEY_PROFILE.get("seniority", {}).get("exclude", [])]
        _default_exclude = [
            'staff engineer', 'principal engineer', 'head of engineering',
            'chief', 'cto', 'vp of', 'vice president', 'engineering manager',
            'people manager', 'team manager',
        ]
        exec_keywords = list(set(_profile_exclude + _default_exclude))

        for keyword in exec_keywords:
            if keyword in title_lower:
                return False, 'leadership', 0.0  # HARD GATE — title only

        # "team lead" is management; "tech lead" is IC — title check only
        if re.search(r'\bteam lead\b', title_lower):
            return False, 'team_lead', 0.0  # HARD GATE

        # ── EXPERIENCE CEILING: look for clear requirement phrases only ────────
        # Match patterns like: "8+ years experience", "minimum 8 years",
        # "requires 8 years", "at least 8 years of experience"
        # Deliberately NOT matching bare "8 years" which fires on company age,
        # team size, product lifespan etc. in the general description body.
        exp_req_patterns = [
            r'(\d+)\+\s*years',                                 # "8+ years"
            r'(\d+)\s*years\s+(?:of\s+)?(?:experience|exp\b)', # "8 years experience"
            r'(?:minimum|at\s+least|require[sd]?)\s+(\d+)\s*years', # "requires 8 years"
        ]
        req_years = []
        for pat in exp_req_patterns:
            for m in re.findall(pat, combined):
                try:
                    req_years.append(int(m))
                except (ValueError, TypeError):
                    pass

        max_years = max(req_years, default=0)
        if max_years >= 8:
            return False, 'years_8_plus', 0.3   # Heavy penalty — too senior, but not zero
        if max_years >= 6:
            return True, 'years_6_plus', 0.85   # Stretch — slight penalty

        # Senior IC title is fine (~4 years; Harvey is already at this level)
        if re.search(r'\bsenior\b', title_lower):
            return True, 'senior_ic', 1.0

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
        ai_details: Dict[str, Any] = None  # type: ignore[assignment]
    ) -> str:
        """Generate concise 1-2 sentence reasoning for why Harvey is a good fit."""

        all_terms = ' '.join([*tech_matches, *role_matches, *industry_matches]).lower()

        is_ml         = any(kw in all_terms for kw in ['machine learning', 'ml', 'ai', 'nlp', 'pytorch', 'deep learning', 'llm', 'rag'])
        is_geospatial = any(kw in all_terms for kw in ['geospatial', 'maplibre', 'pmtiles', 'spatial', 'gis', 'mapping'])
        is_carbon     = any(kw in all_terms for kw in ['carbon', 'climate', 'ecology', 'sustainability', 'esg', 'green'])
        is_ios        = any(kw in all_terms for kw in ['swift', 'ios', 'swiftui', 'mobile', 'xcode'])
        is_backend    = any(kw in all_terms for kw in ['backend', 'api', 'server', 'database', 'microservices', 'rest', 'python'])
        is_fullstack  = any(kw in all_terms for kw in ['fullstack', 'full stack', 'react', 'frontend', 'typescript'])
        is_energy     = any(kw in all_terms for kw in ['energy', 'aemo', 'renewables', 'utilities', 'market operator'])
        is_fashion    = any(kw in all_terms for kw in ['fashion', 'apparel', 'shopify', 'ecommerce', 'retail'])

        if total_score >= 75:
            if is_geospatial or is_carbon:
                return ("Direct match: Harvey is currently building geospatial ML pipelines and "
                        "carbon sequestration research systems at ArborMeta, consulting the Australian "
                        "government — this role sits exactly in his wheelhouse.")
            elif is_ml:
                return ("Strong match: Harvey's current ML Engineer role at ArborMeta (spatial data "
                        "pipelines, ecological AI) plus his iOS ML work at FibreTrace makes him a "
                        "compelling fit for this ML challenge.")
            elif is_ios:
                return ("Excellent fit: Harvey built a full SwiftUI product-passport app at FibreTrace "
                        "end-to-end with on-device CoreML models, anomaly detection, and CEO sign-off "
                        "— strong iOS production experience.")
            elif is_backend:
                return ("Solid match: Harvey engineers production backend systems at ArborMeta and "
                        "previously at Friday Technologies and AEMO, with Python, C, PostgreSQL, and "
                        "AWS in real-world high-throughput contexts.")
            elif is_fullstack:
                return ("Great fit: Harvey builds full-stack at ArborMeta (React + MapLibre + "
                        "PostgreSQL) and at Step One Clothing (NLP search + Shopify), combining "
                        "strong frontend and backend depth.")
            elif is_energy:
                return ("Relevant experience: Harvey built Python analytics, C parsers, and C# "
                        "microservices at AEMO over large NEM/MMS datasets — directly applicable "
                        "to energy market engineering challenges.")
            else:
                return ("Strong candidate: Harvey's production experience spans ML pipelines, "
                        "geospatial systems, iOS, and backend engineering across startups and "
                        "government consulting.")

        elif total_score >= 50:
            if is_geospatial or is_carbon:
                return ("Good overlap: Harvey's geospatial and carbon research at ArborMeta gives "
                        "him a head start, even if the stack differs slightly.")
            elif is_ml:
                return ("Transferable: Harvey's ML engineering at ArborMeta and AI work at Friday "
                        "Technologies provide relevant pipeline and model deployment experience.")
            elif is_ios:
                return ("Relevant iOS background: Harvey shipped a production SwiftUI app at "
                        "FibreTrace with CoreML — solid foundation for this mobile role.")
            elif is_backend or is_fullstack:
                return ("Relevant background: Harvey's Python/PostgreSQL backend work at ArborMeta "
                        "and AEMO covers the core of what this role demands.")
            elif is_fashion:
                return ("Domain familiarity: Harvey contracts at Step One Clothing building "
                        "AI-powered search and Shopify experiences — practical retail-tech background.")
            else:
                tech_str = tech_matches[0] if tech_matches else "this stack"
                return (f"Decent match: Harvey's production systems background gives him a solid "
                        f"starting point for working with {tech_str}.")

        else:
            if visa_status == 'excluded':
                return ("Potential blocker: This US role doesn't mention E-3 sponsorship — "
                        "worth confirming before applying.")
            elif not seniority_ok:
                return ("Reach opportunity: Role targets more senior candidates, but Harvey's "
                        "breadth across ML, geospatial, and backend may still resonate.")
            else:
                return ("Stretch role: Stack differs from Harvey's core work, but his "
                        "adaptability and production experience make it worth a look.")


# Convenience function
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
