"""
Gold Coast Lifestyle Job Scorer
For casual/part-time positions at wellness retreats, hospitality, and cool day jobs
Focus: Work-life balance, unique experiences, bougie/upscale environments
"""

from typing import Dict, Any, List
from loguru import logger


class GoldCoastJobScorer:
    """
    Scores Gold Coast casual/part-time jobs based on Harvey's lifestyle preferences
    
    Target jobs:
    - Wellness retreats (yoga instructor, retreat coordinator, guest services)
    - Boutique hotels & resorts (concierge, guest experience, events)
    - Upscale cafes & restaurants (barista, front of house, sommelier assistant)
    - Fitness & wellness centers (personal trainer, class instructor, wellness coach)
    - Experiential/event roles (surf instructor, tour guide, outdoor activities)
    - Creative/artisan shops (gallery assistant, design studio, concept stores)
    """
    
    def __init__(self):
        # Priority venues/companies on Gold Coast
        self.priority_venues = [
            # Wellness Retreats
            'gwinganna', 'golden door', 'soma', 'ikatan spa', 'billabong retreat',
            'Byron bay', 'hinterland', 'wellness sanctuary',
            
            # Boutique Hotels/Resorts
            'halcyon house', 'hamptons', 'q1', 'versace', 'sheraton', 
            'peppers', 'mantra', 'palazzo versace', 'the star',
            
            # Upscale Cafes/Dining
            'maman', 'rick shores', 'greenhouse canteen', 'hellenika',
            'babalou', 'paddock bakery', 'nomad', 'commune',
            
            # Fitness/Wellness
             'f45', 'barry\'s bootcamp', 'yoga', 'pilates', 'barre',
            'crossfit', 'climb', 'surf', 'soul cycle'
        ]
        
        # Ideal job types
        self.ideal_roles = [
            # Wellness/Retreat
            'retreat coordinator', 'wellness coordinator', 'guest services',
            'spa coordinator', 'yoga instructor', 'meditation', 'wellness coach',
            'holistic', 'lifestyle coordinator', 'retreat host',
            
            # Hospitality/Guest Experience  
            'concierge', 'guest experience', 'front of house', 'host',
            'guest relations', 'vip services', 'member services',
            
            # Food & Beverage
            'barista', 'bartender', 'sommelier', 'cafe', 'coffee',
            'mixologist', 'front of house', 'waiter', 'server',
            
            # Fitness/Activities
            'personal trainer', 'fitness instructor', 'group fitness',
            'surf instructor', 'yoga teacher', 'pilates instructor',
            'outdoor guide', 'adventure guide', 'dive instructor',
            
            # Creative/Retail
            'gallery assistant', 'boutique', 'concept store', 'design studio',
            'events coordinator', 'social media coordinator', 'content creator'
        ]
        
        # Desirable keywords
        self.desirable_keywords = [
            # Vibe
            'boutique', 'upscale', 'luxury', 'premium', 'high-end',
            'artisan', 'curated', 'bespoke', 'experiential', 'lifestyle',
            
            # Work style
            'casual', 'part-time', 'flexible', 'roster', 'shifts',
            'weekend', 'mornings', 'casual contract',
            
            # Environment
            'beachside', 'ocean view', 'hinterland', 'tropical',
            'outdoor', 'coastal', 'waterfront', 'wellness', 'retreat',
            
            # Culture
            'creative', 'collaborative', 'community', 'intimate',
            'small team', 'independent', 'passionate', 'values-driven'
        ]
        
        # Red flags (corporate, high-pressure, chain retail)
        self.red_flags = [
            'fast-paced corporate', 'high-volume', 'targets', 'kpis',
            'sales quotas', 'cold calling', 'telemarketing',
            'retail chain', 'franchise', 'big box',
            'night shift', 'graveyard', 'overnight', 'closing shift',
            'casino floor', 'pokies', 'gaming'
        ]
    
    def score_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a Gold Coast job listing
        
        Returns:
            {
                'fit_score': float (0-100),
                'reasoning': str,
                'category': str,
                'vibe_match': bool,
                'recommended': bool
            }
        """
        title = (job_data.get('title', '') or '').lower()
        company = (job_data.get('company', '') or '').lower()
        description = (job_data.get('description', '') or '').lower()
        location = (job_data.get('location', '') or '').lower()
        
        # Combine all text for analysis
        full_text = f"{title} {company} {description} {location}"
        
        # Initialize score components
        scores = {
            'venue_match': 0,      # 25 points - Priority venue/company
            'role_match': 0,       # 30 points - Ideal role type
            'vibe_match': 0,       # 20 points - Desirable keywords/vibe
            'work_style': 0,       # 15 points - Casual/part-time/flexible
            'location_bonus': 0,   # 10 points - Gold Coast/Hinterland
            'red_flag_penalty': 0  # -30 points - Corporate/high-pressure
        }
        
        # 1. Venue/Company Match (25 points)
        venue_matches = [v for v in self.priority_venues if v in full_text]
        if venue_matches:
            scores['venue_match'] = min(25, len(venue_matches) * 10)
        
        # 2. Role Match (30 points)
        role_matches = [r for r in self.ideal_roles if r in full_text]
        if role_matches:
            scores['role_match'] = min(30, len(role_matches) * 8)
        
        # 3. Vibe Match (20 points)
        vibe_matches = [k for k in self.desirable_keywords if k in full_text]
        if vibe_matches:
            scores['vibe_match'] = min(20, len(vibe_matches) * 3)
        
        # 4. Work Style (15 points)
        work_style_indicators = ['casual', 'part-time', 'part time', 'flexible', 'roster']
        work_style_matches = [w for w in work_style_indicators if w in full_text]
        if work_style_matches:
            scores['work_style'] = 15
        elif 'full-time' in full_text or 'full time' in full_text:
            scores['work_style'] = 5  # Still possible but not ideal
        
        # 5. Location Bonus (10 points)
        gold_coast_areas = ['gold coast', 'burleigh', 'currumbin', 'tallebudgera',
                           'miami', 'mermaid', 'broadbeach', 'surfers paradise',
                           'main beach', 'coolangatta', 'hinterland']
        if any(area in location for area in gold_coast_areas):
            scores['location_bonus'] = 10
        
        # 6. Red Flag Penalty (-30 points)
        red_flag_matches = [rf for rf in self.red_flags if rf in full_text]
        if red_flag_matches:
            scores['red_flag_penalty'] = -min(30, len(red_flag_matches) * 10)
        
        # Calculate total
        total_score = sum(scores.values())
        total_score = max(0, min(100, total_score))  # Clamp to 0-100
        
        # Determine category
        category = self._categorize_job(title, description, venue_matches, role_matches)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            total_score,
            venue_matches,
            role_matches,
            vibe_matches,
            work_style_matches,
            red_flag_matches,
            category
        )
        
        # Recommendation
        vibe_match = scores['vibe_match'] >= 10
        recommended = total_score >= 60 and not red_flag_matches
        
        return {
            'fit_score': round(total_score, 1),
            'reasoning': reasoning,
            'category': category,
            'vibe_match': vibe_match,
            'recommended': recommended,
            'breakdown': scores,
            'matches': {
                'venues': venue_matches[:5],
                'roles': role_matches[:5],
                'vibe': vibe_matches[:8]
            }
        }
    
    def _categorize_job(
        self,
        title: str,
        description: str,
        venue_matches: List[str],
        role_matches: List[str]
    ) -> str:
        """Categorize the job type"""
        text = f"{title} {description}".lower()
        
        if any(w in text for w in ['wellness', 'retreat', 'spa', 'holistic', 'yoga', 'meditation']):
            return 'Wellness & Retreats'
        elif any(w in text for w in ['hotel', 'resort', 'concierge', 'guest', 'hospitality']):
            return 'Boutique Hospitality'
        elif any(w in text for w in ['barista', 'cafe', 'coffee', 'bartender', 'restaurant']):
            return 'Food & Beverage'
        elif any(w in text for w in ['fitness', 'trainer', 'instructor', 'gym', 'studio']):
            return 'Fitness & Movement'
        elif any(w in text for w in ['surf', 'dive', 'outdoor', 'adventure', 'guide']):
            return 'Outdoor & Adventure'
        elif any(w in text for w in ['gallery', 'design', 'creative', 'boutique', 'concept']):
            return 'Creative & Retail'
        elif any(w in text for w in ['event', 'social', 'content', 'community']):
            return 'Events & Social'
        else:
            return 'General Hospitality'
    
    def _generate_reasoning(
        self,
        score: float,
        venue_matches: List[str],
        role_matches: List[str],
        vibe_matches: List[str],
        work_style_matches: List[str],
        red_flags: List[str],
        category: str
    ) -> str:
        """Generate concise reasoning in 3-4 sentences"""
        sentences = []
        
        # Sentence 1: Overall + category
        if score >= 75:
            intro = f"Excellent {category.lower()} opportunity at {score:.0f}%"
        elif score >= 60:
            intro = f"Solid {category.lower()} role at {score:.0f}%"
        elif score >= 40:
            intro = f"Moderate fit for {category.lower()} at {score:.0f}%"
        else:
            intro = f"Limited fit at {score:.0f}%"
        
        # Add key matches
        if venue_matches:
            intro += f" - matches priority venue ({venue_matches[0]})"
        elif role_matches:
            intro += f" - aligns as {role_matches[0]}"
        
        sentences.append(intro + ".")
        
        # Sentence 2: Work style
        if work_style_matches:
            sentences.append(f"Work style suits: {', '.join(work_style_matches[:3])}.")
        
        # Sentence 3: Vibe/environment
        if vibe_matches:
            sentences.append(f"Vibe indicators: {', '.join(vibe_matches[:4])}.")
        
        # Sentence 4: Red flags or bonus
        if red_flags:
            sentences.append(f"Concerns: {', '.join(red_flags[:2])} - may not align with lifestyle goals.")
        elif score >= 70:
            sentences.append("Strong match for Gold Coast lifestyle priorities.")
        
        return " ".join(sentences[:4])


# Convenience function
def score_goldcoast_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Score a Gold Coast lifestyle job"""
    scorer = GoldCoastJobScorer()
    return scorer.score_job(job_data)


