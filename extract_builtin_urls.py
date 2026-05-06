#!/usr/bin/env python3
"""
Extract actual application URLs from BuiltIn jobs
Parses the page to find the real Greenhouse/Lever links
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.models import Database, Job
import requests
from bs4 import BeautifulSoup
import re

def extract_application_url(builtin_url):
    """Extract the actual application URL from BuiltIn job page"""
    
    try:
        response = requests.get(builtin_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        if response.status_code != 200:
            return None, 'error'
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for apply button/link in HTML
        # BuiltIn often has the real URL in the page source
        
        # Method 1: Look for greenhouse/lever URLs in any links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            if 'greenhouse' in href.lower():
                return href, 'greenhouse'
            elif 'lever' in href.lower():
                return href, 'lever'
        
        # Method 2: Look in script tags for URLs
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                greenhouse_match = re.search(r'(https?://[^"\']*greenhouse[^"\']*)', script.string)
                if greenhouse_match:
                    return greenhouse_match.group(1), 'greenhouse'
                
                lever_match = re.search(r'(https?://[^"\']*lever\.co[^"\']*)', script.string)
                if lever_match:
                    return lever_match.group(1), 'lever'
        
        # Method 3: Look for apply button data attributes
        apply_buttons = soup.find_all(['a', 'button'], class_=re.compile(r'apply', re.I))
        for btn in apply_buttons:
            for attr in ['data-url', 'data-apply-url', 'data-href', 'href']:
                url = btn.get(attr, '')
                if url and ('greenhouse' in url.lower() or 'lever' in url.lower()):
                    platform = 'greenhouse' if 'greenhouse' in url.lower() else 'lever'
                    return url, platform
        
        return None, 'not_found'
        
    except Exception as e:
        print(f"   Error: {e}")
        return None, 'error'

def main():
    db = Database()
    session = db.get_session()
    
    # Get top BuiltIn jobs
    jobs = session.query(Job).filter(
        Job.source == 'builtin_nyc',
        Job.applied == False
    ).order_by(Job.fit_score.desc()).limit(20).all()
    
    print("=" * 70)
    print("🔍 Extracting Application URLs from BuiltIn Jobs")
    print("=" * 70)
    print(f"\nAnalyzing {len(jobs)} BuiltIn jobs...")
    
    results = {
        'greenhouse': [],
        'lever': [],
        'not_found': [],
        'error': []
    }
    
    for i, job in enumerate(jobs, 1):
        print(f"\n[{i}/{len(jobs)}] {job.title}")
        print(f"   BuiltIn URL: {job.url}")
        
        app_url, platform = extract_application_url(job.url)
        
        if app_url:
            print(f"   ✅ Found {platform.upper()} URL:")
            print(f"   {app_url}")
            results[platform].append({
                'job': job,
                'application_url': app_url
            })
        else:
            print(f"   ⚠️  {platform}")
            results[platform].append({'job': job})
    
    # Print results
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    
    print(f"\n🟢 Greenhouse ({len(results['greenhouse'])} jobs):")
    for r in results['greenhouse']:
        print(f"   Job ID {r['job'].id}: {r['job'].title}")
        print(f"   → {r['application_url']}\n")
    
    print(f"\n🟢 Lever ({len(results['lever'])} jobs):")
    for r in results['lever']:
        print(f"   Job ID {r['job'].id}: {r['job'].title}")
        print(f"   → {r['application_url']}\n")
    
    print(f"\n⚠️  Not Found: {len(results['not_found'])} jobs")
    print(f"❌ Errors: {len(results['error'])} jobs")
    
    # Calculate percentage
    total = len(jobs)
    auto_submit_capable = len(results['greenhouse']) + len(results['lever'])
    percentage = (auto_submit_capable / total * 100) if total > 0 else 0
    
    print(f"\n" + "=" * 70)
    print(f"✅ {auto_submit_capable}/{total} jobs ({percentage:.1f}%) have extractable Greenhouse/Lever URLs!")
    print("=" * 70)
    
    if auto_submit_capable > 0:
        print("\n💡 Next Step: Update the scrapers to extract these URLs automatically")
    
    session.close()

if __name__ == "__main__":
    main()
