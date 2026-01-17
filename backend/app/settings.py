from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database connection - prefer DATABASE_URL, fallback to components
    DATABASE_URL: Optional[str] = None
    
    # Individual database components (used if DATABASE_URL not provided)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "strain"
    DB_USER: str = "strain"
    DB_PASSWORD: str = "strain"
    
    # CORS origins - comma-separated list, default to localhost:5173 and 127.0.0.1:5173 for dev
    CORS_ORIGINS: Optional[str] = None
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    def get_cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        if not self.CORS_ORIGINS:
            # Default to localhost:5173 and 127.0.0.1:5173 for dev
            return ["http://localhost:5173", "http://127.0.0.1:5173"]
        # Split by comma, strip whitespace, filter empty strings
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return origins if origins else ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    def get_database_url(self) -> str:
        """Returns SQLAlchemy-compatible database URL."""
        if self.DATABASE_URL:
            # Ensure it uses psycopg2 driver
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif self.DATABASE_URL.startswith("postgresql+psycopg2://"):
                return self.DATABASE_URL
            else:
                return f"postgresql+psycopg2://{self.DATABASE_URL}"
        
        # Build from components
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()

