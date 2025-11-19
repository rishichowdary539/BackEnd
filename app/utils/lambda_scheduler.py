"""
Lambda Scheduler Service
Handles scheduled and manual triggering of the monthly expense reports Lambda function
"""
import logging
import os
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# AWS Configuration
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "smart-expense-monthly-reports")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# Initialize Lambda client
lambda_client = boto3.client("lambda", region_name=AWS_REGION)


def invoke_lambda_function(payload: Optional[dict] = None) -> dict:
    """
    Invoke the monthly expense reports Lambda function.
    
    Args:
        payload: Optional payload to send to Lambda (default: {})
        
    Returns:
        dict: Response from Lambda function
    """
    if payload is None:
        payload = {}
    
    try:
        logger.info(f"Invoking Lambda function: {LAMBDA_FUNCTION_NAME}")
        
        import json as json_lib
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType="RequestResponse",  # Synchronous invocation
            Payload=json_lib.dumps(payload).encode('utf-8') if payload else b'{}'
        )
        
        # Read response
        response_payload = response["Payload"].read()
        
        if response.get("FunctionError"):
            logger.error(f"Lambda function error: {response_payload.decode('utf-8')}")
            return {
                "success": False,
                "error": response_payload.decode('utf-8'),
                "status_code": response.get("StatusCode", 500)
            }
        
        result = response_payload.decode('utf-8')
        logger.info(f"Lambda function executed successfully")
        
        return {
            "success": True,
            "result": result,
            "status_code": response.get("StatusCode", 200)
        }
        
    except ClientError as e:
        error_msg = f"AWS Lambda error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error invoking Lambda: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }


def trigger_monthly_reports() -> dict:
    """
    Trigger monthly expense reports for all users with scheduler enabled.
    This is called by the scheduler.
    """
    from app.db import dynamo
    
    # Get all users with scheduler enabled
    enabled_user_ids = dynamo.get_all_users_with_scheduler_enabled()
    
    if not enabled_user_ids:
        logger.info("No users have scheduler enabled. Skipping monthly reports.")
        return {
            "success": True,
            "message": "No users have scheduler enabled",
            "users_processed": 0
        }
    
    logger.info(f"Triggering monthly reports at {datetime.utcnow()} for {len(enabled_user_ids)} users")
    logger.info(f"Enabled user IDs: {enabled_user_ids}")
    
    # Send user IDs to Lambda so it only processes enabled users
    payload = {
        "user_ids": enabled_user_ids,
        "triggered_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Sending payload to Lambda: {payload}")
    return invoke_lambda_function(payload)