if __name__ == "__main__":
    # Test examples
    test_jobs = [
        {
            'title': 'Wellness Retreat Coordinator',
            'company': 'Gwinganna Lifestyle Retreat',
            'description': 'Part-time role coordinating guest experiences at luxury wellness retreat. Flexible roster, beautiful hinterland location.',
            'location': 'Gold Coast Hinterland'
        },
        {
            'title': 'Barista - Boutique Cafe',
            'company': 'Paddock Bakery',
            'description': 'Casual barista position at artisan bakery. Weekend shifts, passionate about coffee and community.',
            'location': 'Burleigh Heads'
        },
        {
            'title': 'Retail Sales Associate',
            'company': 'Big Box Electronics',
            'description': 'Full-time sales role, KPI-driven, high-volume retail environment. Fast-paced with sales targets.',
            'location': 'Southport'
        }
    ]
    
    scorer = GoldCoastJobScorer()
    
    for job in test_jobs:
        print(f"\n{'='*70}")
        print(f"Job: {job['title']} at {job['company']}")
        print(f"{'='*70}")
        result = scorer.score_job(job)
        print(f"Score: {result['fit_score']}%")
        print(f"Category: {result['category']}")
        print(f"Recommended: {result['recommended']}")
        print(f"Reasoning: {result['reasoning']}")
        if result['matches']['venues']:
            print(f"Venue matches: {', '.join(result['matches']['venues'])}")
        if result['matches']['roles']:
            print(f"Role matches: {', '.join(result['matches']['roles'])}")
