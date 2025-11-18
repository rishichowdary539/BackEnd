"""
Example Router - For testing API Gateway proxy
This will be removed later
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """
    Example endpoint to test API Gateway proxy.
    This endpoint will be removed later.
    """
    return {
        "message": "This is a test endpoint",
        "status": "working",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "This endpoint works automatically through API Gateway proxy"
    }


@router.get("/info")
async def info_endpoint():
    """
    Another example endpoint.
    """
    return {
        "service": "SmartExpenseTracker",
        "version": "1.0.0",
        "proxy": "Working via /api/{proxy+}",
        "timestamp": datetime.utcnow().isoformat()
    }

