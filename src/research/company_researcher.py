"""
Company Research Module
For high-scoring jobs (75%+), automatically research the company to determine cultural fit,
tech stack alignment, visa sponsorship likelihood, and potential red flags.
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from loguru import logger
import time
import re
from urllib.parse import urljoin, urlparse


class CompanyResearcher:
    """Researches companies for high-scoring job matches"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.timeout = 10
    
    def research_company(self, company_name: str, company_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Deep research on a company for cultural and technical fit.
        
        Args:
            company_name: Name of the company
            company_url: Optional company website URL
        
        Returns:
            Dictionary with research findings
        """
        logger.info(f"🔍 Researching {company_name}...")
        
        research = {
            'company_name': company_name,
            'researched': True,
            'fit_score_adjustment': 0,  # +/- points based on findings
            'insights': [],
            'tech_stack': [],
            'culture_signals': [],
            'visa_signals': [],
            'red_flags': [],
            'green_flags': [],
            'confidence': 'medium'  # low, medium, high
        }
        
        try:
            # 1. Try to find company website if not provided
            if not company_url:
                company_url = self._find_company_website(company_name)
            
            if not company_url:
                logger.debug(f"Could not find website for {company_name}")
                research['confidence'] = 'low'
                return research
            
            # 2. Scrape company website
            website_data = self._scrape_company_website(company_url)
            
            # 3. Analyze tech stack
            tech_analysis = self._analyze_tech_stack(website_data, company_name)
            research['tech_stack'] = tech_analysis['stack']
            research['insights'].extend(tech_analysis['insights'])
            
            # 4. Check visa/immigration signals
            visa_analysis = self._check_visa_signals(website_data, company_name)
            research['visa_signals'] = visa_analysis['signals']
            research['insights'].extend(visa_analysis['insights'])
            
            # 5. Analyze culture/values
            culture_analysis = self._analyze_culture(website_data, company_name)
            research['culture_signals'] = culture_analysis['signals']
            research['insights'].extend(culture_analysis['insights'])
            
            # 6. Check for red flags
            red_flags = self._detect_red_flags(website_data, company_name)
            research['red_flags'] = red_flags
            
            # 7. Check for green flags
            green_flags = self._detect_green_flags(website_data, company_name)
            research['green_flags'] = green_flags
            
            # 8. Calculate fit score adjustment
            adjustment = len(green_flags) * 2 - len(red_flags) * 3
            research['fit_score_adjustment'] = max(-10, min(10, adjustment))
            
            # 9. Set confidence based on data quality
            if len(research['insights']) >= 3:
                research['confidence'] = 'high'
            elif len(research['insights']) >= 1:
                research['confidence'] = 'medium'
            else:
                research['confidence'] = 'low'
            
            logger.info(f"✓ Research complete for {company_name} (confidence: {research['confidence']})")
            
        except Exception as e:
            logger.error(f"Error researching {company_name}: {e}")
            research['researched'] = False
            research['confidence'] = 'low'
        
        return research
    
    def _find_company_website(self, company_name: str) -> Optional[str]:
        """Try to find company website via simple heuristics"""
        # Clean company name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name).strip().lower()
        
        # Try common patterns
        common_domains = [
            f"https://www.{clean_name.replace(' ', '')}.com",
            f"https://{clean_name.replace(' ', '')}.com",
            f"https://www.{clean_name.replace(' ', '')}.ai",
            f"https://{clean_name.replace(' ', '')}.ai",
            f"https://www.{clean_name.replace(' ', '')}.io",
        ]
        
        for url in common_domains:
            try:
                response = requests.head(url, timeout=5, allow_redirects=True, headers=self.headers)
                if response.status_code == 200:
                    logger.debug(f"Found website: {url}")
                    return url
            except:
                continue
        
        return None
    
    def _scrape_company_website(self, url: str) -> Dict[str, Any]:
        """Scrape company website for key information"""
        data = {
            'url': url,
            'text': '',
            'links': [],
            'meta': {}
        }
        
        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get all text content
            data['text'] = soup.get_text(separator=' ', strip=True).lower()
            
            # Get relevant links (careers, about, team)
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                if any(keyword in href for keyword in ['career', 'about', 'team', 'culture', 'values', 'jobs']):
                    full_url = urljoin(url, link['href'])
                    data['links'].append(full_url)
            
            # Get meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                data['meta']['description'] = meta_desc.get('content', '')
            
            # Try to scrape careers/about pages if found
            for link in data['links'][:3]:  # Limit to 3 additional pages
                try:
                    time.sleep(1)  # Be polite
                    page_response = requests.get(link, timeout=self.timeout, headers=self.headers)
                    page_soup = BeautifulSoup(page_response.content, 'html.parser')
                    data['text'] += ' ' + page_soup.get_text(separator=' ', strip=True).lower()
                except:
                    continue
            
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
        
        return data
    
    def _analyze_tech_stack(self, website_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Analyze tech stack from website content"""
        text = website_data['text']
        
        # Tech keywords to look for
        tech_keywords = {
            'python': ['python', 'pytorch', 'tensorflow', 'scikit-learn', 'pandas', 'numpy'],
            'ml_tools': ['mlflow', 'airflow', 'kubeflow', 'sagemaker', 'vertex ai'],
            'cloud': ['aws', 'azure', 'gcp', 'google cloud', 'kubernetes', 'docker'],
            'databases': ['postgresql', 'postgres', 'mysql', 'mongodb', 'redis', 'snowflake'],
            'backend': ['fastapi', 'django', 'flask', 'node.js', 'go', 'rust', 'java'],
            'frontend': ['react', 'vue', 'angular', 'typescript'],
            'mobile': ['ios', 'swift', 'kotlin', 'react native', 'flutter']
        }
        
        stack = []
        insights = []
        
        for category, keywords in tech_keywords.items():
            found = [kw for kw in keywords if kw in text]
            if found:
                stack.extend(found)
                
                # Generate insights for Harvey's profile matches
                if category == 'python' and 'python' in found:
                    insights.append(f"Uses Python extensively - matches Harvey's primary language")
                if category == 'ml_tools' and any(tool in found for tool in ['mlflow', 'airflow', 'kubeflow']):
                    insights.append(f"ML infrastructure tools detected - aligns with Harvey's MLOps experience")
                if category == 'cloud' and any(cloud in found for cloud in ['aws', 'gcp']):
                    insights.append(f"Cloud-native - Harvey has experience deploying to production")
                if category == 'mobile' and 'ios' in found:
                    insights.append(f"iOS development - Harvey has Swift/iOS experience from Friday Technologies")
        
        return {
            'stack': list(set(stack)),
            'insights': insights
        }
    
    def _check_visa_signals(self, website_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Check for visa sponsorship signals"""
        text = website_data['text']
        
        visa_keywords = {
            'positive': [
                'visa sponsorship',
                'h1b sponsor',
                'international candidates',
                'work authorization',
                'global team',
                'remote international',
                'e3 visa',
                'tn visa',
                'immigration support'
            ],
            'negative': [
                'us citizen only',
                'no visa sponsorship',
                'must be authorized to work',
                'citizens only',
                'no sponsorship'
            ]
        }
        
        signals = []
        insights = []
        
        # Check positive signals
        for keyword in visa_keywords['positive']:
            if keyword in text:
                signals.append(f"✓ Mentions '{keyword}'")
                insights.append(f"Good fit: Company likely sponsors visas (found '{keyword}')")
        
        # Check negative signals
        for keyword in visa_keywords['negative']:
            if keyword in text:
                signals.append(f"✗ Warning: '{keyword}'")
                insights.append(f"Potential blocker: Found '{keyword}' on website - may not sponsor E3 visa")
        
        return {
            'signals': signals,
            'insights': insights
        }
    
    def _analyze_culture(self, website_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Analyze company culture signals"""
        text = website_data['text']
        
        culture_keywords = {
            'positive': [
                'work-life balance',
                'flexible hours',
                'remote-first',
                'learning budget',
                'professional development',
                'open source',
                'diversity',
                'inclusive',
                'transparent',
                'autonomous teams',
                'innovation',
                'research-driven',
                'publication'
            ],
            'concerning': [
                'rockstar',
                'ninja',
                'hustle',
                'work hard play hard',
                'fast-paced',
                'wear many hats'
            ]
        }
        
        signals = []
        insights = []
        
        # Check positive culture signals
        positive_count = sum(1 for kw in culture_keywords['positive'] if kw in text)
        if positive_count >= 3:
            signals.append(f"Strong culture fit signals ({positive_count} positive indicators)")
            insights.append(f"Cultural fit: Company values align well (mentions learning, flexibility, innovation)")
        
        # Check concerning signals
        concerning = [kw for kw in culture_keywords['concerning'] if kw in text]
        if concerning:
            signals.append(f"⚠️ Potential intensity: {', '.join(concerning)}")
        
        return {
            'signals': signals,
            'insights': insights
        }
    
    def _detect_red_flags(self, website_data: Dict[str, Any], company_name: str) -> list:
        """Detect potential red flags"""
        text = website_data['text']
        red_flags = []
        
        red_flag_patterns = {
            'outdated_tech': ['php 5', 'python 2', 'angular.js', 'jquery'],
            'burnout_signals': ['unlimited overtime', 'always on', '24/7 availability'],
            'poor_engineering': ['no testing', 'move fast break things', 'cowboy coding'],
        }
        
        for category, patterns in red_flag_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    red_flags.append(f"{category}: {pattern}")
        
        return red_flags
    
    def _detect_green_flags(self, website_data: Dict[str, Any], company_name: str) -> list:
        """Detect positive signals"""
        text = website_data['text']
        green_flags = []
        
        green_flag_patterns = {
            'strong_engineering': ['engineering blog', 'open source contributions', 'tech talks', 'conference'],
            'good_practices': ['ci/cd', 'automated testing', 'code review', 'pair programming'],
            'growth': ['series a', 'series b', 'well-funded', 'yc backed', 'y combinator'],
            'impact': ['climate tech', 'social impact', 'sustainability', 'mission-driven'],
        }
        
        for category, patterns in green_flag_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    green_flags.append(f"{category}: {pattern}")
        
        return list(set(green_flags))  # Remove duplicates
    
    def enhance_reasoning_with_research(self, base_reasoning: str, research: Dict[str, Any]) -> str:
        """Enhance AI reasoning with company research insights"""
        
        if not research.get('researched') or research.get('confidence') == 'low':
            return base_reasoning
        
        enhanced = base_reasoning + "\n\n**Company Research Insights:**\n"
        
        # Add key insights
        if research['insights']:
            for insight in research['insights'][:3]:  # Top 3 insights
                enhanced += f"- {insight}\n"
        
        # Add green flags
        if research['green_flags']:
            enhanced += f"\n**Positive Signals:** {', '.join([gf.split(': ')[1] for gf in research['green_flags'][:2]])}\n"
        
        # Add red flags (important!)
        if research['red_flags']:
            enhanced += f"\n**⚠️ Considerations:** {', '.join([rf.split(': ')[1] for rf in research['red_flags'][:2]])}\n"
        
        # Add fit score adjustment note
        if research['fit_score_adjustment'] > 0:
            enhanced += f"\n*Research suggests stronger fit than resume match alone (+{research['fit_score_adjustment']}% adjustment)*"
        elif research['fit_score_adjustment'] < 0:
            enhanced += f"\n*Some concerns identified ({research['fit_score_adjustment']}% adjustment)*"
        
        return enhanced
