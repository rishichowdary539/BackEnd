"""
Simple test script to test email functionality
Run this from BackEnd directory: python test_email.py
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.email_service import send_monthly_report_email

# Test email
test_email = input("Enter your email address to test: ").strip()

if not test_email:
    print("No email provided. Exiting.")
    sys.exit(1)

print(f"\nSending test email to {test_email}...")

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

