import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://etl_user:etl_pass@localhost:5432/healthcare_etl",
    )
    PHI_ENCRYPTION_KEY: str = os.getenv("PHI_ENCRYPTION_KEY", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
