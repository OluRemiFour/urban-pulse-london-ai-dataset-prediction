"""
MongoDB models for Urban Pulse data.
Uses Pydantic for validation and serialization.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PropertyStatus(str, Enum):
    """Possible home statuses."""
    FOR_SALE = "FOR_SALE"
    SOLD = "SOLD"
    FOR_RENT = "FOR_RENT"
    PENDING = "PENDING"
    OFF_MARKET = "OFF_MARKET"
    UNKNOWN = "UNKNOWN"


class Property(BaseModel):
    """Individual property data model."""
    
    zpid: str = Field(..., description="Zillow Property ID")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    borough: Optional[str] = Field(None, description="London borough name")
    
    # Pricing
    price: float = Field(..., description="Current listing price")
    zestimate: Optional[float] = Field(None, description="Zillow estimate of property value")
    rentZestimate: Optional[float] = Field(None, description="Zillow rental estimate")
    lastSoldPrice: Optional[float] = Field(None, description="Last sale price")
    
    # Property details
    bedrooms: Optional[float] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    livingArea: Optional[float] = Field(None, description="Living area in sqft")
    sqft: Optional[float] = Field(None, description="Total property size in sqft")
    lotSize: Optional[float] = Field(None, description="Lot size in sqft")
    yearBuilt: Optional[int] = Field(None, description="Year property was built")
    homeType: Optional[str] = Field(None, description="Type of home")
    
    # Market signals
    daysOnZillow: int = Field(default=0, description="Days on marketplace")
    tourViewCount: int = Field(default=0, description="Number of tour views")
    num_of_contacts: int = Field(default=0, description="Number of buyer contacts")
    num_of_applications: int = Field(default=0, description="Number of rental applications")
    sold_to_list_ratio: Optional[float] = Field(None, description="Ratio of sold to list price")
    
    # Location & Environmental
    city: Optional[str] = Field(None, description="City")
    zipcode: Optional[str] = Field(None, description="ZIP code")
    county: Optional[str] = Field(None, description="County")
    getting_around_scores: Optional[Dict[str, Any]] = Field(None, description="Mobility scores")
    climate_risks: Optional[Dict[str, Any]] = Field(None, description="Climate risk assessment")
    
    # Status
    homeStatus: str = Field(default="UNKNOWN", description="Current home status")
    dateSold: Optional[datetime] = Field(None, description="Date property was sold")
    
    # Derived features
    price_per_sqft: Optional[float] = Field(None, description="Price per square foot")
    price_growth: float = Field(default=0.0, description="Price growth percentage")
    demand_score: float = Field(default=50.0, ge=0, le=100, description="Demand score 0-100")
    mobility_score: float = Field(default=50.0, ge=0, le=100, description="Mobility score 0-100")
    climate_risk_score: float = Field(default=25.0, ge=0, le=100, description="Climate risk 0-100")
    property_quality_score: float = Field(default=50.0, ge=0, le=100, description="Quality score 0-100")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "zpid": "12345678",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "price": 750000,
                "bedrooms": 3,
                "bathrooms": 2,
                "sqft": 1500,
                "demand_score": 75.0,
                "mobility_score": 85.0,
                "climate_risk_score": 20.0
            }
        }


class BoroughMetrics(BaseModel):
    """Borough-level aggregated metrics."""
    
    borough_name: str = Field(..., description="Name of the London borough")
    
    # Aggregated metrics
    property_count: int = Field(default=0, description="Total properties in borough")
    avg_price: float = Field(default=0, description="Average property price")
    avg_price_growth: float = Field(default=0, description="Average price growth %")
    avg_demand_score: float = Field(default=50, ge=0, le=100, description="Average demand score")
    avg_mobility_score: float = Field(default=50, ge=0, le=100, description="Average mobility score")
    avg_climate_risk_score: float = Field(default=25, ge=0, le=100, description="Average climate risk")
    avg_quality_score: float = Field(default=50, ge=0, le=100, description="Average property quality")
    
    # Market statistics
    median_price: Optional[float] = Field(None, description="Median property price")
    price_range_min: Optional[float] = Field(None, description="Minimum property price")
    price_range_max: Optional[float] = Field(None, description="Maximum property price")
    avg_days_on_market: float = Field(default=0, description="Average days on market")
    avg_bedrooms: float = Field(default=0, description="Average number of bedrooms")
    
    # Opportunity Score (main metric)
    opportunity_score: float = Field(default=50, ge=0, le=100, description="Overall opportunity score 0-100")
    rank: Optional[int] = Field(None, description="Rank among all boroughs (1 = best)")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "borough_name": "Westminster",
                "property_count": 1250,
                "avg_price": 850000,
                "avg_price_growth": 5.2,
                "avg_demand_score": 78.5,
                "avg_mobility_score": 92.3,
                "avg_climate_risk_score": 18.5,
                "opportunity_score": 72.3,
                "rank": 2
            }
        }


class PropertyResponse(BaseModel):
    """Response model for individual property."""
    
    id: Optional[str] = Field(None, alias="_id")
    zpid: str
    latitude: float
    longitude: float
    borough: Optional[str]
    price: float
    bedrooms: Optional[float]
    bathrooms: Optional[float]
    demand_score: float
    mobility_score: float
    climate_risk_score: float
    opportunity_score: Optional[float] = None
    
    class Config:
        populate_by_name = True


class BoroughResponse(BaseModel):
    """Response model for borough metrics."""
    
    id: Optional[str] = Field(None, alias="_id")
    borough_name: str
    property_count: int
    avg_price: float
    avg_price_growth: float
    avg_demand_score: float
    avg_mobility_score: float
    avg_climate_risk_score: float
    opportunity_score: float
    rank: Optional[int]
    
    class Config:
        populate_by_name = True


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    
    total: int = Field(..., description="Total number of items")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    items: List[Any] = Field(..., description="Response items")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    status: str = "error"
    message: str
    detail: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsSummary(BaseModel):
    """System-wide analytics summary."""
    
    total_properties: int
    total_boroughs: int
    avg_borough_opportunity_score: float
    highest_opportunity_borough: str
    lowest_opportunity_borough: str
    market_statistics: Dict[str, Any]
    last_updated: datetime
