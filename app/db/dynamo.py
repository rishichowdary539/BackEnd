from decimal import Decimal
from typing import Any

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
