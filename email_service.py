"""
Email Service Module

Provides SMTP email delivery for will documents and execution checklists.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, List
from datetime import datetime

from flask import current_app, render_template_string

from app.audit_logger import log_email_sent


# Email templates
WILL_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1a4232; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
        .important { background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; }
        .footer { padding: 20px; font-size: 12px; color: #666; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Your Will is Ready</h1>
        </div>
        <div class="content">
            <p>Dear {{ will_maker_name }},</p>
            
            <p>Your Last Will and Testament has been generated and is attached to this email.</p>
            
            <div class="warning">
                <strong>Important:</strong> This document is not legally valid until it is properly 
                signed and witnessed according to Queensland law.
            </div>
            
            <p><strong>Document Details:</strong></p>
            <ul>
                <li>Generated: {{ generated_at }}</li>
                <li>Document Hash: {{ document_hash }}</li>
            </ul>
            
            <p><strong>Next Steps:</strong></p>
            <ol>
                <li>Review the document carefully</li>
                <li>Print the document (do not sign yet)</li>
                <li>Follow the Execution Checklist attached</li>
                <li>Sign in the presence of two independent witnesses</li>
                <li>Store the original in a safe place</li>
            </ol>
            
            <div class="important">
                <strong>What This Will Does NOT Cover:</strong>
                <ul>
                    <li>Superannuation (contact your fund for a binding nomination)</li>
                    <li>Jointly held assets (these pass to the surviving owner)</li>
                    <li>Assets held in trust</li>
                    <li>Life insurance proceeds (check your beneficiary nominations)</li>
                </ul>
            </div>
            
            <p>If you need to make changes, you must create a new will. Do not write on this document.</p>
        </div>
        <div class="footer">
            <p>This email was sent from the Will Generator system.</p>
            <p>This is not legal advice. Consult a solicitor for complex situations.</p>
        </div>
    </div>
</body>
</html>
"""

TEXT_EMAIL_TEMPLATE = """
Your Will is Ready
==================

Dear {{ will_maker_name }},

Your Last Will and Testament has been generated and is attached to this email.

IMPORTANT: This document is not legally valid until it is properly signed and 
witnessed according to Queensland law.

Document Details:
- Generated: {{ generated_at }}
- Document Hash: {{ document_hash }}

Next Steps:
1. Review the document carefully
2. Print the document (do not sign yet)
3. Follow the Execution Checklist attached
4. Sign in the presence of two independent witnesses
5. Store the original in a safe place

What This Will Does NOT Cover:
- Superannuation (contact your fund for a binding nomination)
- Jointly held assets (these pass to the surviving owner)
- Assets held in trust
- Life insurance proceeds (check your beneficiary nominations)

If you need to make changes, you must create a new will. Do not write on this document.

---
This email was sent from the Will Generator system.
This is not legal advice. Consult a solicitor for complex situations.
"""


class EmailService:
    """Service for sending emails with will documents."""
    
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', '')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.smtp_tls = os.environ.get('SMTP_TLS', 'true').lower() == 'true'
        self.from_address = os.environ.get('EMAIL_FROM', 'noreply@willgenerator.local')
        self.enabled = all([self.smtp_host, self.smtp_user, self.smtp_password])
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return self.enabled
    
    def send_will_email(
        self,
        recipient_email: str,
        will_maker_name: str,
        pdf_bytes: bytes,
        checklist_pdf_bytes: bytes,
        document_hash: str,
        submission_id: int
    ) -> tuple:
        """
        Send will document and execution checklist via email.
        
        Args:
            recipient_email: Recipient email address
            will_maker_name: Name of will maker for personalization
            pdf_bytes: Will PDF content
            checklist_pdf_bytes: Execution checklist PDF content
            document_hash: Document hash for verification
            submission_id: Submission ID for audit logging
        
        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        if not self.is_configured():
            return False, 'Email service not configured'
        
        try:
            # Build email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Your Last Will and Testament'
            msg['From'] = self.from_address
            msg['To'] = recipient_email
            
            # Render templates
            template_vars = {
                'will_maker_name': will_maker_name,
                'generated_at': datetime.utcnow().strftime('%d %B %Y at %H:%M UTC'),
                'document_hash': document_hash[:16]
            }
            
            html_content = render_template_string(WILL_EMAIL_TEMPLATE, **template_vars)
            text_content = render_template_string(TEXT_EMAIL_TEMPLATE, **template_vars)
            
            # Attach content
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Attach will PDF
            will_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
            will_attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename='Last_Will_and_Testament.pdf'
            )
            msg.attach(will_attachment)
            
            # Attach checklist PDF
            checklist_attachment = MIMEApplication(checklist_pdf_bytes, _subtype='pdf')
            checklist_attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename='Execution_Checklist.pdf'
            )
            msg.attach(checklist_attachment)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            # Log success
            log_email_sent(submission_id, recipient_email, True)
            
            return True, None
        
        except Exception as e:
            error_msg = str(e)
            current_app.logger.error(f'Failed to send email: {error_msg}')
            
            # Log failure
            log_email_sent(submission_id, recipient_email, False, error_msg)
            
            return False, error_msg


# Global instance
email_service = EmailService()


def send_will_email(
    recipient_email: str,
    will_maker_name: str,
    pdf_bytes: bytes,
    checklist_pdf_bytes: bytes,
    document_hash: str,
    submission_id: int
) -> tuple:
    """
    Convenience function to send will email.
    
    Args:
        recipient_email: Recipient email address
        will_maker_name: Name of will maker
        pdf_bytes: Will PDF content
        checklist_pdf_bytes: Execution checklist PDF content
        document_hash: Document hash
        submission_id: Submission ID
    
    Returns:
        Tuple of (success, error_message)
    """
    return email_service.send_will_email(
        recipient_email,
        will_maker_name,
        pdf_bytes,
        checklist_pdf_bytes,
        document_hash,
        submission_id
    )
