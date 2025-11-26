"""
Alert delivery system
Sends email and SMS notifications for high-match jobs
"""
from typing import List, Dict, Any
from datetime import datetime
import os
from loguru import logger


class EmailAlerter:
    """Email alert sender"""
    
    def __init__(self, provider: str = "sendgrid"):
        self.provider = provider
        self.enabled = os.getenv('ENABLE_EMAIL_ALERTS', 'true').lower() == 'true'
        
        if provider == "sendgrid":
            self.api_key = os.getenv('SENDGRID_API_KEY')
            if self.enabled and not self.api_key:
                logger.warning("SendGrid API key not configured")
                self.enabled = False
        elif provider == "smtp":
            self.smtp_host = os.getenv('SMTP_HOST')
            self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
            self.smtp_user = os.getenv('SMTP_USERNAME')
            self.smtp_pass = os.getenv('SMTP_PASSWORD')
    
    def send_immediate_alert(self, job: Dict[str, Any], recipient: str) -> bool:
        """Send immediate alert for high-match job"""
        if not self.enabled:
            logger.info(f"Email alerts disabled. Would send alert for: {job.get('title')}")
            return False
        
        subject = f"🎯 High-Match Job: {job.get('title')} at {job.get('company')}"
        body = self._format_job_email(job, alert_type="immediate")
        
        return self._send_email(recipient, subject, body)
    
    def send_digest(self, jobs: List[Dict[str, Any]], recipient: str) -> bool:
        """Send daily digest of moderate-match jobs"""
        if not self.enabled:
            logger.info(f"Email alerts disabled. Would send digest with {len(jobs)} jobs")
            return False
        
        subject = f"📬 Daily Job Digest: {len(jobs)} New Opportunities"
        body = self._format_digest_email(jobs)
        
        return self._send_email(recipient, subject, body)
    
    def _format_job_email(self, job: Dict[str, Any], alert_type: str = "immediate") -> str:
        """Format single job for email"""
        fit_score = job.get('fit_score', 0)
        matches = job.get('matches', {})
        reasoning = job.get('reasoning', 'No reasoning available')
        
        tech_skills = ', '.join(matches.get('tech', [])[:8])
        industries = ', '.join(matches.get('industry', []))
        roles = ', '.join(matches.get('role', []))
        visa_status = job.get('visa_status', 'unknown')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0066cc;">{job.get('title', 'Untitled')}</h2>
            <h3 style="color: #333;">{job.get('company', 'Unknown Company')}</h3>
            
            <div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Fit Score: {fit_score}/100</h3>
                <p><strong>Technical Match:</strong> {tech_skills or 'None identified'}</p>
                <p><strong>Industry:</strong> {industries or 'General'}</p>
                <p><strong>Role:</strong> {roles or 'Various'}</p>
                <p><strong>Visa Status:</strong> {visa_status}</p>
            </div>
            
            <div style="margin: 20px 0;">
                <h4>Why this matches:</h4>
                <p>{reasoning}</p>
            </div>
            
            <div style="margin: 30px 0;">
                <a href="{job.get('url', '#')}" 
                   style="background: #0066cc; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Apply Now →
                </a>
            </div>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            
            <div style="font-size: 12px; color: #666;">
                <p><strong>Location:</strong> {job.get('location', 'Not specified')}</p>
                <p><strong>Posted:</strong> {job.get('posted_date', 'Recently')}</p>
                <p><strong>Source:</strong> {job.get('source', 'Unknown')}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_digest_email(self, jobs: List[Dict[str, Any]]) -> str:
        """Format multiple jobs for digest email"""
        job_items = ""
        
        for job in sorted(jobs, key=lambda x: x.get('fit_score', 0), reverse=True):
            fit_score = job.get('fit_score', 0)
            tech_skills = ', '.join(job.get('matches', {}).get('tech', [])[:5])
            
            job_items += f"""
            <div style="border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <h3 style="margin-top: 0;">
                    <a href="{job.get('url', '#')}" style="color: #0066cc; text-decoration: none;">
                        {job.get('title', 'Untitled')}
                    </a>
                </h3>
                <p><strong>{job.get('company', 'Unknown')}</strong> • {job.get('location', 'Location TBD')}</p>
                <p style="background: #f0f8ff; padding: 8px; border-radius: 3px; display: inline-block;">
                    Fit Score: {fit_score}/100
                </p>
                <p><strong>Key Skills:</strong> {tech_skills or 'Various'}</p>
                <p><em>{job.get('reasoning', '')[:150]}...</em></p>
                <a href="{job.get('url', '#')}" style="color: #0066cc;">View Details →</a>
            </div>
            """
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
            <h1 style="color: #0066cc;">Your Daily Job Digest</h1>
            <p style="font-size: 16px; color: #666;">
                {len(jobs)} new opportunities matched your profile
            </p>
            
            {job_items}
            
            <hr style="margin: 30px 0;">
            <p style="font-size: 12px; color: #666; text-align: center;">
                JobHunter • Automated Job Alerts for Harvey Houlahan
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _send_email(self, recipient: str, subject: str, html_body: str) -> bool:
        """Send email via configured provider"""
        try:
            if self.provider == "sendgrid":
                return self._send_via_sendgrid(recipient, subject, html_body)
            elif self.provider == "smtp":
                return self._send_via_smtp(recipient, subject, html_body)
            else:
                logger.error(f"Unknown email provider: {self.provider}")
                return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_via_sendgrid(self, recipient: str, subject: str, html_body: str) -> bool:
        """Send via SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=os.getenv('ALERT_EMAIL', recipient),
                to_emails=recipient,
                subject=subject,
                html_content=html_body
            )
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            logger.info(f"Email sent to {recipient}: {subject}")
            return response.status_code == 202
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False
    
    def _send_via_smtp(self, recipient: str, subject: str, html_body: str) -> bool:
        """Send via SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = recipient
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info(f"Email sent to {recipient}: {subject}")
            return True
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False


