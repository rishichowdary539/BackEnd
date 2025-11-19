"""
Lambda Trigger Router
Endpoints for manually triggering the monthly expense reports Lambda function
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict

from app.utils.lambda_scheduler import trigger_monthly_reports
from app.utils.scheduler import get_scheduler_status
from app.core.security import decode_access_token
from fastapi import Header

router = APIRouter()


class LambdaTriggerResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    message: Optional[str] = None


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate user ID from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        token = authorization.replace("Bearer ", "").strip()
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        return user_id
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@router.post("/trigger", response_model=LambdaTriggerResponse)
async def trigger_lambda_manually(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Manually trigger the monthly expense reports Lambda function.
    This will send emails to all users with scheduler enabled.
    """
    try:
        # Use trigger_monthly_reports() which gets enabled users and sends to Lambda
        result = trigger_monthly_reports()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=result.get("status_code", 500),
                detail=result.get("error", "Failed to invoke Lambda function")
            )
        
        return LambdaTriggerResponse(
            success=True,
            message=result.get("message", "Monthly reports triggered successfully"),
            result=result.get("result")
        )
    
    except HTTPException:
        raise
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

