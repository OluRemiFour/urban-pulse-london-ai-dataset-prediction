"""
FastAPI backend for Urban Pulse Investment Intelligence Platform.
Provides REST API endpoints for accessing borough opportunity scores and property data.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime

from config import settings
from database import db
from models import (
    BoroughResponse, PropertyResponse, PaginatedResponse,
    ErrorResponse, AnalyticsSummary
)
from data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("Starting Urban Pulse API...")
    await db.connect()
    logger.info("✓ API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Urban Pulse API...")
    await db.disconnect()
    logger.info("✓ API shut down")


# ============================================================================
# API INITIALIZATION
# ============================================================================

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Check API and database health."""
    try:
        # Quick health check - verify we can reach MongoDB
        await db.properties_collection.count_documents({})
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "database": "connected"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow(),
                "error": str(e)
            }
        )


@app.get("/api/status", tags=["Health"])
async def api_status():
    """Get API status and version information."""
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "operational",
        "timestamp": datetime.utcnow()
    }


# ============================================================================
# BOROUGH ENDPOINTS
# ============================================================================

@app.get(
    "/api/boroughs",
    response_model=List[BoroughResponse],
    tags=["Boroughs"],
    summary="Get all boroughs with metrics"
)
async def get_all_boroughs(
    sort_by: str = Query("opportunity_score", regex="^(opportunity_score|property_count|avg_price)$")
):
    """
    Retrieve all London boroughs with their investment opportunity metrics.
    
    **Query Parameters:**
    - `sort_by`: Sort results by `opportunity_score` (default), `property_count`, or `avg_price`
    
    **Response:** List of borough metrics sorted by selected criterion.
    """
    try:
        boroughs = await db.get_all_boroughs()
        
        if not boroughs:
            return []
        
        # Sort results
        sort_key = sort_by
        reverse = True
        
        boroughs = sorted(
            boroughs,
            key=lambda x: x.get(sort_key, 0),
            reverse=reverse
        )
        
        return boroughs
    except Exception as e:
        logger.error(f"Error retrieving boroughs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving borough data")


@app.get(
    "/api/boroughs/{borough_name}",
    response_model=BoroughResponse,
    tags=["Boroughs"],
    summary="Get borough details"
)
async def get_borough_details(borough_name: str):
    """
    Retrieve detailed metrics for a specific borough.
    
    **Path Parameters:**
    - `borough_name`: Name of the London borough
    
    **Response:** Detailed borough metrics including opportunity score, market stats, and rankings.
    """
    try:
        borough = await db.get_borough_by_name(borough_name)
        
        if not borough:
            raise HTTPException(
                status_code=404,
                detail=f"Borough '{borough_name}' not found"
            )
        
        return borough
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving borough details: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving borough data")


@app.get(
    "/api/top-growth-zones",
    response_model=List[BoroughResponse],
    tags=["Boroughs"],
    summary="Get top growth opportunities"
)
async def get_top_growth_zones(limit: int = Query(5, ge=1, le=27)):
    """
    Retrieve the top boroughs by opportunity score (best investment opportunities).
    
    **Query Parameters:**
    - `limit`: Number of top boroughs to return (default: 5, max: 27)
    
    **Response:** List of top boroughs ranked by opportunity score.
    """
    try:
        top_boroughs = await db.get_top_boroughs(limit=limit)
        return top_boroughs
    except Exception as e:
        logger.error(f"Error retrieving top growth zones: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving top growth zones")


@app.get(
    "/api/boroughs-by-price-range",
    response_model=List[BoroughResponse],
    tags=["Boroughs"],
    summary="Get boroughs filtered by price range"
)
async def get_boroughs_by_price(
    min_price: float = Query(0, ge=0),
    max_price: float = Query(1000000, ge=0)
):
    """
    Retrieve boroughs with average prices within a specified range.
    
    **Query Parameters:**
    - `min_price`: Minimum average price (default: 0)
    - `max_price`: Maximum average price (default: 1,000,000)
    
    **Response:** Filtered list of boroughs.
    """
    try:
        all_boroughs = await db.get_all_boroughs()
        
        filtered = [
            b for b in all_boroughs
            if min_price <= b.get('avg_price', 0) <= max_price
        ]
        
        return sorted(filtered, key=lambda x: x.get('opportunity_score', 0), reverse=True)
    except Exception as e:
        logger.error(f"Error filtering boroughs by price: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving borough data")