class SMSAlerter:
    """SMS alert sender via Twilio"""
    
    def __init__(self):
        self.enabled = os.getenv('ENABLE_SMS_ALERTS', 'false').lower() == 'true'
        
        if self.enabled:
            self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            self.from_number = os.getenv('TWILIO_FROM_NUMBER')
            
            if not all([self.account_sid, self.auth_token, self.from_number]):
                logger.warning("Twilio credentials not fully configured")
                self.enabled = False
    
    def send_alert(self, job: Dict[str, Any], recipient: str) -> bool:
        """Send SMS alert"""
        if not self.enabled:
            logger.info(f"SMS alerts disabled. Would send alert for: {job.get('title')}")
            return False
        
        message = self._format_sms(job)
        return self._send_sms(recipient, message)
    
    def _format_sms(self, job: Dict[str, Any]) -> str:
        """Format job for SMS (160 chars limit)"""
        fit_score = job.get('fit_score', 0)
        title = job.get('title', 'Job')[:40]
        company = job.get('company', 'Company')[:20]
        url = job.get('url', '')
        
        # Keep it short
        message = f"🎯 {fit_score}/100: {title} @ {company}\n{url}"
        return message[:160]
    
    def _send_sms(self, recipient: str, message: str) -> bool:
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            msg = client.messages.create(
                body=message,
                from_=self.from_number,
                to=recipient
            )
            
            logger.info(f"SMS sent to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Twilio error: {e}")
            return False


