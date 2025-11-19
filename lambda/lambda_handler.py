import json
import logging
import os
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from analyzer import FinanceAnalyzer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ENV vars expected with defaults
DYNAMO_REGION = os.environ.get("DYNAMO_REGION", "eu-west-1")
USERS_TABLE = os.environ.get("DYNAMO_TABLE_USERS", "smart-expense-users")
EXPENSES_TABLE = os.environ.get("DYNAMO_TABLE_EXPENSES", "smart-expense-expenses")
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "smart-expense-reports-2025")
S3_REGION = os.environ.get("S3_REGION", "eu-west-1")

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb", region_name=DYNAMO_REGION)
s3 = boto3.client("s3", region_name=S3_REGION) if S3_BUCKET else None

users_table = dynamodb.Table(USERS_TABLE)
expenses_table = dynamodb.Table(EXPENSES_TABLE)

finance_analyzer = FinanceAnalyzer()


def lambda_handler(event, context):
    """
    Lambda handler for monthly expense reports.
    Processes all users and generates expense summaries.
    """
    try:
        today = datetime.utcnow()
        month = today.strftime("%Y-%m")

        logger.info(f"Processing monthly reports for {month}")
        logger.info(f"Using tables: {USERS_TABLE}, {EXPENSES_TABLE}")

        # Get users to process - check if user_ids are provided in event (from scheduler)
        user_ids_to_process = None
        if event and isinstance(event, dict):
            user_ids_to_process = event.get("user_ids")
            if user_ids_to_process:
                logger.info(f"Processing reports for {len(user_ids_to_process)} enabled users")
        
        # Get users - either specific users or all users
        if user_ids_to_process:
            # Get specific users with scheduler enabled
            users = []
            for user_id in user_ids_to_process:
                try:
                    response = users_table.get_item(Key={"user_id": user_id})
                    if "Item" in response:
                        users.append(response["Item"])
                except Exception as e:
                    logger.error(f"Error fetching user {user_id}: {str(e)}")
        else:
            # Get all users (backward compatibility)
            users = users_table.scan().get("Items", [])

        if not users:
            logger.info("No users found in database")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "success",
                    "message": "No users found",
                    "users_processed": 0
                })
            }

        processed_count = 0
        results = []

        for user in users:
            try:
                user_id = user["user_id"]
                email = user.get("email", "unknown")

                # Query expenses for this user
                response = expenses_table.query(
                    KeyConditionExpression=Key("user_id").eq(user_id) & Key("expense_id").begins_with(month)
                )
                expenses = _from_dynamo(response.get("Items", []))

                if not expenses:
                    logger.info(f"No expenses found for user {user_id} in {month}")
                    continue

                # Analyze expenses
                summary = finance_analyzer.summarize(expenses)

                # Generate CSV report if S3 is configured
                report_url = None
                if s3 and S3_BUCKET:
                    csv_lines = ["category,amount,description,timestamp"]
                    for e in expenses:
                        csv_lines.append(
                            f"{e['category']},{e['amount']},{e.get('description', '')},{e['timestamp']}"
                        )

                    import uuid
                    report_id = f"{user_id}_{month}_{uuid.uuid4().hex[:6]}"
                    csv_key = f"reports/{user_id}/{report_id}.csv"
                    s3.put_object(
                        Bucket=S3_BUCKET,
                        Key=csv_key,
                        Body="\n".join(csv_lines),
                        ContentType="text/csv"
                    )
                    report_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{csv_key}"

                # Send email notification
                try:
                    from email_service import send_monthly_report_email
                    
                    if email and email != "unknown":
                        email_sent = send_monthly_report_email(
                            user_email=email,
                            month=month,
                            total_spent=summary['monthly_total'],
                            csv_url=report_url,
                            overspending_categories=summary.get('overspending_categories', {})
                        )
                        if email_sent:
                            logger.info(f"Monthly report email sent to {email}")
                        else:
                            logger.warning(f"Failed to send monthly report email to {email}")
                    else:
                        logger.warning(f"No valid email for user {user_id}, skipping email")
                except Exception as e:
                    logger.error(f"Error sending email notification: {str(e)}")
                    # Don't fail the report generation if email fails

                # Log report details
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

                results.append({
                    "user_id": user_id,
                    "email": email,
                    "total_spent": summary['monthly_total'],
                    "report_url": report_url
                })

                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing user {user.get('user_id', 'unknown')}: {str(e)}")
                continue

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "month": month,
                "users_processed": processed_count,
                "total_users": len(users),
                "results": results
            }, default=str)
        }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": str(e)
            })
        }


def _from_dynamo(obj):
    """Convert DynamoDB types to Python native types."""
    if isinstance(obj, list):
        return [_from_dynamo(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    return obj

