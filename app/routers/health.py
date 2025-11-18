"""
Health Check Router
Simple health check endpoint
"""
from fastapi import APIRouter
from datetime import datetime
import logging
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.db import dynamo
from app.utils.lambda_scheduler import lambda_client, LAMBDA_FUNCTION_NAME

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns API status.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def aws_services_status():
    """
    Check connectivity and status of all AWS services:
    - DynamoDB (Users and Expenses tables)
    - S3 (Reports bucket)
    - Lambda (Monthly reports function)
    """
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check DynamoDB
    dynamodb_status = {
        "connected": False,
        "tables": {},
        "error": None
    }
    try:
        # Check Users table
        try:
            dynamo.users_table.scan(Limit=1)
            dynamodb_status["tables"]["users"] = {
                "name": settings.DYNAMO_USERS_TABLE,
                "status": "accessible",
                "region": settings.DYNAMO_REGION
            }
        except Exception as e:
            dynamodb_status["tables"]["users"] = {
                "name": settings.DYNAMO_USERS_TABLE,
                "status": "error",
                "error": str(e)
            }
        
        # Check Expenses table
        try:
            dynamo.expenses_table.scan(Limit=1)
            dynamodb_status["tables"]["expenses"] = {
                "name": settings.DYNAMO_EXPENSES_TABLE,
                "status": "accessible",
                "region": settings.DYNAMO_REGION
            }
        except Exception as e:
            dynamodb_status["tables"]["expenses"] = {
                "name": settings.DYNAMO_EXPENSES_TABLE,
                "status": "error",
                "error": str(e)
            }
        
        if all(table["status"] == "accessible" for table in dynamodb_status["tables"].values()):
            dynamodb_status["connected"] = True
    except Exception as e:
        dynamodb_status["error"] = str(e)
        logger.error(f"DynamoDB check failed: {str(e)}")
    
    status["services"]["dynamodb"] = dynamodb_status
    
    # Check S3
    s3_status = {
        "connected": False,
        "bucket": settings.S3_BUCKET_NAME,
        "region": settings.S3_REGION,
        "error": None
    }
    try:
        s3_client = boto3.client("s3", region_name=settings.S3_REGION)
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        s3_status["connected"] = True
        s3_status["status"] = "accessible"
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        s3_status["error"] = f"{error_code}: {str(e)}"
        s3_status["status"] = "error"
        logger.error(f"S3 check failed: {str(e)}")
    except Exception as e:
        s3_status["error"] = str(e)
        s3_status["status"] = "error"
        logger.error(f"S3 check failed: {str(e)}")
    
    status["services"]["s3"] = s3_status
    
    # Check Lambda
    lambda_status = {
        "connected": False,
        "function_name": LAMBDA_FUNCTION_NAME,
        "error": None
    }
    try:
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        lambda_status["connected"] = True
        lambda_status["status"] = response["Configuration"]["State"]
        lambda_status["runtime"] = response["Configuration"]["Runtime"]
        # LastModified is already a string from AWS API
        last_modified = response["Configuration"]["LastModified"]
        lambda_status["last_modified"] = last_modified.isoformat() if hasattr(last_modified, 'isoformat') else str(last_modified)
        lambda_status["region"] = settings.DYNAMO_REGION
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        lambda_status["error"] = f"{error_code}: {str(e)}"
        lambda_status["status"] = "error"
        logger.error(f"Lambda check failed: {str(e)}")
    except Exception as e:
        lambda_status["error"] = str(e)
        lambda_status["status"] = "error"
        logger.error(f"Lambda check failed: {str(e)}")
    
    status["services"]["lambda"] = lambda_status
    
    # Overall status
    all_connected = all(
        service.get("connected", False) 
        for service in status["services"].values()
    )
    
    status["overall_status"] = "healthy" if all_connected else "degraded"
    
    return status
