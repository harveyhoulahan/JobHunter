"""
Safe Auto-Submit Integration
Automates job applications where legally permitted and effective

🟢 FULLY SUPPORTED (Auto-fill + Submit):
- ✅ Greenhouse ATS (Stripe, Airbnb, DoorDash, Robinhood, Coinbase)
- ✅ Lever ATS (Netflix, Uber, Spotify, GitHub, Cloudflare)
- ✅ Email applications (direct SMTP submission)

🟡 PARTIAL SUPPORT (Auto-fill only, manual submit):
- ⚠️ Workday (too complex, company-specific variations)
- ⚠️ Taleo (upload resume, manual fields)
- ⚠️ iCIMS (basic auto-fill)

🔴 NOT SUPPORTED:
- ❌ LinkedIn Easy Apply (ToS violation → account ban)
- ❌ Indeed (redirects to company sites, no real API)

STRATEGY:
1. Greenhouse/Lever: Full auto-submit (80% of tech startups)
2. Email: Full auto-submit (20% of roles)
3. Workday/Taleo: Resume upload + pause for review
4. Everything else: Manual application (with pre-filled cover letter)

PHILOSOPHY:
- Only automate where safe and effective
- Review mode by default (can be disabled)
- Quality > quantity (10 perfect apps > 100 spam)
- Track everything in database
"""

from typing import Dict, Any, Optional, List
from loguru import logger
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
from pathlib import Path


