from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.routers import auth, expenses, reports, lambda_trigger
from app.utils.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the scheduler
    logger.info("Starting scheduler...")
    start_scheduler()
    yield
    # Shutdown: Stop the scheduler
    logger.info("Stopping scheduler...")
    stop_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


# Register routers
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Auth"])
app.include_router(expenses.router, prefix=f"{settings.API_PREFIX}/expenses", tags=["Expenses"])
app.include_router(reports.router, prefix=f"{settings.API_PREFIX}/reports", tags=["Reports"])
app.include_router(lambda_trigger.router, prefix=f"{settings.API_PREFIX}/lambda", tags=["Lambda"])
