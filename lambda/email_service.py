"""
Email Service for Lambda
Sends emails using SMTP (similar to Java's SimpleMailMessage)
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None
) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML email body
        body_text: Plain text email body (optional)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Hardcoded email configuration (temporary - will use env later)
        smtp_host = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = "godelevengaming@gmail.com"
        smtp_password = "dotnzjptumdfhjtv"  # App password (no spaces)
        from_email = "godelevengaming@gmail.com"
        
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
    csv_url: Optional[str] = None,
    overspending_categories: Optional[dict] = None
) -> bool:
    """
    Send monthly expense report email to user.
    
    Args:
        user_email: User's email address
        month: Month in YYYY-MM format
        total_spent: Total amount spent in the month
        csv_url: URL to download CSV report
        overspending_categories: Dict of categories that exceeded budget
    
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
        for category in overspending_categories:
            html_body += f"<li><strong>{category}</strong></li>"
        html_body += """
                    </ul>
                </div>
        """
    
    # Add download link
    html_body += """
                <div style="text-align: center; margin: 20px 0;">
    """
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
        for category in overspending_categories:
            text_body += f"- {category} exceeded budget\n"
    
    if csv_url:
        text_body += f"\nDownload CSV Report: {csv_url}\n"
    
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

