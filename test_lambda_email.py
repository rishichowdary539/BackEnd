"""
Test Lambda email service directly
Usage: python test_lambda_email.py your-email@example.com
"""
import sys
import os

# Add lambda directory to path
lambda_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lambda")
sys.path.insert(0, lambda_dir)

from email_service import send_monthly_report_email

# Get email from command line argument
if len(sys.argv) < 2:
    print("Usage: python test_lambda_email.py your-email@example.com")
    sys.exit(1)

test_email = sys.argv[1].strip()

print("\nTesting Lambda Email Service")
print(f"Sending test email to: {test_email}")
print("Using SMTP: smtp.gmail.com:587")
print("From: godelevengaming@gmail.com\n")

# Send test email with sample data
success = send_monthly_report_email(
    user_email=test_email,
    month="2025-11",
    total_spent=1250.50,
    csv_url="https://example.com/report.csv",
    overspending_categories={"Food": 150.00, "Shopping": 75.50}
)

if success:
    print(f"\nSUCCESS: Email sent successfully to {test_email}!")
    print("Check your inbox (and spam folder).")
    print("\nThe email should contain:")
    print("  - Monthly spending summary")
    print("  - Budget alerts (if any)")
    print("  - Download link for CSV report")
else:
    print(f"\nFAILED: Could not send email.")
    print("Check the error messages above for details.")

