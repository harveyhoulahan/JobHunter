"""
Configuration loader for scraping locations and job boards
"""
import os
import json
from typing import List, Dict
from loguru import logger


def load_scraping_locations() -> List[str]:
    """
    Load enabled scraping locations from config file.
    Returns list of location strings (e.g., ['New York, NY', 'Melbourne, AU'])
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'locations.json')
    
    # Default locations if no config exists
    default_locations = [
        {'name': 'New York, NY', 'country': 'US', 'enabled': True},
        {'name': 'Los Angeles, CA', 'country': 'US', 'enabled': True},
        {'name': 'San Francisco, CA', 'country': 'US', 'enabled': True},
        {'name': 'Seattle, WA', 'country': 'US', 'enabled': True},
        {'name': 'Austin, TX', 'country': 'US', 'enabled': True},
        {'name': 'Boston, MA', 'country': 'US', 'enabled': True},
        {'name': 'Remote', 'country': 'US', 'enabled': True}
    ]
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                locations_data = json.load(f)
        else:
            logger.info("No locations config found, using defaults")
            locations_data = default_locations
        
        # Filter to only enabled locations
        enabled = [loc['name'] for loc in locations_data if loc.get('enabled', True)]
        logger.info(f"Loaded {len(enabled)} enabled scraping locations")
        return enabled
        
    except Exception as e:
        logger.error(f"Error loading locations config: {e}, using defaults")
        return [loc['name'] for loc in default_locations if loc.get('enabled', True)]


def get_active_countries() -> List[str]:
    """
    Get list of active country codes from enabled locations.
    Used to determine which job boards to activate.
    Returns: List of ISO country codes (e.g., ['US', 'AU', 'UK'])
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'locations.json')
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                locations_data = json.load(f)
            
            # Get unique country codes from enabled locations
            countries = set()
            for loc in locations_data:
                if loc.get('enabled', True):
                    countries.add(loc.get('country', 'US'))
            
            return list(countries)
        else:
            return ['US']  # Default to US only
            
    except Exception as e:
        logger.error(f"Error getting active countries: {e}")
        return ['US']


def should_activate_job_board(board_name: str) -> bool:
    """
    Determine if a specific job board should be activated based on active countries.
    
    Args:
        board_name: Job board identifier ('seek', 'reed', 'indeed_au', etc.)
    
    Returns:
        Boolean indicating if the board should be activated
    """
    active_countries = get_active_countries()
    
    # Job board to country mapping
    board_countries = {
        'seek': ['AU'],           # Australia & NZ
        'reed': ['UK'],           # United Kingdom
        'indeed_uk': ['UK'],
        'indeed_au': ['AU'],
        'indeed_ca': ['CA'],
        # LinkedIn & YC are global — activate whenever ANY location is enabled
        'linkedin': ['US', 'AU', 'UK', 'CA', 'DE', 'NL', 'IE', 'PT', 'ES', 'FR', 'SG', 'GLOBAL'],
        'builtin': ['US'],
        'ycombinator': ['US', 'UK', 'CA', 'DE', 'NL', 'IE', 'SG', 'GLOBAL'],
        'yc_jobs':     ['US', 'UK', 'CA', 'DE', 'NL', 'IE', 'SG', 'GLOBAL'],
    }
    
    required_countries = board_countries.get(board_name, [])
    
    # Activate if any active country matches the board's countries
    return any(country in active_countries for country in required_countries)


def get_active_regions() -> List[str]:
    """
    Map active country codes to high-level region labels.
    Returns e.g. ['Europe', 'Latin America', 'Middle East', 'Australia', 'Global']
    """
    active_countries = get_active_countries()
    regions: List[str] = ['Global']  # always active

    eu_codes  = {'UK', 'DE', 'NL', 'IE', 'PT', 'ES', 'SE', 'DK', 'AT', 'CH', 'FR', 'BE', 'IT'}
    me_codes  = {'AE', 'IL', 'SA', 'QA', 'KW', 'BH'}
    latam_codes = {'MX', 'CO', 'AR', 'UY', 'BR', 'CL', 'PE'}
    au_codes  = {'AU', 'NZ'}
    apac_codes = {'SG', 'JP', 'KR', 'HK'}

    if any(c in active_countries for c in eu_codes):
        regions.append('Europe')
    if any(c in active_countries for c in me_codes):
        regions.append('Middle East')
    if any(c in active_countries for c in latam_codes):
        regions.append('Latin America')
    if any(c in active_countries for c in au_codes):
        regions.append('Australia')
    if any(c in active_countries for c in apac_codes):
        regions.append('Asia Pacific')
    if 'US' in active_countries:
        regions.append('United States')

    return regions
