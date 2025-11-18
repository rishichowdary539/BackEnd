"""
Lambda Trigger Router
Endpoints for manually triggering the monthly expense reports Lambda function
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.utils.lambda_scheduler import invoke_lambda_function, trigger_monthly_reports
from app.utils.scheduler import get_scheduler_status

router = APIRouter()


class LambdaTriggerResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


@router.post("/trigger", response_model=LambdaTriggerResponse)
async def trigger_lambda_manually():
    """
    Manually trigger the monthly expense reports Lambda function.
    Can be called via API Gateway or directly.
    """
    try:
        result = invoke_lambda_function()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=result.get("status_code", 500),
                detail=result.get("error", "Failed to invoke Lambda function")
            )
        
        return LambdaTriggerResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering Lambda: {str(e)}")


@router.get("/status")
async def lambda_status():
    """
    Check if Lambda function is accessible and scheduler status.
    """
    try:
        import boto3
        from app.utils.lambda_scheduler import lambda_client, LAMBDA_FUNCTION_NAME
        
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        scheduler_status = get_scheduler_status()
        
        return {
            "function_name": LAMBDA_FUNCTION_NAME,
            "status": response["Configuration"]["State"],
            "last_modified": response["Configuration"]["LastModified"],
            "runtime": response["Configuration"]["Runtime"],
            "scheduler": scheduler_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking Lambda status: {str(e)}")

