import json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from finance_analyzer_lib import FinanceAnalyzer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ENV vars expected
DYNAMO_REGION = os.environ["DYNAMO_REGION"]
USERS_TABLE = os.environ["DYNAMO_TABLE_USERS"]
EXPENSES_TABLE = os.environ["DYNAMO_TABLE_EXPENSES"]
S3_BUCKET = os.environ["S3_BUCKET_NAME"]
S3_REGION = os.environ["S3_REGION"]

dynamodb = boto3.resource("dynamodb", region_name=DYNAMO_REGION)
s3 = boto3.client("s3", region_name=S3_REGION)

users_table = dynamodb.Table(USERS_TABLE)
expenses_table = dynamodb.Table(EXPENSES_TABLE)
finance_analyzer = FinanceAnalyzer()


def lambda_handler(event, context):
    today = datetime.utcnow()
    month = today.strftime("%Y-%m")

    # Get all users
    users = users_table.scan().get("Items", [])

    for user in users:
        user_id = user["user_id"]
        email = user["email"]

        # Query expenses for this user
        response = expenses_table.query(
            KeyConditionExpression=Key("user_id").eq(user_id) & Key("expense_id").begins_with(month)
        )
        expenses = _from_dynamo(response.get("Items", []))

        if not expenses:
            continue

        summary = finance_analyzer.summarize(expenses)

        # Generate simple CSV
        csv_lines = ["category,amount,description,timestamp"]
        for e in expenses:
            csv_lines.append(f"{e['category']},{e['amount']},{e.get('description','')},{e['timestamp']}")

        report_id = f"{user_id}_{month}_{uuid.uuid4().hex[:6]}"
        csv_key = f"reports/{user_id}/{report_id}.csv"
        s3.put_object(Bucket=S3_BUCKET, Key=csv_key, Body="\n".join(csv_lines), ContentType="text/csv")

        report_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{csv_key}"

        # Log report details (using built-in Python logging)
        report_info = {
            "user_id": user_id,
            "email": email,
            "month": month,
            "total_spent": summary['monthly_total'],
            "overspending_categories": list(summary['overspending_categories'].keys()),
            "report_url": report_url,
            "insights": summary["insights"]
        }
        
        logger.info(f"Monthly report generated for user {user_id} ({email}):")
        logger.info(json.dumps(report_info, indent=2, default=str))
        
        # Print summary for CloudWatch Logs
        print(f"\n{'='*60}")
        print(f"Monthly Expense Report - {month}")
        print(f"User: {email} (ID: {user_id})")
        print(f"Total Spent: €{summary['monthly_total']:.2f}")
        print(f"Overspending Categories: {', '.join(summary['overspending_categories'].keys()) or 'None'}")
        print(f"Report URL: {report_url}")
        print(f"{'='*60}\n")

    return {"status": "success", "users_processed": len(users)}


def _from_dynamo(obj):
    if isinstance(obj, list):
        return [_from_dynamo(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    return obj

