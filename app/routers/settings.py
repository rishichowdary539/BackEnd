"""
Settings Router
Provides endpoints to control scheduler and manage application settings
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel

from app.core.security import decode_access_token
from app.db import dynamo
from app.utils.scheduler import (
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
    scheduler
)
from apscheduler.triggers.cron import CronTrigger
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


class SchedulerScheduleUpdate(BaseModel):
    day: int  # Day of month (1-31)
    hour: int  # Hour (0-23)
    minute: int  # Minute (0-59)


class BudgetThresholdsUpdate(BaseModel):
    thresholds: Dict[str, float]  # Category name -> amount


@router.get("/scheduler")
def get_scheduler_settings(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get current scheduler status and configuration.
    Loads settings from DynamoDB.
    """
    status_info = get_scheduler_status()
    
    # Get schedule from DynamoDB (source of truth)
    db_settings = dynamo.get_scheduler_settings()
    if db_settings:
        current_schedule = {
            "day": db_settings.get("day", 1),
            "hour": db_settings.get("hour", 6),
            "minute": db_settings.get("minute", 0),
        }
    else:
        # Fallback to defaults if not in DB
        current_schedule = {
            "day": 1,
            "hour": 6,
            "minute": 0,
        }
    
    # Get next run time from running scheduler if available
    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        for job in jobs:
            if job.id == "monthly_expense_reports" and job.next_run_time:
                current_schedule["next_run"] = job.next_run_time.isoformat()
                break
    
    return {
        "running": status_info.get("running", False),
        "jobs": status_info.get("jobs", []),
        "schedule": current_schedule,
    }


@router.post("/scheduler/start")
def start_scheduler_endpoint(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Start the scheduler and save state to DB.
    """
    try:
        if scheduler and scheduler.running:
            # Update DB state
            db_settings = dynamo.get_scheduler_settings()
            if db_settings:
                dynamo.save_scheduler_settings(
                    db_settings.get("day", 1),
                    db_settings.get("hour", 6),
                    db_settings.get("minute", 0),
                    running=True
                )
            return {
                "success": True,
                "message": "Scheduler is already running",
                "status": get_scheduler_status()
            }
        
        start_scheduler()
        
        # Save running state to DB
        db_settings = dynamo.get_scheduler_settings()
        if db_settings:
            dynamo.save_scheduler_settings(
                db_settings.get("day", 1),
                db_settings.get("hour", 6),
                db_settings.get("minute", 0),
                running=True
            )
        
        return {
            "success": True,
            "message": "Scheduler started successfully",
            "status": get_scheduler_status()
        }
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/scheduler/stop")
def stop_scheduler_endpoint(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Stop the scheduler and save state to DB.
    """
    try:
        if scheduler is None or not scheduler.running:
            # Update DB state
            db_settings = dynamo.get_scheduler_settings()
            if db_settings:
                dynamo.save_scheduler_settings(
                    db_settings.get("day", 1),
                    db_settings.get("hour", 6),
                    db_settings.get("minute", 0),
                    running=False
                )
            return {
                "success": True,
                "message": "Scheduler is already stopped",
                "status": {"running": False}
            }
        
        stop_scheduler()
        
        # Save stopped state to DB
        db_settings = dynamo.get_scheduler_settings()
        if db_settings:
            dynamo.save_scheduler_settings(
                db_settings.get("day", 1),
                db_settings.get("hour", 6),
                db_settings.get("minute", 0),
                running=False
            )
        
        return {
            "success": True,
            "message": "Scheduler stopped successfully",
            "status": {"running": False}
        }
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@router.put("/scheduler/schedule")
def update_scheduler_schedule(
    schedule: SchedulerScheduleUpdate,
    user_id: str = Depends(get_current_user_id)
) -> Dict:
    """
    Update the scheduler cron schedule.
    Requires scheduler to be restarted to take effect.
    """
    # Validate inputs
    if not (1 <= schedule.day <= 31):
        raise HTTPException(status_code=400, detail="Day must be between 1 and 31")
    if not (0 <= schedule.hour <= 23):
        raise HTTPException(status_code=400, detail="Hour must be between 0 and 23")
    if not (0 <= schedule.minute <= 59):
        raise HTTPException(status_code=400, detail="Minute must be between 0 and 59")
    
    try:
        # If scheduler is running, we need to update the job
        if scheduler and scheduler.running:
            # Remove existing job
            scheduler.remove_job("monthly_expense_reports")
            
            # Add new job with updated schedule
            from app.utils.scheduler import monthly_reports_job
            scheduler.add_job(
                monthly_reports_job,
                trigger=CronTrigger(
                    day=schedule.day,
                    hour=schedule.hour,
                    minute=schedule.minute
                ),
                id="monthly_expense_reports",
                name="Monthly Expense Reports",
                replace_existing=True
            )
            
            logger.info(f"Scheduler schedule updated to: day={schedule.day}, hour={schedule.hour}, minute={schedule.minute}")
            
            # Save to DynamoDB (preserve running state)
            db_settings = dynamo.get_scheduler_settings()
            running = db_settings.get("running", False) if db_settings else False
            dynamo.save_scheduler_settings(schedule.day, schedule.hour, schedule.minute, running=running)
            
            # Get updated job info
            job = scheduler.get_job("monthly_expense_reports")
            next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
            
            return {
                "success": True,
                "message": f"Scheduler schedule updated and saved to database. Next run: {next_run}",
                "schedule": {
                    "day": schedule.day,
                    "hour": schedule.hour,
                    "minute": schedule.minute,
                    "next_run": next_run
                }
            }
        else:
            # Scheduler is not running, save to DynamoDB for when it starts (preserve running state)
            db_settings = dynamo.get_scheduler_settings()
            running = db_settings.get("running", False) if db_settings else False
            dynamo.save_scheduler_settings(schedule.day, schedule.hour, schedule.minute, running=running)
            
            return {
                "success": True,
                "message": "Schedule updated and saved to database. Start scheduler to apply changes.",
                "schedule": {
                    "day": schedule.day,
                    "hour": schedule.hour,
                    "minute": schedule.minute,
                },
                "note": "Scheduler is not running. Start it to apply this schedule."
            }
    except Exception as e:
        logger.error(f"Error updating scheduler schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.get("/thresholds")
def get_budget_thresholds(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get current budget thresholds from DynamoDB.
    """
    thresholds = dynamo.get_budget_thresholds()
    if thresholds is None:
        # Return empty dict if not found
        return {"thresholds": {}}
    
    return {"thresholds": thresholds}


@router.put("/thresholds")
def update_budget_thresholds(
    update: BudgetThresholdsUpdate,
    user_id: str = Depends(get_current_user_id)
) -> Dict:
    """
    Update budget thresholds in DynamoDB.
    These thresholds are used for notifications when spending crosses limits.
    """
    # Validate thresholds (all values must be positive)
    for category, amount in update.thresholds.items():
        if amount < 0:
            raise HTTPException(status_code=400, detail=f"Threshold for {category} must be positive")
    
    try:
        success = dynamo.save_budget_thresholds(update.thresholds)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save budget thresholds")
        
        return {
            "success": True,
            "message": "Budget thresholds updated successfully",
            "thresholds": update.thresholds
        }
    except Exception as e:
        logger.error(f"Error updating budget thresholds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update thresholds: {str(e)}")

