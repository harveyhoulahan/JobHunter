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
        """Format single job for email (mobile-optimized for iOS)"""
        fit_score = job.get('fit_score', 0)
        matches = job.get('matches', {})
        reasoning = job.get('reasoning', 'No reasoning available')
        
        tech_skills = ', '.join(matches.get('tech', [])[:8])
        industries = ', '.join(matches.get('industry', []))
        roles = ', '.join(matches.get('role', []))
        visa_status = job.get('visa_status', 'unknown')
        
        # Clean URL - remove tracking params and LinkedIn app redirect
        job_url = job.get('url', '#')
        # For LinkedIn jobs, use the web URL to prevent app redirect issues
        if 'linkedin.com' in job_url:
            # Ensure we're using linkedin.com/jobs/view instead of linkedin app links
            job_url = job_url.replace('linkedin://job/', 'https://www.linkedin.com/jobs/view/')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
            <style>
                /* iOS Mail optimization */
                @media only screen and (max-width: 600px) {{
                    .button {{
                        width: 100% !important;
                        display: block !important;
                        padding: 16px 24px !important;
                        font-size: 18px !important;
                    }}
                    .container {{
                        padding: 16px !important;
                    }}
                    h2 {{
                        font-size: 22px !important;
                    }}
                    h3 {{
                        font-size: 18px !important;
                    }}
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background-color: #f5f5f5;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
                <tr>
                    <td align="center">
                        <table class="container" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%); padding: 24px; text-align: center;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">🎯 High-Match Job Alert</h1>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td style="padding: 24px;">
                                    <h2 style="color: #1a1a1a; margin: 0 0 8px 0; font-size: 24px; line-height: 1.3;">{job.get('title', 'Untitled')}</h2>
                                    <h3 style="color: #6b7280; margin: 0 0 24px 0; font-weight: 600; font-size: 20px;">{job.get('company', 'Unknown Company')}</h3>
                                    
                                    <!-- Fit Score -->
                                    <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 20px; border-radius: 10px; margin: 24px 0; border-left: 4px solid #8b5cf6;">
                                        <h3 style="margin: 0 0 16px 0; color: #1a1a1a; font-size: 18px;">Fit Score: <span style="color: #8b5cf6; font-size: 28px; font-weight: 700;">{fit_score}/100</span></h3>
                                        <p style="margin: 8px 0; color: #374151; line-height: 1.6;"><strong>Technical Match:</strong> {tech_skills or 'None identified'}</p>
                                        <p style="margin: 8px 0; color: #374151; line-height: 1.6;"><strong>Industry:</strong> {industries or 'General'}</p>
                                        <p style="margin: 8px 0; color: #374151; line-height: 1.6;"><strong>Role:</strong> {roles or 'Various'}</p>
                                        <p style="margin: 8px 0; color: #374151; line-height: 1.6;"><strong>Visa Status:</strong> {visa_status}</p>
                                    </div>
                                    
                                    <!-- Why this matches -->
                                    <div style="margin: 24px 0;">
                                        <h4 style="margin: 0 0 12px 0; color: #1a1a1a; font-size: 16px;">Why this matches:</h4>
                                        <p style="margin: 0; color: #4b5563; line-height: 1.7; font-size: 15px;">{reasoning}</p>
                                    </div>
                                    
                                    <!-- CTA Button - Mobile Optimized -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 32px 0;">
                                        <tr>
                                            <td align="center">
                                                <a href="{job_url}" class="button" style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 10px; display: inline-block; font-weight: 600; font-size: 16px; min-width: 200px; text-align: center; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);">
                                                    Apply Now →
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- Job Details -->
                                    <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 24px;">
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">
                                                    <strong style="color: #374151;">📍 Location:</strong> {job.get('location', 'Not specified')}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">
                                                    <strong style="color: #374151;">📅 Posted:</strong> {job.get('posted_date', 'Recently')}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">
                                                    <strong style="color: #374151;">🔗 Source:</strong> {job.get('source', 'Unknown')}
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                    
                                    <!-- Direct Link (fallback) -->
                                    <div style="margin-top: 20px; padding: 16px; background-color: #f9fafb; border-radius: 8px;">
                                        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 13px;">If button doesn't work, copy this link:</p>
                                        <p style="margin: 0; word-break: break-all; color: #8b5cf6; font-size: 12px;">{job_url}</p>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                                    <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                        JobHunter • Automated Job Alerts for Harvey Houlahan
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        return html
    
    def _format_digest_email(self, jobs: List[Dict[str, Any]]) -> str:
        """Format multiple jobs for digest email (mobile-optimized for iOS)"""
        job_items = ""
        
        for job in sorted(jobs, key=lambda x: x.get('fit_score', 0), reverse=True):
            fit_score = job.get('fit_score', 0)
            tech_skills = ', '.join(job.get('matches', {}).get('tech', [])[:5])
            
            # Clean URL for LinkedIn
            job_url = job.get('url', '#')
            if 'linkedin.com' in job_url:
                job_url = job_url.replace('linkedin://job/', 'https://www.linkedin.com/jobs/view/')
            
            job_items += f"""
            <tr>
                <td style="padding: 16px; border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 16px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td>
                                <h3 style="margin: 0 0 8px 0; font-size: 18px; line-height: 1.4;">
                                    <a href="{job_url}" style="color: #8b5cf6; text-decoration: none; font-weight: 600;">
                                        {job.get('title', 'Untitled')}
                                    </a>
                                </h3>
                                <p style="margin: 0 0 12px 0; color: #374151; font-size: 15px;">
                                    <strong>{job.get('company', 'Unknown')}</strong> • {job.get('location', 'Location TBD')}
                                </p>
                                <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 10px 16px; border-radius: 8px; display: inline-block; margin-bottom: 12px;">
                                    <span style="color: #8b5cf6; font-weight: 700; font-size: 16px;">Fit Score: {fit_score}/100</span>
                                </div>
                                <p style="margin: 12px 0; color: #6b7280; font-size: 14px;"><strong>Key Skills:</strong> {tech_skills or 'Various'}</p>
                                <p style="margin: 12px 0; color: #4b5563; font-size: 14px; line-height: 1.6;"><em>{job.get('reasoning', '')[:150]}...</em></p>
                                
                                <!-- Mobile-optimized button -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 16px;">
                                    <tr>
                                        <td align="center" style="padding: 8px 0;">
                                            <a href="{job_url}" style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: 600; font-size: 14px; min-width: 140px; text-align: center;">
                                                View Details →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr><td style="height: 16px;"></td></tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
            <style>
                @media only screen and (max-width: 600px) {{
                    .container {{
                        padding: 12px !important;
                    }}
                    h1 {{
                        font-size: 24px !important;
                    }}
                    .button {{
                        width: 100% !important;
                        display: block !important;
                    }}
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background-color: #f5f5f5;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
                <tr>
                    <td align="center">
                        <table class="container" width="100%" style="max-width: 700px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%); padding: 24px; text-align: center;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">📬 Your Daily Job Digest</h1>
                                    <p style="margin: 8px 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 16px;">
                                        {len(jobs)} new opportunities matched your profile
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Jobs List -->
                            <tr>
                                <td style="padding: 24px;">
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        {job_items}
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                                    <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                        JobHunter • Automated Job Alerts for Harvey Houlahan
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
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
