import csv
import io
from fpdf import FPDF
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

# Initialize S3 client using default AWS credential chain
# (environment variables, AWS credentials file, or IAM role)
s3 = boto3.client("s3", region_name=settings.S3_REGION)


def generate_and_upload_pdf(user_id, month, expenses, total, overspending, suggested, spikes, report_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Monthly Report - {month}", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"User ID: {user_id}", ln=True)
    pdf.cell(0, 10, f"Total Spent: ${total}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Overspending Categories:", ln=True)
    pdf.set_font("Arial", "", 12)
    if overspending:
        for cat, amt in overspending.items():
            pdf.cell(0, 10, f"- {cat}: ${amt}", ln=True)
    else:
        pdf.cell(0, 10, "None", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Suggested Budgets:", ln=True)
    pdf.set_font("Arial", "", 12)
    for cat, amt in suggested.items():
        pdf.cell(0, 10, f"- {cat}: ${amt}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Spending Spikes (>$1000):", ln=True)
    pdf.set_font("Arial", "", 12)
    for spike in spikes:
        pdf.cell(0, 10, f"- {spike['category']}: ${spike['amount']} on {spike['timestamp']}", ln=True)

    # pdf.output(dest="S") returns bytes/bytearray, no need to encode
    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, str):
        pdf_bytes = pdf_output.encode("latin-1")
    elif isinstance(pdf_output, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_output)
    else:
        pdf_bytes = bytes(pdf_output)
    buffer = io.BytesIO(pdf_bytes)

    s3_key = f"reports/{user_id}/{report_id}.pdf"
    try:
        s3.upload_fileobj(buffer, settings.S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "application/pdf"})
        return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.S3_REGION}.amazonaws.com/{s3_key}"
    except ClientError as e:
        print(f"[ERROR] Failed to upload PDF: {e}")
        return None


def generate_and_upload_csv(user_id, month, expenses, report_id):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["category", "amount", "description", "timestamp"])
    writer.writeheader()
    for e in expenses:
        writer.writerow({
            "category": e["category"],
            "amount": e["amount"],
            "description": e.get("description", ""),
            "timestamp": e["timestamp"],
        })

    csv_buffer = io.BytesIO(output.getvalue().encode())
    s3_key = f"reports/{user_id}/{report_id}.csv"
    try:
        s3.upload_fileobj(csv_buffer, settings.S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "text/csv"})
        return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.S3_REGION}.amazonaws.com/{s3_key}"
    except ClientError as e:
        print(f"[ERROR] Failed to upload CSV: {e}")
        return None
