#!/usr/bin/env python3
"""
Test BuiltIn Job Redirects
Check if BuiltIn jobs redirect to Greenhouse/Lever for auto-submit
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.models import Database, Job
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def check_redirect(job_url, authenticated=False):
    """Check where a BuiltIn job redirects to when you click Apply"""
    
    print(f"\n🔍 Testing: {job_url}")
    
    # Setup Chrome with user data to maintain login
    options = Options()
    # options.add_argument('--headless')  # Comment out to see browser
    
    # Use your browser profile to maintain login (macOS Chrome path)
    if authenticated:
        user_data_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
        options.add_argument(f'user-data-dir={user_data_dir}')
        options.add_argument('profile-directory=Default')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # Go to BuiltIn job page
        driver.get(job_url)
        time.sleep(3)  # Wait for page to load
        
        # Check if redirected to signup
        if 'auth/signup' in driver.current_url or 'login' in driver.current_url:
            print("   ⚠️  Requires authentication - please login manually")
            print("   Waiting 30 seconds for you to login...")
            time.sleep(30)  # Give user time to login
            driver.get(job_url)  # Go back to job page
            time.sleep(3)
        
        print("   ✅ Loaded BuiltIn page")
        
        # Try to find and click Apply button
        apply_selectors = [
            "a.apply-button",
            "a[href*='apply']",
            "button.apply",
            ".job-apply-button",
            "a.btn-primary"
        ]
        
        apply_clicked = False
        for selector in apply_selectors:
            try:
                apply_btn = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"   ✅ Found Apply button: {selector}")
                
                # Get the href if it's a link
                if apply_btn.tag_name == 'a':
                    redirect_url = apply_btn.get_attribute('href')
                    print(f"   🔗 Direct link to: {redirect_url}")
                    
                    # Check if it's Greenhouse/Lever
                    if 'greenhouse' in redirect_url.lower():
                        return 'greenhouse', redirect_url
                    elif 'lever' in redirect_url.lower():
                        return 'lever', redirect_url
                    else:
                        return 'other', redirect_url
                else:
                    # It's a button, click it
                    apply_btn.click()
                    apply_clicked = True
                    time.sleep(3)
                    break
            except:
                continue
        
        if apply_clicked:
            # Check the new URL after clicking
            final_url = driver.current_url
            print(f"   ✅ Redirected to: {final_url}")
            
            if 'greenhouse' in final_url.lower():
                return 'greenhouse', final_url
            elif 'lever' in final_url.lower():
                return 'lever', final_url
            else:
                return 'other', final_url
        else:
            print("   ⚠️  No Apply button found")
            return 'no_button', None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 'error', str(e)
    finally:
        driver.quit()

def main():
    db = Database()
    session = db.get_session()
    
    # Get top BuiltIn jobs
    jobs = session.query(Job).filter(
        Job.source == 'builtin_nyc',
        Job.applied == False
    ).order_by(Job.fit_score.desc()).limit(10).all()
    
    print("=" * 70)
    print("🧪 Testing BuiltIn Job Redirects")
    print("=" * 70)
    print(f"\nTesting {len(jobs)} BuiltIn jobs...")
    
    results = {
        'greenhouse': [],
        'lever': [],
        'other': [],
        'no_button': [],
        'error': []
    }
    
    for i, job in enumerate(jobs, 1):
        print(f"\n[{i}/{len(jobs)}] {job.title} at {job.company or 'Unknown'}")
        platform, url = check_redirect(job.url)
        
        results[platform].append({
            'job': job,
            'redirect_url': url
        })
        
        time.sleep(2)  # Be polite
    
    # Print results
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    
    print(f"\n🟢 Greenhouse ({len(results['greenhouse'])} jobs):")
    for r in results['greenhouse']:
        print(f"   - {r['job'].title}")
        print(f"     {r['redirect_url']}")
    
    print(f"\n🟢 Lever ({len(results['lever'])} jobs):")
    for r in results['lever']:
        print(f"   - {r['job'].title}")
        print(f"     {r['redirect_url']}")
    
    print(f"\n⚠️  Other Platforms ({len(results['other'])} jobs):")
    for r in results['other'][:5]:  # Show first 5
        print(f"   - {r['job'].title}")
        print(f"     {r['redirect_url']}")
    
    print(f"\n❌ No Apply Button ({len(results['no_button'])} jobs)")
    print(f"❌ Errors ({len(results['error'])} jobs)")
    
    # Calculate percentage
    total = len(jobs)
    auto_submit_capable = len(results['greenhouse']) + len(results['lever'])
    percentage = (auto_submit_capable / total * 100) if total > 0 else 0
    
    print(f"\n" + "=" * 70)
    print(f"✅ {auto_submit_capable}/{total} jobs ({percentage:.1f}%) are auto-submit capable!")
    print("=" * 70)
    
    session.close()

if __name__ == "__main__":
    main()