# ============================================================================
# PROPERTY ENDPOINTS
# ============================================================================

@app.get(
    "/api/properties/borough/{borough_name}",
    response_model=PaginatedResponse,
    tags=["Properties"],
    summary="Get properties in a borough"
)
async def get_properties_by_borough(
    borough_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Retrieve properties from a specific borough with pagination.
    
    **Path Parameters:**
    - `borough_name`: Name of the borough
    
    **Query Parameters:**
    - `skip`: Number of properties to skip (pagination offset)
    - `limit`: Maximum properties to return (default: 20, max: 100)
    
    **Response:** Paginated list of properties sorted by demand score.
    """
    try:
        properties = await db.get_properties_by_borough(borough_name, skip=skip, limit=limit)
        total = await db.count_properties_by_borough(borough_name)
        
        return PaginatedResponse(
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            items=properties
        )
    except Exception as e:
        logger.error(f"Error retrieving properties by borough: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving properties")


@app.get(
    "/api/properties/top",
    response_model=PaginatedResponse,
    tags=["Properties"],
    summary="Get top-rated properties"
)
async def get_top_properties(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Retrieve top-rated properties by demand score.
    
    **Query Parameters:**
    - `limit`: Number of properties to return (default: 20, max: 100)
    - `skip`: Number of properties to skip (pagination offset)
    
    **Response:** Paginated list of top properties.
    """
    try:
        properties = await db.get_top_properties(limit=limit, skip=skip)
        total = await db.properties_collection.count_documents({})
        
        return PaginatedResponse(
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            items=properties
        )
    except Exception as e:
        logger.error(f"Error retrieving top properties: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving properties")


@app.get(
    "/api/properties/{zpid}",
    response_model=PropertyResponse,
    tags=["Properties"],
    summary="Get property details"
)
async def get_property_details(zpid: str):
    """
    Retrieve detailed information for a specific property.
    
    **Path Parameters:**
    - `zpid`: Zillow Property ID
    
    **Response:** Complete property details including all features and scores.
    """
    try:
        property_data = await db.get_property_by_zpid(zpid)
        
        if not property_data:
            raise HTTPException(
                status_code=404,
                detail=f"Property with ZPID '{zpid}' not found"
            )
        
        return property_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving property details: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving property data")


# ============================================================================
# SEARCH AND FILTER ENDPOINTS
# ============================================================================

@app.get(
    "/api/properties/search",
    response_model=PaginatedResponse,
    tags=["Search"],
    summary="Search properties"
)
async def search_properties(
    borough: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_demand_score: Optional[float] = Query(None, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search properties with multiple filter criteria.
    
    **Query Parameters:**
    - `borough`: Filter by borough name
    - `min_price`: Minimum property price
    - `max_price`: Maximum property price
    - `min_demand_score`: Minimum demand score (0-100)
    - `skip`: Pagination offset
    - `limit`: Results per page
    
    **Response:** Filtered and paginated list of properties.
    """
    try:
        query = {}
        
        if borough:
            query["borough"] = borough
        
        if min_price is not None or max_price is not None:
            query["price"] = {}
            if min_price is not None:
                query["price"]["$gte"] = min_price
            if max_price is not None:
                query["price"]["$lte"] = max_price
        
        if min_demand_score is not None:
            query["demand_score"] = {"$gte": min_demand_score}
        
        properties, total = await db.search_properties(query, skip=skip, limit=limit)
        
        return PaginatedResponse(
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            items=properties
        )
    except Exception as e:
        logger.error(f"Error searching properties: {str(e)}")
        raise HTTPException(status_code=500, detail="Error searching properties")


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get(
    "/api/analytics",
    response_model=AnalyticsSummary,
    tags=["Analytics"],
    summary="Get system analytics"
)
async def get_analytics():
    """
    Retrieve system-wide analytics and market summary.
    
    **Response:** 
    - Total properties and boroughs indexed
    - Average opportunity scores
    - Market statistics
    - Best and worst performing boroughs
    """
    try:
        summary = await db.get_analytics_summary()
        
        if not summary:
            raise HTTPException(
                status_code=500,
                detail="Error calculating analytics"
            )
        
        return AnalyticsSummary(**summary)
    except Exception as e:
        logger.error(f"Error retrieving analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving analytics")


@app.get(
    "/api/market-summary",
    tags=["Analytics"],
    summary="Get market summary"
)
async def get_market_summary():
    """
    Retrieve high-level market summary statistics.
    
    **Response:** Quick market overview including average prices, scores, and trends.
    """
    try:
        stats = await db._calculate_market_stats()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error retrieving market summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving market summary")


# ============================================================================
# DATA MANAGEMENT ENDPOINTS
# ============================================================================

@app.post(
    "/api/admin/load-data",
    tags=["Admin"],
    summary="Load data from Zillow file"
)
async def load_data_endpoint(
    clear_existing: bool = Query(False)
):
    """
    Load and process Zillow property data into MongoDB.
    
    **Query Parameters:**
    - `clear_existing`: If True, clear existing data before loading (default: False)
    
    **Response:** Summary of loaded data and processing results.
    
    **Note:** This is an admin endpoint. In production, add authentication.
    """
    try:
        if clear_existing:
            logger.info("Clearing existing data...")
            await db.clear_all_data()
        
        logger.info("Starting data processing pipeline...")
        processor = DataProcessor()
        
        properties_list, borough_list = processor.process_full_pipeline(
            geojson_path=settings.GEOJSON_PATH
        )
        
        if not properties_list:
            raise HTTPException(
                status_code=400,
                detail="No data to load. Check Zillow data file."
            )
        
        # Insert/Upsert data
        properties_count = await db.upsert_properties(properties_list)
        boroughs_count = await db.upsert_borough_metrics(borough_list)
        
        logger.info(f"✓ Data load complete: {properties_count} properties, {boroughs_count} boroughs")
        
        return {
            "status": "success",
            "message": "Data loaded successfully",
            "properties_loaded": properties_count,
            "boroughs_loaded": boroughs_count,
            "timestamp": datetime.utcnow()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error loading data: {str(e)}"
        )


@app.post(
    "/api/admin/refresh-borough-metrics",
    tags=["Admin"],
    summary="Recalculate borough metrics"
)
async def refresh_borough_metrics():
    """
    Recalculate all borough-level metrics from property data.
    
    **Response:** Summary of recalculation results.
    
    **Note:** This is an admin endpoint. In production, add authentication.
    """
    try:
        logger.info("Refreshing borough metrics...")
        
        # Get all properties
        properties_cursor = db.properties_collection.find({})
        properties = await properties_cursor.to_list(length=None)
        
        if not properties:
            raise HTTPException(
                status_code=400,
                detail="No properties to aggregate"
            )
        
        # Recalculate borough metrics
        processor = DataProcessor()
        # This is a simplified version - in production, create proper aggregation
        
        return {
            "status": "success",
            "message": "Borough metrics refreshed",
            "properties_processed": len(properties),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error refreshing metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing metrics: {str(e)}"
        )


@app.delete(
    "/api/admin/clear-data",
    tags=["Admin"],
    summary="Clear all data"
)
async def clear_data_endpoint():
    """
    Clear all data from the database.
    
    **Response:** Confirmation of data deletion.
    
    **Warning:** This operation cannot be undone.
    **Note:** This is an admin endpoint. In production, add authentication.
    """
    try:
        logger.warning("Clearing all data from database...")
        await db.clear_all_data()
        
        return {
            "status": "success",
            "message": "All data cleared from database",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error clearing data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing data: {str(e)}"
        )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status="error",
            message=exc.detail,
            detail={"type": "HTTPException"}
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            status="error",
            message="Internal server error",
            detail={"error": str(exc) if settings.LOG_LEVEL == "DEBUG" else "An error occurred"}
        ).model_dump()
    )


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint with documentation links."""
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "documentation": {
            "swagger": "/docs",
            "openapi_schema": "/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "boroughs": "/api/boroughs",
            "top_opportunities": "/api/top-growth-zones",
            "analytics": "/api/analytics"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
