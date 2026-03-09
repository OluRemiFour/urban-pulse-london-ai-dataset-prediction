"""
MongoDB database operations for Urban Pulse backend.
Uses Motor for async I/O operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from src.core.models import Property, BoroughMetrics
from src.core.config import settings

logger = logging.getLogger(__name__)


class MongoDatabase:
    """MongoDB database connection and operations."""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.properties_collection: Optional[AsyncIOMotorCollection] = None
        self.borough_metrics_collection: Optional[AsyncIOMotorCollection] = None
    
    async def connect(self):
        """Establish database connection."""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # Get collections
            self.properties_collection = self.db["properties"]
            self.borough_metrics_collection = self.db["borough_metrics"]
            
            # Create indexes for faster queries
            await self._create_indexes()
            
            # Verify connection
            await self.client.admin.command('ping')
            logger.info("✓ Connected to MongoDB successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
            return False
    
    async def disconnect(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("✓ Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes for optimized queries."""
        try:
            # Properties indexes
            await self.properties_collection.create_index([("zpid", 1)], unique=True)
            await self.properties_collection.create_index([("borough", 1)])
            await self.properties_collection.create_index([("latitude", 1), ("longitude", 1)])
            await self.properties_collection.create_index([("demand_score", -1)])
            await self.properties_collection.create_index([("opportunity_score", -1)])
            
            # Borough metrics indexes
            await self.borough_metrics_collection.create_index([("borough_name", 1)], unique=True)
            await self.borough_metrics_collection.create_index([("opportunity_score", -1)])
            await self.borough_metrics_collection.create_index([("rank", 1)])
            
            logger.info("✓ Database indexes created")
        except Exception as e:
            logger.warning(f"⚠ Warning creating indexes: {str(e)}")
    
    # ========================================================================
    # PROPERTY OPERATIONS
    # ========================================================================
    
    async def insert_properties(self, properties: List[Dict[str, Any]]) -> int:
        """Insert multiple properties. Returns count of inserted documents."""
        try:
            if not properties:
                return 0
            
            # Use insert_many with ordered=False to skip duplicates
            result = await self.properties_collection.insert_many(
                properties, 
                ordered=False
            )
            logger.info(f"✓ Inserted {len(result.inserted_ids)} properties")
            return len(result.inserted_ids)
        except Exception as e:
            logger.error(f"✗ Error inserting properties: {str(e)}")
            raise
    
    async def upsert_properties(self, properties: List[Dict[str, Any]]) -> int:
        """Upsert properties (insert or update). Returns count of upserted documents."""
        try:
            if not properties:
                return 0
            
            count = 0
            for prop in properties:
                result = await self.properties_collection.update_one(
                    {"zpid": prop.get("zpid")},
                    {"$set": prop},
                    upsert=True
                )
                if result.upserted_id or result.modified_count:
                    count += 1
            
            logger.info(f"✓ Upserted {count} properties")
            return count
        except Exception as e:
            logger.error(f"✗ Error upserting properties: {str(e)}")
            raise
    
    async def get_property_by_zpid(self, zpid: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single property by Zillow ID."""
        try:
            return await self.properties_collection.find_one({"zpid": zpid})
        except Exception as e:
            logger.error(f"✗ Error retrieving property: {str(e)}")
            return None
    
    async def get_properties_by_borough(
        self, 
        borough: str, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get properties for a specific borough with pagination."""
        try:
            cursor = self.properties_collection.find({"borough": borough})
            cursor.skip(skip).limit(limit).sort("demand_score", -1)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"✗ Error retrieving properties by borough: {str(e)}")
            return []
    
    async def count_properties_by_borough(self, borough: str) -> int:
        """Count properties in a borough."""
        try:
            return await self.properties_collection.count_documents({"borough": borough})
        except Exception as e:
            logger.error(f"✗ Error counting properties: {str(e)}")
            return 0
    
    async def get_top_properties(
        self, 
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get top properties by opportunity score."""
        try:
            cursor = self.properties_collection.find({})
            cursor.sort("demand_score", -1).skip(skip).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"✗ Error retrieving top properties: {str(e)}")
            return []
    
    async def search_properties(
        self,
        query: Dict[str, Any],
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Dict[str, Any]], int]:
        """Search properties with custom query. Returns (results, total_count)."""
        try:
            total = await self.properties_collection.count_documents(query)
            cursor = self.properties_collection.find(query)
            cursor.skip(skip).limit(limit).sort("demand_score", -1)
            results = await cursor.to_list(length=limit)
            return results, total
        except Exception as e:
            logger.error(f"✗ Error searching properties: {str(e)}")
            return [], 0
    
    # ========================================================================
    # BOROUGH METRICS OPERATIONS
    # ========================================================================
    
    async def insert_borough_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        """Insert borough metrics. Returns count inserted."""
        try:
            if not metrics:
                return 0
            
            result = await self.borough_metrics_collection.insert_many(metrics, ordered=False)
            logger.info(f"✓ Inserted {len(result.inserted_ids)} borough metrics")
            return len(result.inserted_ids)
        except Exception as e:
            logger.error(f"✗ Error inserting borough metrics: {str(e)}")
            raise
    
    async def upsert_borough_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        """Upsert borough metrics. Returns count upserted."""
        try:
            if not metrics:
                return 0
            
            count = 0
            for metric in metrics:
                result = await self.borough_metrics_collection.update_one(
                    {"borough_name": metric.get("borough_name")},
                    {"$set": metric},
                    upsert=True
                )
                if result.upserted_id or result.modified_count:
                    count += 1
            
            logger.info(f"✓ Upserted {count} borough metrics")
            return count
        except Exception as e:
            logger.error(f"✗ Error upserting borough metrics: {str(e)}")
            raise
    
    async def get_all_boroughs(self) -> List[Dict[str, Any]]:
        """Get all borough metrics sorted by opportunity score."""
        try:
            cursor = self.borough_metrics_collection.find({})
            cursor.sort("opportunity_score", -1)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"✗ Error retrieving all boroughs: {str(e)}")
            return []
    
    async def get_borough_by_name(self, borough_name: str) -> Optional[Dict[str, Any]]:
        """Get specific borough metrics."""
        try:
            return await self.borough_metrics_collection.find_one({"borough_name": borough_name})
        except Exception as e:
            logger.error(f"✗ Error retrieving borough: {str(e)}")
            return None
    
    async def get_top_boroughs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top N boroughs by opportunity score."""
        try:
            cursor = self.borough_metrics_collection.find({})
            cursor.sort("opportunity_score", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"✗ Error retrieving top boroughs: {str(e)}")
            return []
    
    async def get_analytics_summary(self) -> Dict[str, Any]:
        """Get system-wide analytics summary."""
        try:
            # Total properties
            total_properties = await self.properties_collection.count_documents({})
            
            # Total boroughs
            total_boroughs = await self.borough_metrics_collection.count_documents({})
            
            # Average opportunity score
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg_score": {"$avg": "$opportunity_score"}
                    }
                }
            ]
            result = await self.borough_metrics_collection.aggregate(pipeline).to_list(1)
            avg_opportunity = result[0]["avg_score"] if result else 0
            
            # Best and worst boroughs
            top = await self.get_top_boroughs(1)
            best_borough = top[0]["borough_name"] if top else "N/A"
            
            bottom = await self.borough_metrics_collection.find({}).sort("opportunity_score", 1).limit(1).to_list(1)
            worst_borough = bottom[0]["borough_name"] if bottom else "N/A"
            
            # Market statistics
            market_stats = await self._calculate_market_stats()
            
            return {
                "total_properties": total_properties,
                "total_boroughs": total_boroughs,
                "avg_borough_opportunity_score": round(avg_opportunity, 2),
                "highest_opportunity_borough": best_borough,
                "lowest_opportunity_borough": worst_borough,
                "market_statistics": market_stats,
                "last_updated": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"✗ Error calculating analytics: {str(e)}")
            return {}
    
    async def _calculate_market_stats(self) -> Dict[str, Any]:
        """Calculate overall market statistics."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg_price": {"$avg": "$price"},
                        "median_price": {"$avg": "$price"},
                        "avg_demand": {"$avg": "$demand_score"},
                        "avg_mobility": {"$avg": "$mobility_score"},
                        "avg_climate_risk": {"$avg": "$climate_risk_score"},
                        "property_count": {"$sum": 1}
                    }
                }
            ]
            result = await self.properties_collection.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                return {
                    "avg_price": round(stats.get("avg_price", 0), 2),
                    "avg_demand_score": round(stats.get("avg_demand", 0), 2),
                    "avg_mobility_score": round(stats.get("avg_mobility", 0), 2),
                    "avg_climate_risk": round(stats.get("avg_climate_risk", 0), 2),
                    "total_properties": stats.get("property_count", 0)
                }
            return {}
        except Exception as e:
            logger.error(f"✗ Error calculating market stats: {str(e)}")
            return {}
    
    async def clear_all_data(self):
        """Clear all data from collections (for reset/testing)."""
        try:
            await self.properties_collection.delete_many({})
            await self.borough_metrics_collection.delete_many({})
            logger.info("✓ Cleared all data from MongoDB")
        except Exception as e:
            logger.error(f"✗ Error clearing data: {str(e)}")
            raise


# Global database instance
db = MongoDatabase()
