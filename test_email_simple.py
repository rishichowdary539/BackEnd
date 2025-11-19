"""
Simple test script to test email functionality
Usage: python test_email_simple.py your-email@example.com
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.email_service import send_monthly_report_email

# Get email from command line argument
if len(sys.argv) < 2:
    print("Usage: python test_email_simple.py your-email@example.com")
    sys.exit(1)

test_email = sys.argv[1].strip()

print(f"\nSending test email to {test_email}...")
print("Using SMTP: smtp.gmail.com:587")
print("From: test.send.email.spring@gmail.com\n")

# Send test email with sample data
success = send_monthly_report_email(
    user_email=test_email,
    month="2025-11",
    total_spent=1250.50,
    pdf_url="https://example.com/report.pdf",
    csv_url="https://example.com/report.csv",
    overspending_categories={"Food": 150.00, "Shopping": 75.50},
    spending_spikes=[
        {"category": "Travel", "amount": 500.00},
        {"category": "Rent", "amount": 1200.00}
    ]
)

if success:
    print(f"\n✅ Email sent successfully to {test_email}!")
    print("Check your inbox (and spam folder).")
else:
    print(f"\n❌ Failed to send email. Check the logs above for errors.")

