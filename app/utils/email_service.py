"""
Email Service
Sends emails using SMTP (similar to Java's SimpleMailMessage)
Supports Gmail, Outlook, and other SMTP servers
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    attachments: Optional[List[dict]] = None
) -> bool:
    """
    Send an email using SMTP (similar to Java's SimpleMailMessage).
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML email body
        body_text: Plain text email body (optional, defaults to HTML stripped)
        attachments: List of attachments, each with 'filename' and 'content' (bytes)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Hardcoded email configuration (temporary - will use env later)
        smtp_host = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = "test.send.email.spring@gmail.com"
        smtp_password = "wehzmwvoyddbgnop"  # App password
        from_email = "test.send.email.spring@gmail.com"
        
        # SMTP settings
        smtp_auth = True
        smtp_starttls = True
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add text and HTML parts
        if body_text:
            part1 = MIMEText(body_text, 'plain')
            msg.attach(part1)
        
        part2 = MIMEText(body_html, 'html')
        msg.attach(part2)
        
        # Add attachments if provided
        if attachments:
            for attachment in attachments:
                filename = attachment.get('filename')
                content = attachment.get('content')
                if filename and content:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()  # Enable encryption
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


def send_monthly_report_email(
    user_email: str,
    month: str,
    total_spent: float,
    pdf_url: Optional[str] = None,
    csv_url: Optional[str] = None,
    overspending_categories: Optional[dict] = None,
    spending_spikes: Optional[List[dict]] = None
) -> bool:
    """
    Send monthly expense report email to user.
    
    Args:
        user_email: User's email address
        month: Month in YYYY-MM format
        total_spent: Total amount spent in the month
        pdf_url: URL to download PDF report
        csv_url: URL to download CSV report
        overspending_categories: Dict of categories that exceeded budget
        spending_spikes: List of spending spikes detected
    
    Returns:
        bool: True if email sent successfully
    """
    # Format month for display
    from datetime import datetime
    try:
        month_date = datetime.strptime(month, "%Y-%m")
        month_display = month_date.strftime("%B %Y")
    except:
        month_display = month
    
    # Build HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background-color: #f8fafc; padding: 20px; border-radius: 0 0 8px 8px; }}
            .summary-box {{ background-color: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #2563eb; }}
            .alert-box {{ background-color: #fef2f2; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #dc2626; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin: 10px 5px; }}
            .button:hover {{ background-color: #1d4ed8; }}
            .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Monthly Expense Report</h1>
                <p>{month_display}</p>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>Your monthly expense report for <strong>{month_display}</strong> is ready!</p>
                
                <div class="summary-box">
                    <h2 style="margin-top: 0;">Summary</h2>
                    <p style="font-size: 24px; font-weight: bold; color: #2563eb;">Total Spent: €{total_spent:,.2f}</p>
                </div>
    """
    
    # Add overspending alerts
    if overspending_categories and len(overspending_categories) > 0:
        html_body += """
                <div class="alert-box">
                    <h3 style="margin-top: 0; color: #dc2626;">Budget Alerts</h3>
                    <p>The following categories exceeded your budget:</p>
                    <ul>
        """
        for category, amount in overspending_categories.items():
            html_body += f"<li><strong>{category}</strong>: €{amount:,.2f} over budget</li>"
        html_body += """
                    </ul>
                </div>
        """
    
    # Add spending spikes
    if spending_spikes and len(spending_spikes) > 0:
        html_body += """
                <div class="alert-box">
                    <h3 style="margin-top: 0; color: #dc2626;">Spending Spikes Detected</h3>
                    <p>Unusual spending detected in the following transactions:</p>
                    <ul>
        """
        for spike in spending_spikes[:5]:  # Show top 5
            html_body += f"<li><strong>{spike.get('category', 'Unknown')}</strong>: €{spike.get('amount', 0):,.2f}</li>"
        html_body += """
                    </ul>
                </div>
        """
    
    # Add download links
    html_body += """
                <div style="text-align: center; margin: 20px 0;">
    """
    if pdf_url:
        html_body += f'<a href="{pdf_url}" class="button">Download PDF Report</a>'
    if csv_url:
        html_body += f'<a href="{csv_url}" class="button">Download CSV Report</a>'
    
    html_body += """
                </div>
                
                <p>You can also view your reports in the Smart Expense Tracker dashboard.</p>
            </div>
            <div class="footer">
                <p>This is an automated email from Smart Expense Tracker.</p>
                <p>If you have any questions, please contact support.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
Monthly Expense Report - {month_display}

Hello,

Your monthly expense report for {month_display} is ready!

Summary:
Total Spent: €{total_spent:,.2f}
    """
    
    if overspending_categories and len(overspending_categories) > 0:
        text_body += "\n\nBudget Alerts:\n"
        for category, amount in overspending_categories.items():
            text_body += f"- {category}: €{amount:,.2f} over budget\n"
    
    if spending_spikes and len(spending_spikes) > 0:
        text_body += "\nSpending Spikes Detected:\n"
        for spike in spending_spikes[:5]:
            text_body += f"- {spike.get('category', 'Unknown')}: €{spike.get('amount', 0):,.2f}\n"
    
    if pdf_url:
        text_body += f"\nDownload PDF Report: {pdf_url}\n"
    if csv_url:
        text_body += f"Download CSV Report: {csv_url}\n"
    
    text_body += "\nYou can also view your reports in the Smart Expense Tracker dashboard.\n"
    text_body += "\nThis is an automated email from Smart Expense Tracker."
    
    # Send email
    subject = f"Monthly Expense Report - {month_display}"
    return send_email(
        to_email=user_email,
        subject=subject,
        body_html=html_body,
        body_text=text_body
    )