class AutoSubmitManager:
    """
    Manages automated job applications across multiple platforms
    
    Usage:
        submitter = AutoSubmitManager()
        result = submitter.submit_application(job_data, resume_path, cover_letter_path)
    """
    
    def __init__(self, headless: bool = False, review_mode: bool = True):
        """
        Args:
            headless: Run browser in headless mode
            review_mode: Stop before final submit for human review (RECOMMENDED)
        """
        self.headless = headless
        self.review_mode = review_mode
        self.driver = None
        
    def submit_application(
        self,
        job_data: Dict[str, Any],
        resume_path: str,
        cover_letter_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for auto-submission
        
        Returns:
            {
                'success': bool,
                'method': str,  # 'indeed_api', 'greenhouse', 'email', etc.
                'status': str,  # 'submitted', 'ready_for_review', 'failed'
                'confirmation': str,  # confirmation number if available
                'error': str  # if failed
            }
        """
        url = job_data.get('url', '')
        source = job_data.get('source', '').lower()
        
        # Route to appropriate handler
        if 'greenhouse.io' in url:
            return self._submit_greenhouse(job_data, resume_path, cover_letter_path)
        elif 'lever.co' in url:
            return self._submit_lever(job_data, resume_path, cover_letter_path)
        elif 'myworkdayjobs.com' in url:
            return self._submit_workday(job_data, resume_path, cover_letter_path)
        elif source == 'indeed':
            return self._submit_indeed(job_data, resume_path, cover_letter_path)
        elif self._is_email_application(job_data):
            return self._submit_email(job_data, resume_path, cover_letter_path)
        else:
            return {
                'success': False,
                'method': 'unsupported',
                'status': 'manual_required',
                'error': f"Platform not supported for auto-apply: {url}"
            }
    
    # ==================== GREENHOUSE ATS ====================
    
    def _submit_greenhouse(
        self,
        job_data: Dict[str, Any],
        resume_path: str,
        cover_letter_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-fill Greenhouse application
        Used by: Airbnb, Stripe, DoorDash, Robinhood, etc.
        """
        logger.info(f"Auto-filling Greenhouse application: {job_data.get('title')}")
        
        try:
            self._init_driver()
            self.driver.get(job_data['url'])
            
            # Wait for form to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "first_name"))
            )
            
            # Fill personal info
            self._fill_field_by_id("first_name", "Harvey")
            self._fill_field_by_id("last_name", "Houlahan")
            self._fill_field_by_id("email", "harveyhoulahan@outlook.com")
            self._fill_field_by_id("phone", "+1234567890")  # Update with real number
            
            # Upload resume
            resume_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file'][name='resume']")
            resume_input.send_keys(os.path.abspath(resume_path))
            
            # Wait for resume to process
            time.sleep(2)
            
            # Fill LinkedIn URL if available
            try:
                linkedin_field = self.driver.find_element(By.ID, "job_application_answers_attributes_0_text_value")
                linkedin_field.send_keys("https://linkedin.com/in/harveyhoulahan")
            except NoSuchElementException:
                pass
            
            # Cover letter (if field exists)
            if cover_letter_path:
                try:
                    cover_letter_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file'][name='cover_letter']")
                    cover_letter_input.send_keys(os.path.abspath(cover_letter_path))
                    time.sleep(1)
                except NoSuchElementException:
                    logger.debug("No cover letter field found")
            
            if self.review_mode:
                logger.info("🛑 REVIEW MODE: Application filled, awaiting manual submit")
                logger.info(f"Review at: {job_data['url']}")
                input("Press Enter after reviewing and submitting...")
                return {
                    'success': True,
                    'method': 'greenhouse',
                    'status': 'ready_for_review',
                    'message': 'Application auto-filled, manual review required'
                }
            else:
                # Find and click submit button
                submit_btn = self.driver.find_element(By.ID, "submit_app")
                submit_btn.click()
                
                time.sleep(3)
                
                return {
                    'success': True,
                    'method': 'greenhouse',
                    'status': 'submitted',
                    'confirmation': 'Application submitted via Greenhouse'
                }
                
        except Exception as e:
            logger.error(f"Greenhouse auto-submit failed: {e}")
            return {
                'success': False,
                'method': 'greenhouse',
                'status': 'failed',
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    # ==================== LEVER ATS ====================
    
    def _submit_lever(
        self,
        job_data: Dict[str, Any],
        resume_path: str,
        cover_letter_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-fill Lever application
        Used by: Netflix, Uber, Spotify, GitHub, etc.
        """
        logger.info(f"Auto-filling Lever application: {job_data.get('title')}")
        
        try:
            self._init_driver()
            self.driver.get(job_data['url'])
            
            # Click "Apply" button
            apply_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "template-btn-submit"))
            )
            apply_btn.click()
            
            # Wait for form
            time.sleep(2)
            
            # Fill name
            name_field = self.driver.find_element(By.CSS_SELECTOR, "input[name='name']")
            name_field.send_keys("Harvey J. Houlahan")
            
            # Fill email
            email_field = self.driver.find_element(By.CSS_SELECTOR, "input[name='email']")
            email_field.send_keys("harveyhoulahan@outlook.com")
            
            # Upload resume
            resume_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            resume_input.send_keys(os.path.abspath(resume_path))
            time.sleep(2)
            
            # LinkedIn URL
            try:
                linkedin_field = self.driver.find_element(By.CSS_SELECTOR, "input[name='urls[LinkedIn]']")
                linkedin_field.send_keys("https://linkedin.com/in/harveyhoulahan")
            except NoSuchElementException:
                pass
            
            if self.review_mode:
                logger.info("🛑 REVIEW MODE: Lever application filled, awaiting manual submit")
                input("Press Enter after reviewing and submitting...")
                return {
                    'success': True,
                    'method': 'lever',
                    'status': 'ready_for_review'
                }
            else:
                submit_btn = self.driver.find_element(By.CLASS_NAME, "template-btn-submit")
                submit_btn.click()
                time.sleep(3)
                
                return {
                    'success': True,
                    'method': 'lever',
                    'status': 'submitted'
                }
                
        except Exception as e:
            logger.error(f"Lever auto-submit failed: {e}")
            return {
                'success': False,
                'method': 'lever',
                'status': 'failed',
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    # ==================== WORKDAY ATS ====================
    
    def _submit_workday(
        self,
        job_data: Dict[str, Any],
        resume_path: str,
        cover_letter_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-fill Workday application
        Used by: Amazon, Google, Meta, Apple, etc.
        
        NOTE: Workday is VERY complex and varies by company.
        This is a basic implementation - may need company-specific customization.
        """
        logger.info(f"Auto-filling Workday application: {job_data.get('title')}")
        
        try:
            self._init_driver()
            self.driver.get(job_data['url'])
            
            # Click "Apply" button
            apply_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-automation-id='applyManually']"))
            )
            apply_btn.click()
            
            time.sleep(3)
            
            # Upload resume
            resume_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            resume_input.send_keys(os.path.abspath(resume_path))
            
            time.sleep(5)  # Workday takes time to parse resume
            
            logger.warning("Workday applications are complex - MANUAL REVIEW REQUIRED")
            logger.info("Resume uploaded, please complete remaining fields manually")
            
            # Always use review mode for Workday
            input("Press Enter after completing and submitting application...")
            
            return {
                'success': True,
                'method': 'workday',
                'status': 'ready_for_review',
                'message': 'Resume uploaded, manual completion required'
            }
                
        except Exception as e:
            logger.error(f"Workday auto-submit failed: {e}")
            return {
                'success': False,
                'method': 'workday',
                'status': 'failed',
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    # ==================== INDEED API ====================
    
    def _submit_indeed(
        self,
        job_data: Dict[str, Any],
        resume_path: str,
        cover_letter_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit via Indeed (using their official mechanisms where available)
        
        NOTE: Indeed doesn't have a public API for applications.
        This uses Selenium to interact with their "Apply Now" flow.
        """
        logger.info(f"Auto-filling Indeed application: {job_data.get('title')}")
        
        try:
            self._init_driver()
            self.driver.get(job_data['url'])
            
            # Check if "Apply Now" button exists
            try:
                apply_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "indeedApplyButton"))
                )
                apply_btn.click()
                time.sleep(2)
                
                # Indeed applications vary widely
                # Most require manual completion
                logger.info("Indeed application opened - manual completion required")
                input("Press Enter after completing application...")
                
                return {
                    'success': True,
                    'method': 'indeed',
                    'status': 'ready_for_review'
                }
            except TimeoutException:
                # Redirects to company site
                return {
                    'success': False,
                    'method': 'indeed',
                    'status': 'external_redirect',
                    'error': 'Job redirects to company website'
                }
                
        except Exception as e:
            logger.error(f"Indeed auto-submit failed: {e}")
            return {
                'success': False,
                'method': 'indeed',
                'status': 'failed',
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    # ==================== EMAIL APPLICATIONS ====================
    
    def _is_email_application(self, job_data: Dict[str, Any]) -> bool:
        """Check if job accepts email applications"""
        description = job_data.get('description', '').lower()
        return 'email' in description and any(word in description for word in ['apply via email', 'send resume to', 'email to apply'])
    
    def _submit_email(
        self,
        job_data: Dict[str, Any],
        resume_path: str,
        cover_letter_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send application via email
        
        Requires SMTP credentials in environment:
        - EMAIL_ADDRESS
        - EMAIL_PASSWORD
        - EMAIL_SMTP_SERVER (default: smtp.gmail.com)
        - EMAIL_SMTP_PORT (default: 587)
        """
        logger.info(f"Sending email application: {job_data.get('title')}")
        
        # Extract email from description
        import re
        description = job_data.get('description', '')
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', description)
        
        if not emails:
            return {
                'success': False,
                'method': 'email',
                'status': 'failed',
                'error': 'No email address found in job description'
            }
        
        recipient_email = emails[0]
        
        try:
            # Get SMTP credentials
            smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
            sender_email = os.getenv('EMAIL_ADDRESS')
            sender_password = os.getenv('EMAIL_PASSWORD')
            
            if not sender_email or not sender_password:
                raise ValueError("EMAIL_ADDRESS and EMAIL_PASSWORD must be set in environment")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"Application for {job_data.get('title')} - Harvey J. Houlahan"
            
            # Email body
            body = f"""Dear Hiring Manager,

I am writing to express my interest in the {job_data.get('title')} position at {job_data.get('company')}.

Please find attached my resume{' and cover letter' if cover_letter_path else ''} for your review.

I look forward to the opportunity to discuss how my experience can contribute to your team.

Best regards,
Harvey J. Houlahan
harveyhoulahan@outlook.com
"""
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach resume
            with open(resume_path, 'rb') as f:
                resume_attachment = MIMEApplication(f.read(), _subtype='pdf')
                resume_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(resume_path))
                msg.attach(resume_attachment)
            
            # Attach cover letter if provided
            if cover_letter_path and os.path.exists(cover_letter_path):
                with open(cover_letter_path, 'rb') as f:
                    cover_attachment = MIMEApplication(f.read(), _subtype='pdf')
                    cover_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(cover_letter_path))
                    msg.attach(cover_attachment)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email application sent to {recipient_email}")
            
            return {
                'success': True,
                'method': 'email',
                'status': 'submitted',
                'confirmation': f'Sent to {recipient_email}'
            }
            
        except Exception as e:
            logger.error(f"Email application failed: {e}")
            return {
                'success': False,
                'method': 'email',
                'status': 'failed',
                'error': str(e)
            }
    
    # ==================== HELPER METHODS ====================
    
    def _init_driver(self):
        """Initialize Selenium WebDriver"""
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def _fill_field_by_id(self, field_id: str, value: str):
        """Helper to fill a form field by ID"""
        try:
            field = self.driver.find_element(By.ID, field_id)
            field.clear()
            field.send_keys(value)
        except NoSuchElementException:
            logger.debug(f"Field {field_id} not found, skipping")