class AlertManager:
    """Manages all alert delivery"""
    
    def __init__(self, email_provider: str = None, db = None):
        """
        Initialize alert manager
        
        Args:
            email_provider: Email provider to use ('smtp' or 'sendgrid')
                          If None, uses EMAIL_PROVIDER from env or defaults to 'smtp'
            db: Database instance for tracking alerted jobs
        """
        # Default to smtp if not specified
        if email_provider is None:
            email_provider = os.getenv('EMAIL_PROVIDER', 'smtp')
        
        self.email = EmailAlerter(provider=email_provider)
        self.sms = SMSAlerter()
        self.db = db
    
    def send_alerts(self, jobs: List[Dict[str, Any]], thresholds: Dict[str, int]) -> Dict[str, int]:
        """
        Send appropriate alerts based on job scores
        Only sends alerts for jobs that haven't been alerted before
        
        Args:
            jobs: List of scored jobs
            thresholds: Dict with 'immediate' and 'digest' score thresholds
        
        Returns:
            Stats dict with counts of alerts sent
        """
        immediate_threshold = thresholds.get('immediate', 70)
        digest_threshold = thresholds.get('digest', 50)
        
        # Filter for jobs that haven't been alerted yet
        unalerted_jobs = []
        for job in jobs:
            job_id = job.get('id')
            if job_id and self.db:
                # Check if already alerted
                session = self.db.get_session()
                try:
                    from src.database.models import Job as JobModel
                    db_job = session.query(JobModel).filter_by(id=job_id).first()
                    if db_job and db_job.alerted_at is None:
                        unalerted_jobs.append(job)
                finally:
                    session.close()
            else:
                # No ID or DB - send alert anyway (shouldn't happen)
                unalerted_jobs.append(job)
        
        if len(jobs) > len(unalerted_jobs):
            logger.info(f"Skipping {len(jobs) - len(unalerted_jobs)} jobs - already alerted")
        
        immediate_jobs = [j for j in unalerted_jobs if j.get('fit_score', 0) >= immediate_threshold]
        digest_jobs = [j for j in unalerted_jobs if digest_threshold <= j.get('fit_score', 0) < immediate_threshold]
        
        stats = {'immediate': 0, 'digest': 0, 'skipped': 0}
        
        # Send immediate alerts
        recipient_email = os.getenv('ALERT_EMAIL')
        recipient_sms = os.getenv('ALERT_SMS')
        
        alerted_job_ids = []
        
        for job in immediate_jobs:
            if recipient_email:
                if self.email.send_immediate_alert(job, recipient_email):
                    stats['immediate'] += 1
                    if job.get('id'):
                        alerted_job_ids.append(job['id'])
            
            if recipient_sms and self.sms.enabled:
                self.sms.send_alert(job, recipient_sms)
        
        # Send digest if there are digest-level jobs
        if digest_jobs and recipient_email:
            if self.email.send_digest(digest_jobs, recipient_email):
                stats['digest'] = len(digest_jobs)
                for job in digest_jobs:
                    if job.get('id'):
                        alerted_job_ids.append(job['id'])
        
        # Mark jobs as alerted in database
        if alerted_job_ids and self.db:
            session = self.db.get_session()
            try:
                from src.database.models import Job as JobModel
                from datetime import datetime
                session.query(JobModel).filter(JobModel.id.in_(alerted_job_ids)).update(
                    {JobModel.alerted_at: datetime.utcnow()},
                    synchronize_session=False
                )
                session.commit()
                logger.info(f"Marked {len(alerted_job_ids)} jobs as alerted")
            except Exception as e:
                logger.error(f"Error marking jobs as alerted: {e}")
                session.rollback()
            finally:
                session.close()
        
        stats['skipped'] = len(jobs) - len(immediate_jobs) - len(digest_jobs)
        
        logger.info(f"Alerts sent - Immediate: {stats['immediate']}, Digest: {stats['digest']}, Skipped: {stats['skipped']}")
        return stats


if __name__ == "__main__":
    # Test
    test_job = {
        'title': 'Machine Learning Engineer',
        'company': 'TestCo',
        'url': 'https://example.com/job',
        'fit_score': 85,
        'matches': {'tech': ['Python', 'ML', 'AWS'], 'industry': ['AI/ML'], 'role': ['ML Engineer']},
        'reasoning': 'Strong technical match',
        'visa_status': 'explicit'
    }
    
    manager = AlertManager()
    print("Alert system initialized")
