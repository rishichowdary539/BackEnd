import os
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # App settings
    PROJECT_NAME: str = "SmartExpenseTracker"
    API_PREFIX: str = "/api"
    DEBUG: bool = Field(default=False)

    # DynamoDB
    DYNAMO_REGION: str = Field(..., env="DYNAMO_REGION")
    DYNAMO_USERS_TABLE: str = Field(..., env="DYNAMO_TABLE_USERS")
    DYNAMO_EXPENSES_TABLE: str = Field(..., env="DYNAMO_TABLE_EXPENSES")

    # AWS S3
    S3_BUCKET_NAME: str = Field(..., env="S3_BUCKET_NAME")
    S3_REGION: str = Field(..., env="S3_REGION")

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Custom Library Settings (if needed)
    BUDGET_THRESHOLDS_JSON: str = Field(default="config/budget_thresholds.json")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
