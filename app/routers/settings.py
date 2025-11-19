"""
Settings Router
Provides endpoints to control scheduler and manage application settings
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel

from app.core.security import decode_access_token
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


@router.get("/scheduler")
def get_scheduler_settings(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get current scheduler status and configuration.
    """
    status_info = get_scheduler_status()
    
    # Get current schedule from the job if scheduler is running
    current_schedule = None
    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        for job in jobs:
            if job.id == "monthly_expense_reports":
                trigger = job.trigger
                if isinstance(trigger, CronTrigger):
                    # Extract schedule from trigger fields
                    try:
                        day_field = trigger.fields[2]  # Day of month field
                        hour_field = trigger.fields[3]  # Hour field
                        minute_field = trigger.fields[4]  # Minute field
                        
                        # Get first value from each field
                        day = list(day_field.expressions[0].values)[0] if hasattr(day_field, 'expressions') and day_field.expressions else None
                        hour = list(hour_field.expressions[0].values)[0] if hasattr(hour_field, 'expressions') and hour_field.expressions else None
                        minute = list(minute_field.expressions[0].values)[0] if hasattr(minute_field, 'expressions') and minute_field.expressions else None
                        
                        current_schedule = {
                            "day": day,
                            "hour": hour,
                            "minute": minute,
                        }
                    except (AttributeError, IndexError, TypeError):
                        # Fallback: try to get from job kwargs or use defaults
                        current_schedule = {
                            "day": 1,
                            "hour": 6,
                            "minute": 0,
                        }
                    
                    # Get next run time
                    if job.next_run_time:
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
    Start the scheduler.
    """
    try:
        if scheduler and scheduler.running:
            return {
                "success": True,
                "message": "Scheduler is already running",
                "status": get_scheduler_status()
            }
        
        start_scheduler()
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
    Stop the scheduler.
    """
    try:
        if scheduler is None or not scheduler.running:
            return {
                "success": True,
                "message": "Scheduler is already stopped",
                "status": {"running": False}
            }
        
        stop_scheduler()
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
            
            # Get updated job info
            job = scheduler.get_job("monthly_expense_reports")
            next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
            
            return {
                "success": True,
                "message": f"Scheduler schedule updated. Next run: {next_run}",
                "schedule": {
                    "day": schedule.day,
                    "hour": schedule.hour,
                    "minute": schedule.minute,
                    "next_run": next_run
                }
            }
        else:
            # Scheduler is not running, just return the schedule that will be used when started
            return {
                "success": True,
                "message": "Schedule updated. Start scheduler to apply changes.",
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

