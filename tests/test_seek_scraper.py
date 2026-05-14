#!/usr/bin/env python3
"""
Test Seek scraper
"""
import sys
sys.path.insert(0, '/app')
from src.scrapers.seek import SeekScraper
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

def test_seek_scraper():
    """Test Seek scraper with Melbourne jobs"""
    print("\n" + "="*80)
    print("TESTING SEEK SCRAPER - MELBOURNE, AUSTRALIA")
    print("="*80 + "\n")
    
    scraper = SeekScraper()
    
    # Test with a few search terms
    test_terms = [
        "Machine Learning Engineer",
        "Python Developer",
        "Backend Engineer"
    ]
    
    print(f"Searching for {len(test_terms)} job types in Melbourne...\n")
    
    jobs = scraper.search_jobs(test_terms[:2], location="Melbourne VIC")
    
    print(f"\n{'='*80}")
    print(f"RESULTS: Found {len(jobs)} total jobs")
    print(f"{'='*80}\n")
    
    if jobs:
        print("Sample jobs:\n")
        for i, job in enumerate(jobs[:5], 1):
            print(f"{i}. {job['title']}")
            print(f"   Company: {job['company']}")
            print(f"   Location: {job['location']}")
            print(f"   Posted: {job.get('posted_date', 'N/A')}")
            print(f"   URL: {job['url']}")
            print(f"   Description snippet: {job['description'][:150]}...")
            print()
        
        # Test fetching a full description
        if jobs:
            print(f"\n{'='*80}")
            print("Testing full description fetch for first job...")
            print(f"{'='*80}\n")
            
            first_job = jobs[0]
            full_desc = scraper.fetch_single_job_description(first_job['url'])
            
            if full_desc:
                print(f"Full description ({len(full_desc)} chars):")
                print(f"{full_desc[:500]}...")
            else:
                print("Could not fetch full description")
    else:
        print("No jobs found. This could mean:")
        print("1. Seek's HTML structure has changed")
        print("2. Network/rate limiting issues")
        print("3. No jobs match the search criteria")
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_seek_scraper()
