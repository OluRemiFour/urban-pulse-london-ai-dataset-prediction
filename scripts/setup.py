"""
Setup and initialization script for Urban Pulse backend.
Handles database setup, data loading, and system initialization.
"""

import asyncio
import logging
import sys
from pathlib import Path
from src.pipeline.data_processor import DataProcessor
from src.core.database import db
from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_database():
    """Initialize MongoDB connection and create indexes."""
    logger.info("Setting up MongoDB...")
    
    if not await db.connect():
        logger.error("Failed to connect to MongoDB")
        return False
    
    logger.info("✓ MongoDB connected successfully")
    return True


async def load_zillow_data(clear_existing: bool = False):
    """Load and process Zillow data into MongoDB."""
    logger.info("Loading Zillow property data...")
    
    if not Path(settings.ZILLOW_DATA_PATH).exists():
        logger.error(f"Data file not found: {settings.ZILLOW_DATA_PATH}")
        return False
    
    try:
        # Clear existing data if requested
        if clear_existing:
            logger.warning("Clearing existing data...")
            await db.clear_all_data()
        
        # Process data
        processor = DataProcessor(settings.ZILLOW_DATA_PATH)
        properties_list, borough_list = processor.process_full_pipeline(
            geojson_path=settings.GEOJSON_PATH
        )
        
        if not properties_list:
            logger.error("No data to load")
            return False
        
        # Insert data
        logger.info("Inserting properties into database...")
        properties_count = await db.upsert_properties(properties_list)
        
        logger.info("Inserting borough metrics into database...")
        boroughs_count = await db.upsert_borough_metrics(borough_list)
        
        logger.info(f"✓ Data loaded successfully")
        logger.info(f"  Properties: {properties_count}")
        logger.info(f"  Boroughs: {boroughs_count}")
        
        return True
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return False


async def verify_data():
    """Verify data was loaded correctly."""
    logger.info("Verifying data...")
    
    try:
        # Count properties
        properties_count = await db.properties_collection.count_documents({})
        logger.info(f"  Properties in database: {properties_count}")
        
        # Count boroughs
        boroughs_count = await db.borough_metrics_collection.count_documents({})
        logger.info(f"  Boroughs with metrics: {boroughs_count}")
        
        # Get top borough
        top_boroughs = await db.get_top_boroughs(1)
        if top_boroughs:
            top = top_boroughs[0]
            logger.info(f"  Top borough: {top['borough_name']} (score: {top['opportunity_score']:.1f})")
        
        return properties_count > 0 and boroughs_count > 0
    except Exception as e:
        logger.error(f"Error verifying data: {str(e)}")
        return False


async def main():
    """Run main setup process."""
    logger.info("=" * 70)
    logger.info("Urban Pulse Backend - Setup & Initialization")
    logger.info("=" * 70)
    
    # Step 1: Connect to database
    if not await setup_database():
        logger.error("Setup failed at database connection")
        sys.exit(1)
    
    # Step 2: Load data
    clear_existing = len(sys.argv) > 1 and sys.argv[1] == "--clear"
    if not await load_zillow_data(clear_existing=clear_existing):
        logger.error("Setup failed at data loading")
        sys.exit(1)
    
    # Step 3: Verify data
    if not await verify_data():
        logger.error("Setup failed at data verification")
        sys.exit(1)
    
    # Step 4: Disconnect
    await db.disconnect()
    
    logger.info("=" * 70)
    logger.info("✓ Setup completed successfully!")
    logger.info("=" * 70)
    logger.info("\nNext steps:")
    logger.info("  1. Start the API: uvicorn app:app --reload")
    logger.info("  2. Visit: http://localhost:8000/docs")
    logger.info("  3. Query endpoints to verify data")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
