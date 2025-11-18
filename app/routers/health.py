"""
Health Check Router
Simple health check endpoint
"""
from fastapi import APIRouter
from datetime import datetime

from app.core.config import settings

router = APIRouter()


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
