"""
Configuration management for Urban Pulse backend system.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "urban_pulse")
    
    # API
    API_TITLE: str = "Urban Pulse Investment Intelligence API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Transform real estate listing data into borough-level Opportunity Scores"
    
    # Data paths
    ZILLOW_DATA_PATH: str = os.getenv("ZILLOW_DATA_PATH", "zillow_properties_listing.csv")
    GEOJSON_PATH: Optional[str] = os.getenv("GEOJSON_PATH", None)  # Optional GeoJSON for boroughs
    
    # Feature weights (for Opportunity Score calculation)
    WEIGHT_PRICE_GROWTH: float = 0.25
    WEIGHT_DEMAND_SCORE: float = 0.25
    WEIGHT_MOBILITY_SCORE: float = 0.20
    WEIGHT_CLIMATE_RISK: float = -0.10  # Negative because lower is better
    
    # Processing
    BATCH_SIZE: int = 1000
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
