import os
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # App settings
    PROJECT_NAME: str = "SmartExpenseTracker"
    API_PREFIX: str = "/api"
    DEBUG: bool = Field(default=False)

    # DynamoDB
    DYNAMO_REGION: str = Field(default="eu-west-1", env="DYNAMO_REGION")
    DYNAMO_USERS_TABLE: str = Field(default="smart-expense-users", env="DYNAMO_TABLE_USERS")
    DYNAMO_EXPENSES_TABLE: str = Field(default="smart-expense-expenses", env="DYNAMO_TABLE_EXPENSES")

    # AWS S3
    S3_BUCKET_NAME: str = Field(default="smart-expense-reports-2025", env="S3_BUCKET_NAME")
    S3_REGION: str = Field(default="eu-west-1", env="S3_REGION")

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(default="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9", env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days


    # Custom Library Settings (if needed)
    BUDGET_THRESHOLDS_JSON: str = Field(default="config/budget_thresholds.json")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
