from decimal import Decimal
from typing import Any, Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=settings.DYNAMO_REGION)

# Get table references
users_table = dynamodb.Table(settings.DYNAMO_USERS_TABLE)
expenses_table = dynamodb.Table(settings.DYNAMO_EXPENSES_TABLE)


def get_user_by_email(email: str):
    """Query the Users table by email (assumes a GSI exists on email)."""
    try:
        response = users_table.query(
            IndexName="email-index",  # You must create this GSI manually
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email)
        )
        return _from_dynamo(response["Items"][0]) if response["Items"] else None
    except ClientError as e:
        print(f"[ERROR] get_user_by_email failed: {e.response['Error']['Message']}")
        return None


def get_user_by_id(user_id: str):
    """Get user by user_id from the Users table."""
    try:
        response = users_table.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        return _from_dynamo(item) if item else None
    except ClientError as e:
        print(f"[ERROR] get_user_by_id failed: {e.response['Error']['Message']}")
        return None


def put_user(user_item: dict):
    """Insert a new user into the Users table."""
    try:
        users_table.put_item(Item=_convert_for_dynamo(user_item))
        return True
    except ClientError as e:
        print(f"[ERROR] put_user failed: {e.response['Error']['Message']}")
        return False


def put_expense(expense_item: dict):
    """Insert or update an expense for a user."""
    try:
        expenses_table.put_item(Item=_convert_for_dynamo(expense_item))
        return True
    except ClientError as e:
        print(f"[ERROR] put_expense failed: {e.response['Error']['Message']}")
        return False


def get_expenses_for_user(user_id: str, month_prefix: str):
    """
    Query all expenses for a given user and month.
    month_prefix: '2024-11' matches all items with SK like '2024-11-01T...'
    """
    try:
        response = expenses_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id) &
                                   boto3.dynamodb.conditions.Key("expense_id").begins_with(month_prefix)
        )
        return [_from_dynamo(item) for item in response["Items"]]
    except ClientError as e:
        print(f"[ERROR] get_expenses_for_user failed: {e.response['Error']['Message']}")
        return []


def delete_expense(user_id: str, expense_id: str):
    """Delete a specific expense item."""
    try:
        response = expenses_table.delete_item(
            Key={"user_id": user_id, "expense_id": expense_id},
            ReturnValues="ALL_OLD",
        )
        return "Attributes" in response
    except ClientError as e:
        print(f"[ERROR] delete_expense failed: {e.response['Error']['Message']}")
        return False


def get_expense(user_id: str, expense_id: str):
    """Fetch a single expense item."""
    try:
        response = expenses_table.get_item(Key={"user_id": user_id, "expense_id": expense_id})
        item = response.get("Item")
        return _from_dynamo(item) if item else None
    except ClientError as e:
        print(f"[ERROR] get_expense failed: {e.response['Error']['Message']}")
        return None


