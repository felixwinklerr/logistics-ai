"""Application configuration and settings"""
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    

    
    # Application
    app_name: str = "Romanian Freight Forwarder Automation System"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "development-secret-key-change-in-production"
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    allowed_hosts: List[str] = ["*"]
    
    # Database
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "logistics_db"
    db_user: str = "logistics"
    db_password: str = "password"
    
    @property
    def get_database_url(self) -> str:
        """Get the database URL, building it if not provided"""
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # AI Services
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_key: Optional[str] = None
    azure_openai_version: str = "2023-12-01-preview"
    
    # File Storage (MinIO)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket_name: str = "logistics-documents"
    minio_secure: bool = False
    
    # Email Configuration
    email_provider: str = "gmail"
    email_host: str = "imap.gmail.com"
    email_port: int = 993
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_use_ssl: bool = True
    
    # Authentication
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"
    
    # External Services
    mailgun_api_key: Optional[str] = None
    mailgun_domain: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    log_level: str = "INFO"
    prometheus_enabled: bool = True
    
    # Geocoding
    google_maps_api_key: Optional[str] = None
    mapbox_access_token: Optional[str] = None
    
    # Romanian Services
    anaf_api_base_url: str = "https://webservicesp.anaf.ro"
    efactura_endpoint: str = "https://api.anaf.ro/prod/FCTEL/rest"
    efactura_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env to be ignored


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


# Global settings instance
settings = get_settings()
