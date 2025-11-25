"""
Application Email Sender
Sends emails with generated CVs and application tracking
"""
from typing import List, Dict, Any
from datetime import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from loguru import logger


class ApplicationEmailer:
    """
    Sends emails with generated CVs and application links
    Helps user easily apply to jobs with customized materials
    """
    
    def __init__(self):
        self.enabled = os.getenv('ENABLE_CV_EMAILS', 'true').lower() == 'true'
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USERNAME')
        self.smtp_pass = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.to_email = os.getenv('TO_EMAIL', 'harveyhoulahan@outlook.com')
        
        if self.enabled and not all([self.smtp_user, self.smtp_pass]):
            logger.warning("SMTP credentials not configured - CV emails disabled")
            self.enabled = False
    
    def send_application_batch(
        self,
        applications: List[Dict[str, Any]],
        summary_stats: Dict[str, Any]
    ) -> bool:
        """
        Send email with all generated CVs and application tracking links
        
        Args:
            applications: List of prepared application dicts with CVs
            summary_stats: Stats about the job hunt cycle
            
        Returns:
            True if email sent successfully
        """
        if not self.enabled:
            logger.info(f"CV emails disabled. Would send {len(applications)} CVs")
            return False
        
        if not applications:
            logger.info("No applications to email")
            return False
        
        logger.info(f"Preparing email with {len(applications)} CVs...")
        
        # Create email
        msg = MIMEMultipart('mixed')
        msg['From'] = self.from_email
        msg['To'] = self.to_email
        msg['Subject'] = f"🎯 {len(applications)} Job Applications Ready - {datetime.now().strftime('%m/%d/%Y')}"
        
        # Email body with job list and quick apply links
        html_body = self._create_html_body(applications, summary_stats)
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attach PDF CVs
        for app in applications:
            pdf_path = app.get('cv', {}).get('pdf_path')
            if pdf_path and os.path.exists(pdf_path):
                try:
                    with open(pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
                    pdf_filename = os.path.basename(pdf_path)
                    pdf_attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=pdf_filename
                    )
                    msg.attach(pdf_attachment)
                except Exception as e:
                    logger.error(f"Error attaching {pdf_path}: {e}")
        
        # Send email
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            logger.info(f"✓ Sent application email with {len(applications)} CVs to {self.to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending CV email: {e}")
            return False
    
    def _create_html_body(
        self,
        applications: List[Dict[str, Any]],
        summary_stats: Dict[str, Any]
    ) -> str:
        """Create HTML email body with job list and apply links"""
        
        # Sort by score
        sorted_apps = sorted(
            applications,
            key=lambda x: x.get('score', {}).get('fit_score', 0),
            reverse=True
        )
        
        # Build job list HTML
        job_rows = []
        for i, app in enumerate(sorted_apps, 1):
            job = app.get('job', {})
            score = app.get('score', {}).get('fit_score', 0)
            
            # Determine score badge color
            if score >= 80:
                badge_color = '#10b981'  # green
            elif score >= 60:
                badge_color = '#f59e0b'  # orange
            else:
                badge_color = '#6b7280'  # gray
            
            job_url = job.get('url', '#')
            
            job_rows.append(f"""
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 12px 8px; text-align: center; font-weight: bold; color: #374151;">
                        {i}
                    </td>
                    <td style="padding: 12px 8px;">
                        <div style="font-weight: 600; color: #111827; margin-bottom: 4px;">
                            {job.get('title', 'Unknown')}
                        </div>
                        <div style="color: #6b7280; font-size: 14px;">
                            {job.get('company', 'Unknown')} • {job.get('location', 'Remote')}
                        </div>
                    </td>
                    <td style="padding: 12px 8px; text-align: center;">
                        <span style="background: {badge_color}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 14px;">
                            {score:.1f}%
                        </span>
                    </td>
                    <td style="padding: 12px 8px; text-align: center;">
                        <a href="{job_url}" 
                           style="background: #2563eb; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 500; display: inline-block;"
                           onclick="navigator.clipboard.writeText('{app.get('id', '')}'); return true;">
                            Apply Now →
                        </a>
                    </td>
                </tr>
            """)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f9fafb; margin: 0; padding: 20px;">
    <div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center;">
            <h1 style="margin: 0 0 8px 0; font-size: 28px; font-weight: 700;">
                🎯 Your Job Applications Are Ready!
            </h1>
            <p style="margin: 0; font-size: 16px; opacity: 0.95;">
                {len(applications)} customized CVs attached • Generated {datetime.now().strftime('%B %d, %Y')}
            </p>
        </div>
        
        <!-- Summary Stats -->
        <div style="padding: 24px; background: #f9fafb; border-bottom: 1px solid #e5e7eb;">
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <div style="font-size: 32px; font-weight: 700; color: #667eea;">
                        {summary_stats.get('jobs_found', 0)}
                    </div>
                    <div style="color: #6b7280; font-size: 14px; margin-top: 4px;">
                        Jobs Found
                    </div>
                </div>
                <div>
                    <div style="font-size: 32px; font-weight: 700; color: #10b981;">
                        {summary_stats.get('jobs_new', 0)}
                    </div>
                    <div style="color: #6b7280; font-size: 14px; margin-top: 4px;">
                        New Jobs
                    </div>
                </div>
                <div>
                    <div style="font-size: 32px; font-weight: 700; color: #f59e0b;">
                        {len(applications)}
                    </div>
                    <div style="color: #6b7280; font-size: 14px; margin-top: 4px;">
                        CVs Generated
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Job List -->
        <div style="padding: 24px;">
            <h2 style="margin: 0 0 16px 0; color: #111827; font-size: 20px; font-weight: 600;">
                📋 Applications Ready to Submit
            </h2>
            <p style="color: #6b7280; margin: 0 0 20px 0;">
                Each job has a customized CV attached. Click "Apply Now" to open the job posting, then use the attached CV for that company.
            </p>
            
            <table style="width: 100%; border-collapse: collapse; background: white; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                <thead>
                    <tr style="background: #f9fafb; border-bottom: 2px solid #e5e7eb;">
                        <th style="padding: 12px 8px; text-align: center; color: #6b7280; font-weight: 600; font-size: 12px; text-transform: uppercase;">#</th>
                        <th style="padding: 12px 8px; text-align: left; color: #6b7280; font-weight: 600; font-size: 12px; text-transform: uppercase;">Job</th>
                        <th style="padding: 12px 8px; text-align: center; color: #6b7280; font-weight: 600; font-size: 12px; text-transform: uppercase;">Score</th>
                        <th style="padding: 12px 8px; text-align: center; color: #6b7280; font-weight: 600; font-size: 12px; text-transform: uppercase;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(job_rows)}
                </tbody>
            </table>
        </div>
        
        <!-- Instructions -->
        <div style="padding: 24px; background: #eff6ff; border-top: 1px solid #e5e7eb;">
            <h3 style="margin: 0 0 12px 0; color: #1e40af; font-size: 16px; font-weight: 600;">
                📝 How to Apply
            </h3>
            <ol style="margin: 0; padding-left: 20px; color: #374151; line-height: 1.8;">
                <li>Click "Apply Now" to open the job posting</li>
                <li>Use the attached CV for that company (filename matches company name)</li>
                <li>Copy/paste the cover letter from the applications/ folder</li>
                <li>After applying, mark it in the database:
                    <code style="background: white; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #dc2626;">
                        python3 -i manage_applications.py
                    </code>
                </li>
            </ol>
        </div>
        
        <!-- Footer -->
        <div style="padding: 20px; text-align: center; color: #6b7280; font-size: 14px; border-top: 1px solid #e5e7eb;">
            <p style="margin: 0;">
                Generated by JobHunter • {datetime.now().strftime('%I:%M %p')}
            </p>
            <p style="margin: 8px 0 0 0; font-size: 12px;">
                CVs customized using AI • All materials saved in <code>applications/</code> folder
            </p>
        </div>
        
    </div>
</body>
</html>
        """
        
        return html


# Integration with manage_applications.py for tracking
def mark_job_as_applied(job_id: int, cv_filename: str, method: str = "linkedin"):
    """
    Mark a job as applied after user submits application
    
    Usage in manage_applications.py:
        >>> mark_as_applied(123, "CV_Cohere_Software_Engineer.pdf", "linkedin")
    """
    from src.database.models import Database
    
    db = Database()
    db.mark_applied(
        job_id=job_id,
        cv_version=cv_filename,
        application_method=method,
        notes=f"Applied via {method} on {datetime.now().strftime('%Y-%m-%d')}"
    )
    print(f"✓ Marked job {job_id} as applied with CV: {cv_filename}")