# ==================== INTEGRATION WITH MAIN WORKFLOW ====================

def auto_submit_high_scoring_jobs(
    jobs: List[Dict[str, Any]],
    applications_dir: str = 'applications',
    review_mode: bool = True
) -> Dict[str, Any]:
    """
    Automatically submit applications for high-scoring jobs
    
    Args:
        jobs: List of job dictionaries with prepared applications
        applications_dir: Directory containing generated CVs/cover letters
        review_mode: Pause before final submit for review (RECOMMENDED)
        
    Returns:
        Summary statistics
    """
    submitter = AutoSubmitManager(review_mode=review_mode)
    
    results = {
        'submitted': [],
        'ready_for_review': [],
        'failed': [],
        'unsupported': []
    }
    
    for job in jobs:
        job_id = job.get('id') or job.get('source_id')
        
        # Find corresponding resume/cover letter
        resume_path = None
        cover_letter_path = None
        
        # Search for generated files
        for file in Path(applications_dir).glob(f"*{job_id}*"):
            if 'resume' in file.name.lower() or 'cv' in file.name.lower():
                resume_path = str(file)
            elif 'cover_letter' in file.name.lower():
                cover_letter_path = str(file)
        
        if not resume_path:
            logger.warning(f"No resume found for job {job_id}, skipping")
            continue
        
        # Submit application
        result = submitter.submit_application(job, resume_path, cover_letter_path)
        
        # Categorize result
        status = result.get('status')
        if status == 'submitted':
            results['submitted'].append(job)
        elif status == 'ready_for_review':
            results['ready_for_review'].append(job)
        elif status == 'manual_required' or status == 'unsupported':
            results['unsupported'].append(job)
        else:
            results['failed'].append(job)
        
        # Rate limiting
        time.sleep(5)
    
    return results


if __name__ == "__main__":
    # Test the auto-submitter
    print("=" * 60)
    print("Auto-Submit Manager - Test Mode")
    print("=" * 60)
    
    test_job = {
        'title': 'Software Engineer',
        'company': 'Test Company',
        'url': 'https://boards.greenhouse.io/test/jobs/12345',
        'description': 'Test job description'
    }
    
    submitter = AutoSubmitManager(review_mode=True)
    print("\nTesting Greenhouse auto-fill...")
    print("NOTE: This is a test URL and will fail - replace with real job URL to test")
