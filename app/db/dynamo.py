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


# Scheduler Settings Storage (per-user)
SYSTEM_CONFIG_USER_ID = "SYSTEM_CONFIG"  # Still used for system-wide config if needed


def get_scheduler_settings(user_id: str):
    """
    Get scheduler settings from DynamoDB for a specific user.
    Returns dict with day, hour, minute, enabled, or None if not found.
    """
    try:
        response = users_table.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        if item:
            user_data = _from_dynamo(item)
            return {
                "day": user_data.get("scheduler_day", 1),
                "hour": user_data.get("scheduler_hour", 6),
                "minute": user_data.get("scheduler_minute", 0),
                "enabled": user_data.get("scheduler_enabled", False),
            }
        return None
    except ClientError as e:
        print(f"[ERROR] get_scheduler_settings failed: {e.response['Error']['Message']}")
        return None


def save_scheduler_settings(user_id: str, day: int, hour: int, minute: int, enabled: Optional[bool] = None):
    """
    Save scheduler settings to DynamoDB for a specific user.
    """
    try:
        # Get existing user data to preserve other fields
        existing_user = get_user_by_id(user_id)
        
        if existing_user:
            # Update existing user record
            item = dict(existing_user)
            item["scheduler_day"] = day
            item["scheduler_hour"] = hour
            item["scheduler_minute"] = minute
            if enabled is not None:
                item["scheduler_enabled"] = enabled
            elif "scheduler_enabled" not in item:
                item["scheduler_enabled"] = False
            item["updated_at"] = datetime.utcnow().isoformat()
        else:
            # User doesn't exist, this shouldn't happen but handle gracefully
            raise ValueError(f"User {user_id} not found")
        
        users_table.put_item(Item=_convert_for_dynamo(item))
        return True
    except ClientError as e:
        print(f"[ERROR] save_scheduler_settings failed: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"[ERROR] save_scheduler_settings failed: {str(e)}")
        return False


def initialize_default_scheduler_settings(user_id: str):
    """
    Initialize default scheduler settings in DynamoDB for a specific user if they don't exist.
    Default: 1st day of month, 6 AM UTC, disabled.
    """
    existing = get_scheduler_settings(user_id)
    if existing is None:
        # No settings exist, create default
        save_scheduler_settings(user_id, day=1, hour=6, minute=0, enabled=False)
        return True
    return False


def get_all_users_with_scheduler_enabled():
    """
    Get all user IDs that have scheduler enabled.
    Used by the scheduler to determine which users to process.
    """
    try:
        # Scan users table for users with scheduler_enabled = True
        # Note: This is a scan operation, which can be expensive for large tables
        # In production, consider adding a GSI on scheduler_enabled
        from boto3.dynamodb import conditions
        response = users_table.scan(
            FilterExpression=conditions.Attr("scheduler_enabled").eq(True)
        )
        user_ids = []
        for item in response.get("Items", []):
            user_id = item.get("user_id")
            if user_id and user_id != SYSTEM_CONFIG_USER_ID:
                user_ids.append(user_id)
        return user_ids
    except ClientError as e:
        print(f"[ERROR] get_all_users_with_scheduler_enabled failed: {e.response['Error']['Message']}")
        return []


def get_budget_thresholds(user_id: str):
    """
    Get budget thresholds from DynamoDB for a specific user.
    Returns dict with category thresholds, or None if not found.
    """
    try:
        response = users_table.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        if item:
            user_data = _from_dynamo(item)
            thresholds = user_data.get("budget_thresholds")
            if thresholds:
                return thresholds
        return None
    except ClientError as e:
        print(f"[ERROR] get_budget_thresholds failed: {e.response['Error']['Message']}")
        return None


def save_budget_thresholds(user_id: str, thresholds: dict):
    """
    Save budget thresholds to DynamoDB for a specific user.
    thresholds: dict with category names as keys and amounts as values.
    """
    try:
        # Get existing user data to preserve other fields
        existing_user = get_user_by_id(user_id)
        
        if existing_user:
            # Update existing user record
            item = dict(existing_user)
            item["budget_thresholds"] = thresholds
            item["updated_at"] = datetime.utcnow().isoformat()
        else:
            # User doesn't exist, this shouldn't happen but handle gracefully
            raise ValueError(f"User {user_id} not found")
        
        users_table.put_item(Item=_convert_for_dynamo(item))
        return True
    except ClientError as e:
        print(f"[ERROR] save_budget_thresholds failed: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"[ERROR] save_budget_thresholds failed: {str(e)}")
        return False


def initialize_default_budget_thresholds(user_id: str):
    """
    Initialize default budget thresholds in DynamoDB for a specific user if they don't exist.
    Loads from config/budget_thresholds.json file.
    """
    existing = get_budget_thresholds(user_id)
    if existing is None:
        # Load from JSON file
        import json
        from pathlib import Path
        from app.core.config import settings
        
        budget_file = Path(settings.BUDGET_THRESHOLDS_JSON)
        if budget_file.exists():
            with budget_file.open() as fp:
                thresholds = json.load(fp)
                save_budget_thresholds(user_id, thresholds)
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
            save_budget_thresholds(user_id, default_thresholds)
            return True
    return False