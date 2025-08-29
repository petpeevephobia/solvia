"""
Email service for sending audit reports with logging
"""
import os
from typing import Optional
from pathlib import Path
from datetime import datetime
import uuid
import json
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from app.config import settings
from supabase import create_client

async def log_email_activity(
    user_email: str,
    recipient_email: str,
    email_type: str,
    subject: str,
    status: str,
    error_message: str = None,
    audit_id: str = None,
    attachment_name: str = None,
    metadata: dict = None
) -> None:
    """Log email activity to database"""
    try:
        # Use service role key to bypass RLS for logging
        service_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        
        log_data = {
            "user_email": user_email,
            "recipient_email": recipient_email,
            "email_type": email_type,
            "subject": subject,
            "status": status,
            "error_message": error_message,
            "audit_id": audit_id,
            "attachment_name": attachment_name,
            "smtp_server": settings.EMAIL_HOST,
            "sent_from": settings.EMAIL_FROM,
            "sent_at": datetime.utcnow().isoformat() if status == "sent" else None,
            "metadata": json.dumps(metadata) if metadata else "{}"
        }
        
        result = service_client.table("email_logs").insert(log_data).execute()
        print(f"[EMAIL LOG] Logged email activity: {email_type} to {recipient_email} - {status}")
        
    except Exception as e:
        print(f"[EMAIL LOG] Failed to log email activity: {str(e)}")


async def send_audit_report_email(
    recipient_email: str,
    pdf_path: str,
    audit_id: str,
    seo_score: float,
    user_email: str = None
) -> bool:
    """
    Send audit report email with PDF attachment and logging
    """
    # Use recipient as user if not provided
    if not user_email:
        user_email = recipient_email
    
    subject = f"Your SEO Audit Report - Score: {seo_score}/100"
    
    # Check if email is enabled
    if not settings.EMAIL_ENABLED:
        print(f"[EMAIL] Email disabled. Would have sent report to {recipient_email}")
        await log_email_activity(
            user_email, recipient_email, "audit_report", subject,
            "skipped", "Email disabled in settings", audit_id
        )
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = recipient_email
        msg['Subject'] = f"Your SEO Audit Report - Score: {seo_score}/100"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #EC6019; margin-bottom: 10px;">Your SEO Audit is Ready!</h1>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: #1F2937; margin-top: 0;">SEO Score: {seo_score}/100</h2>
                    <p style="color: #6B7280;">
                        We've completed a comprehensive analysis of your website's SEO performance. 
                        Your detailed report is attached to this email.
                    </p>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #1F2937;">What's in the Report?</h3>
                    <ul style="color: #6B7280;">
                        <li>Complete SEO health score breakdown</li>
                        <li>Key performance metrics and trends</li>
                        <li>Critical issues affecting your visibility</li>
                        <li>Actionable recommendations for improvement</li>
                    </ul>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <p style="color: #6B7280;">
                        <strong>Report ID:</strong> {audit_id}<br>
                        <strong>Generated:</strong> Today
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    <p style="color: #9CA3AF; font-size: 14px;">
                        Powered by <strong style="color: #EC6019;">Solvia</strong> - Your AI SEO Assistant<br>
                        © 2025 Solvia. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach PDF
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as file:
                attach = MIMEBase('application', 'pdf')
                attach.set_payload(file.read())
                encoders.encode_base64(attach)
                attach.add_header(
                    'Content-Disposition',
                    f'attachment; filename=seo_audit_{audit_id}.pdf'
                )
                msg.attach(attach)
        
        # Send email with STARTTLS for Zoho
        await aiosmtplib.send(
            msg,
            hostname=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_USERNAME,
            password=settings.EMAIL_PASSWORD,
            start_tls=True,  # Use STARTTLS for Zoho
            use_tls=False    # Don't use direct TLS
        )
        
        # Log successful send
        await log_email_activity(
            user_email, recipient_email, "audit_report", subject,
            "sent", None, audit_id, 
            f"seo_audit_{audit_id}.pdf" if os.path.exists(pdf_path) else None,
            {"seo_score": seo_score}
        )
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"[EMAIL] Error sending audit report: {error_msg}")
        
        # Log failed send
        await log_email_activity(
            user_email, recipient_email, "audit_report", subject,
            "failed", error_msg, audit_id,
            f"seo_audit_{audit_id}.pdf" if pdf_path and os.path.exists(pdf_path) else None,
            {"seo_score": seo_score, "error_type": type(e).__name__}
        )
        
        return False

async def send_audit_notification(
    recipient_email: str,
    audit_id: str,
    seo_score: float,
    critical_issues: int = 0,
    user_email: str = None
) -> bool:
    """
    Send simple notification about audit completion with logging
    """
    # Use recipient as user if not provided
    if not user_email:
        user_email = recipient_email
    
    subject = "Your SEO Audit is Complete"
    
    # Check if email is enabled
    if not settings.EMAIL_ENABLED:
        print(f"[EMAIL] Email disabled. Would have sent notification to {recipient_email}")
        await log_email_activity(
            user_email, recipient_email, "notification", subject,
            "skipped", "Email disabled in settings", audit_id
        )
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = recipient_email
        msg['Subject'] = "Your SEO Audit is Complete"
        
        issue_text = f"{critical_issues} critical issues found" if critical_issues > 0 else "No critical issues"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #EC6019;">Audit Complete!</h2>
                <p>Your SEO audit has been completed successfully.</p>
                <p><strong>SEO Score:</strong> {seo_score}/100<br>
                <strong>Status:</strong> {issue_text}</p>
                <p>View your full report in the Solvia dashboard.</p>
                <p style="margin-top: 20px;">
                    <a href="{settings.FRONTEND_URL}/audit-history" 
                       style="background-color: #EC6019; color: white; padding: 10px 20px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Report
                    </a>
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        await aiosmtplib.send(
            msg,
            hostname=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_USERNAME,
            password=settings.EMAIL_PASSWORD,
            start_tls=True,  # Use STARTTLS for Zoho
            use_tls=False    # Don't use direct TLS
        )
        
        # Log successful send
        await log_email_activity(
            user_email, recipient_email, "notification", subject,
            "sent", None, audit_id, None,
            {"seo_score": seo_score, "critical_issues": critical_issues}
        )
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"[EMAIL] Error sending notification: {error_msg}")
        
        # Log failed send
        await log_email_activity(
            user_email, recipient_email, "notification", subject,
            "failed", error_msg, audit_id, None,
            {"seo_score": seo_score, "critical_issues": critical_issues, "error_type": type(e).__name__}
        )
        
        return False