def update_expense(user_id: str, expense_id: str, updates: dict):
    """
    Apply partial updates to an expense. Returns the updated item or None.
    """
    if not updates:
        return None

    update_expression_parts = []
    expression_attribute_values = {}
    expression_attribute_names = {}

    for idx, (key, value) in enumerate(updates.items()):
        placeholder = f"#f{idx}"
        value_placeholder = f":v{idx}"
        update_expression_parts.append(f"{placeholder} = {value_placeholder}")
        expression_attribute_names[placeholder] = key
        expression_attribute_values[value_placeholder] = value

    update_expression = "SET " + ", ".join(update_expression_parts)

    try:
        response = expenses_table.update_item(
            Key={"user_id": user_id, "expense_id": expense_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=_convert_for_dynamo(expression_attribute_values),
            ReturnValues="ALL_NEW",
        )
        attributes = response.get("Attributes")
        return _from_dynamo(attributes) if attributes else None
    except ClientError as e:
        print(f"[ERROR] update_expense failed: {e.response['Error']['Message']}")
        return None


def _convert_for_dynamo(obj: Any):
    """
    Recursively convert floats to Decimal for DynamoDB compatibility.
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_for_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_for_dynamo(v) for v in obj]
    return obj


def _from_dynamo(obj: Any):
    """
    Recursively convert Decimal instances back to native Python numeric types.
    """
    if isinstance(obj, list):
        return [_from_dynamo(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


# Scheduler Settings Storage (using SYSTEM_CONFIG user_id)
SYSTEM_CONFIG_USER_ID = "SYSTEM_CONFIG"


def get_scheduler_settings():
    """
    Get scheduler settings from DynamoDB (stored in a special system user record).
    Returns dict with day, hour, minute, running, or None if not found.
    """
    try:
        response = users_table.get_item(Key={"user_id": SYSTEM_CONFIG_USER_ID})
        item = response.get("Item")
        if item:
            settings = _from_dynamo(item)
            return {
                "day": settings.get("scheduler_day", 1),
                "hour": settings.get("scheduler_hour", 6),
                "minute": settings.get("scheduler_minute", 0),
                "running": settings.get("scheduler_running", False),
            }
        return None
    except ClientError as e:
        print(f"[ERROR] get_scheduler_settings failed: {e.response['Error']['Message']}")
        return None


def save_scheduler_settings(day: int, hour: int, minute: int, running: Optional[bool] = None):
    """
    Save scheduler settings to DynamoDB (stored in a special system user record).
    Preserves budget thresholds when updating scheduler settings.
    """
    try:
        # Get existing settings to preserve running state if not provided
        existing = get_scheduler_settings()
        if existing is None:
            existing = {}
        
        # Get existing thresholds to preserve them
        existing_thresholds = get_budget_thresholds()
        
        item = {
            "user_id": SYSTEM_CONFIG_USER_ID,
            "email": "system@config.local",  # Dummy email for system record
            "scheduler_day": day,
            "scheduler_hour": hour,
            "scheduler_minute": minute,
            "scheduler_running": running if running is not None else existing.get("running", False),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Preserve budget thresholds if they exist
        if existing_thresholds:
            item["budget_thresholds"] = existing_thresholds
        
        users_table.put_item(Item=_convert_for_dynamo(item))
        return True
    except ClientError as e:
        print(f"[ERROR] save_scheduler_settings failed: {e.response['Error']['Message']}")
        return False


def initialize_default_scheduler_settings():
    """
    Initialize default scheduler settings in DynamoDB if they don't exist.
    Default: 1st day of month, 6 AM UTC (any time can be set later).
    """
    existing = get_scheduler_settings()
    if existing is None:
        # No settings exist, create default
        save_scheduler_settings(day=1, hour=6, minute=0, running=False)
        return True
    return False


def get_budget_thresholds():
    """
    Get budget thresholds from DynamoDB (stored in a special system user record).
    Returns dict with category thresholds, or None if not found.
    """
    try:
        response = users_table.get_item(Key={"user_id": SYSTEM_CONFIG_USER_ID})
        item = response.get("Item")
        if item:
            settings = _from_dynamo(item)
            thresholds = settings.get("budget_thresholds")
            if thresholds:
                return thresholds
        return None
    except ClientError as e:
        print(f"[ERROR] get_budget_thresholds failed: {e.response['Error']['Message']}")
        return None


def save_budget_thresholds(thresholds: dict):
    """
    Save budget thresholds to DynamoDB (stored in a special system user record).
    thresholds: dict with category names as keys and amounts as values.
    """
    try:
        # Get existing settings to preserve scheduler settings
        existing_settings = get_scheduler_settings()
        existing_thresholds = get_budget_thresholds()
        
        item = {
            "user_id": SYSTEM_CONFIG_USER_ID,
            "email": "system@config.local",
            "budget_thresholds": thresholds,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Preserve scheduler settings if they exist
        if existing_settings:
            item["scheduler_day"] = existing_settings.get("day", 1)
            item["scheduler_hour"] = existing_settings.get("hour", 6)
            item["scheduler_minute"] = existing_settings.get("minute", 0)
            item["scheduler_running"] = existing_settings.get("running", False)
        
        users_table.put_item(Item=_convert_for_dynamo(item))
        return True
    except ClientError as e:
        print(f"[ERROR] save_budget_thresholds failed: {e.response['Error']['Message']}")
        return False


def initialize_default_budget_thresholds():
    """
    Initialize default budget thresholds in DynamoDB if they don't exist.
    Loads from config/budget_thresholds.json file.
    """
    existing = get_budget_thresholds()
    if existing is None:
        # Load from JSON file
        import json
        from pathlib import Path
        from app.core.config import settings
        
        budget_file = Path(settings.BUDGET_THRESHOLDS_JSON)
        if budget_file.exists():
            with budget_file.open() as fp:
                thresholds = json.load(fp)
                save_budget_thresholds(thresholds)
                return True
        else:
            # Use default thresholds if file doesn't exist
            default_thresholds = {
                "Food": 400,
                "Travel": 250,
                "Rent": 1200,
                "Shopping": 300,
                "Utilities": 180,
                "Health": 150,
                "Entertainment": 150,
                "Education": 200,
                "Misc": 100
            }
            save_budget_thresholds(default_thresholds)
            return True
    return False