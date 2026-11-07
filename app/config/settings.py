"""Konfigurasi terpusat berbasis environment variable (pydantic v1 & v2)."""
import os
from typing import List

from app.core.paths import BASE_DIR

try:  # pydantic v2
    from pydantic_settings import BaseSettings
    PYDANTIC_V2 = True
except ImportError:  # pydantic v1
    from pydantic import BaseSettings
    PYDANTIC_V2 = False


class Settings(BaseSettings):
    PROJECT_NAME: str = "DTAnalitycs Data Analytic Studio Engine"
    ENV: str = "development"

    DB_TYPE: str = "sqlite"
    DB_NAME: str = "dtanalitycs_studio.db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    SQL_ECHO: bool = False
    AUTO_CREATE_TABLES: bool = True

    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"
    MAX_PREVIEW_ROWS: int = 500
    MAX_UPLOAD_MB: int = 50
    ALLOW_PYTHON_SCRIPT: bool = True
    ALLOW_EXTERNAL_SOURCE_PATH: bool = False

    if PYDANTIC_V2:
        model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}
    else:
        class Config:
            env_file = str(BASE_DIR / ".env")

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() in ("production", "prod")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            return "sqlite:///{}".format(BASE_DIR / self.DB_NAME)
        return "postgresql://{}:{}@{}:{}/{}".format(
            self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME
        )


settings = Settings()
