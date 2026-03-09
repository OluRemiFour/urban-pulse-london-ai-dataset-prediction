"""
Data processing and feature engineering for Urban Pulse backend.
Handles data loading, cleaning, feature engineering, and opportunity scoring.
"""

import logging
import pandas as pd
import numpy as np
import geopandas as gpd
import re
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)


class DataProcessor:
    """Process Zillow data and compute borough-level metrics."""
    
    # Essential columns from Zillow dataset
    ESSENTIAL_COLS = [
        "zpid", "latitude", "longitude", "city", "zipcode", "county",
        "price", "zestimate", "rentZestimate", "lastSoldPrice",
        "bedrooms", "bathrooms", "livingArea", "sqft", "lotSize", "yearBuilt", "homeType",
        "daysOnZillow", "tourViewCount", "num_of_contacts", "num_of_applications",
        "sold_to_list_ratio", "getting_around_scores", "climate_risks",
        "homeStatus", "dateSold"
    ]
    
    # Default London boroughs (in case GeoJSON not available)
    DEFAULT_BOROUGHS = [
        "Westminster", "City of London", "Kensington and Chelsea", "Camden",
        "Islington", "Tower Hamlets", "Hackney", "Haringey",
        "Wandsworth", "Lambeth", "Southwark", "Lewisham",
        "Greenwich", "Bexley", "Havering", "Barking and Dagenham",
        "Newham", "Redbridge", "Waltham Forest", "Ealing",
        "Hounslow", "Richmond upon Thames", "Kingston upon Thames",
        "Merton", "Sutton", "Croydon", "Bromley", "Hillingdon"
    ]
    
    def __init__(self, data_path: str = settings.ZILLOW_DATA_PATH):
        self.data_path = data_path
        self.df_raw = None
        self.df_clean = None
        self.df_features = None
        self.gdf = None
    
    def load_data(self) -> bool:
        """Load Zillow dataset from CSV."""
        try:
            logger.info("Loading Zillow dataset...")
            self.df_raw = pd.read_csv(self.data_path)
            logger.info(f"✓ Loaded {len(self.df_raw)} properties")
            return True
        except FileNotFoundError:
            logger.error(f"✗ Data file not found: {self.data_path}")
            return False
        except Exception as e:
            logger.error(f"✗ Error loading data: {str(e)}")
            return False
    
    def filter_columns(self) -> None:
        """Keep only essential columns."""
        available_cols = [col for col in self.ESSENTIAL_COLS if col in self.df_raw.columns]
        missing_cols = [col for col in self.ESSENTIAL_COLS if col not in self.df_raw.columns]
        
        if missing_cols:
            logger.warning(f"⚠ Missing columns: {missing_cols}")
        
        self.df_clean = self.df_raw[available_cols].copy()
        logger.info(f"✓ Filtered to {len(available_cols)} columns")
    
    def clean_data(self) -> None:
        """Clean and prepare data."""
        logger.info("Cleaning data...")
        
        # Remove rows with missing critical location and pricing data
        initial_rows = len(self.df_clean)
        self.df_clean = self.df_clean.dropna(subset=['latitude', 'longitude', 'price'])
        logger.info(f"  Removed {initial_rows - len(self.df_clean)} rows with missing location/price")
        
        # Convert date columns
        date_cols = ['dateSold']
        for col in date_cols:
            if col in self.df_clean.columns:
                self.df_clean[col] = pd.to_datetime(self.df_clean[col], errors='coerce')
        
        # Convert numeric columns
        numeric_cols = ['price', 'zestimate', 'rentZestimate', 'lastSoldPrice',
                       'bedrooms', 'bathrooms', 'livingArea', 'sqft', 'lotSize',
                       'yearBuilt', 'daysOnZillow', 'tourViewCount',
                       'num_of_contacts', 'num_of_applications', 'sold_to_list_ratio',
                       'latitude', 'longitude']
        
        for col in numeric_cols:
            if col in self.df_clean.columns:
                self.df_clean[col] = pd.to_numeric(self.df_clean[col], errors='coerce')
        
        # Fill missing values
        for col in numeric_cols:
            if col in self.df_clean.columns:
                median_val = self.df_clean[col].median()
                if pd.notna(median_val):
                    self.df_clean[col].fillna(median_val, inplace=True)
        
        # Fill categorical columns
        cat_cols = ['homeStatus', 'homeType', 'city', 'county']
        for col in cat_cols:
            if col in self.df_clean.columns:
                self.df_clean[col].fillna('Unknown', inplace=True)
        
        logger.info(f"✓ Data cleaned: {len(self.df_clean)} properties remaining")
    
    def engineer_features(self) -> None:
        """Create derived features."""
        logger.info("Engineering features...")
        self.df_features = self.df_clean.copy()
        
        # Price per sqft
        self.df_features['price_per_sqft'] = np.where(
            self.df_features['sqft'] > 0,
            self.df_features['price'] / self.df_features['sqft'],
            np.nan
        )
        
        # Price growth
        self.df_features['price_growth'] = np.where(
            (self.df_features['lastSoldPrice'] > 0) & (self.df_features['price'] > 0),
            ((self.df_features['price'] - self.df_features['lastSoldPrice']) / 
             self.df_features['lastSoldPrice']) * 100,
            0
        )
        self.df_features['price_growth'].fillna(self.df_features['price_growth'].median(), inplace=True)
        
        # Demand score
        self.df_features['demand_score'] = self._compute_demand_score()
        
        # Mobility score
        self.df_features['mobility_score'] = self._extract_mobility_score()
        
        # Climate risk score
        self.df_features['climate_risk_score'] = self._extract_climate_risk_score()
        
        # Property quality score
        self.df_features['property_quality_score'] = self._compute_quality_score()
        
        # Opportunity score (property level)
        self.df_features['opportunity_score'] = (
            settings.WEIGHT_PRICE_GROWTH * self._normalize_column(self.df_features['price_growth']) +
            settings.WEIGHT_DEMAND_SCORE * self.df_features['demand_score'] +
            settings.WEIGHT_MOBILITY_SCORE * self.df_features['mobility_score'] +
            settings.WEIGHT_CLIMATE_RISK * (100 - self.df_features['climate_risk_score'])
        ).clip(0, 100)
        
        logger.info(f"✓ Features engineered: {len(self.df_features)} properties")
    
    def _compute_demand_score(self) -> pd.Series:
        """Compute normalized demand score (0-100)."""
        components = []
        
        # Days on Zillow (inverse - lower is better)
        if 'daysOnZillow' in self.df_features.columns:
            days = self.df_features['daysOnZillow']
            if days.max() > days.min():
                days_norm = 100 - ((days - days.min()) / (days.max() - days.min())) * 100
            else:
                days_norm = pd.Series([50] * len(days))
            components.append(days_norm * 0.25)
        
        # Tour view count
        if 'tourViewCount' in self.df_features.columns:
            views = self.df_features['tourViewCount']
            if views.max() > 0:
                views_norm = (views / views.max()) * 100
            else:
                views_norm = pd.Series([50] * len(views))
            components.append(views_norm * 0.35)
        
        # Number of contacts
        if 'num_of_contacts' in self.df_features.columns:
            contacts = self.df_features['num_of_contacts']
            if contacts.max() > 0:
                contacts_norm = (contacts / contacts.max()) * 100
            else:
                contacts_norm = pd.Series([50] * len(contacts))
            components.append(contacts_norm * 0.20)
        
        # Number of applications
        if 'num_of_applications' in self.df_features.columns:
            apps = self.df_features['num_of_applications']
            if apps.max() > 0:
                apps_norm = (apps / apps.max()) * 100
            else:
                apps_norm = pd.Series([50] * len(apps))
            components.append(apps_norm * 0.20)
        
        if components:
            result = pd.concat(components, axis=1).sum(axis=1).clip(0, 100)
        else:
            result = pd.Series([50] * len(self.df_features))
        
        return result
    
    def _extract_mobility_score(self) -> pd.Series:
        """Extract mobility score from getting_around_scores field."""
        scores = []
        
        for score in self.df_features['getting_around_scores'].fillna('50'):
            try:
                if pd.isna(score):
                    scores.append(50)
                else:
                    # Extract numeric values from string
                    numbers = re.findall(r'\d+', str(score))
                    if numbers:
                        avg_score = np.mean([int(n) for n in numbers[:3]])
                        scores.append(min(avg_score, 100))
                    else:
                        scores.append(50)
            except:
                scores.append(50)
        
        return pd.Series(scores)
    
    def _extract_climate_risk_score(self) -> pd.Series:
        """Extract and normalize climate risk score (0-100)."""
        scores = []
        
        for risk in self.df_features['climate_risks'].fillna('25'):
            try:
                if pd.isna(risk):
                    scores.append(25)
                else:
                    numbers = re.findall(r'\d+', str(risk))
                    if numbers:
                        avg_risk = np.mean([int(n) for n in numbers[:3]])
                        scores.append(min(avg_risk, 100))
                    else:
                        scores.append(25)
            except:
                scores.append(25)
        
        return pd.Series(scores)
    
    def _compute_quality_score(self) -> pd.Series:
        """Compute property quality score based on multiple factors."""
        components = []
        
        # Bedrooms (higher is better, capped at 5)
        if 'bedrooms' in self.df_features.columns:
            beds = (self.df_features['bedrooms'] / 5 * 100).clip(0, 100)
            components.append(beds * 0.20)
        
        # Bathrooms (higher is better, capped at 4)
        if 'bathrooms' in self.df_features.columns:
            baths = (self.df_features['bathrooms'] / 4 * 100).clip(0, 100)
            components.append(baths * 0.20)
        
        # Age (newer is better, 0-50 years)
        if 'yearBuilt' in self.df_features.columns:
            age = datetime.utcnow().year - self.df_features['yearBuilt']
            age_score = (100 - (age / 100 * 100)).clip(0, 100)
            components.append(age_score * 0.30)
        
        # Living area (larger is better)
        if 'livingArea' in self.df_features.columns:
            area = self.df_features['livingArea']
            if area.max() > 0:
                area_score = (area / area.max() * 100).clip(0, 100)
            else:
                area_score = pd.Series([50] * len(area))
            components.append(area_score * 0.30)
        
        if components:
            result = pd.concat(components, axis=1).sum(axis=1).clip(0, 100)
        else:
            result = pd.Series([50] * len(self.df_features))
        
        return result
    
    def _normalize_column(self, col: pd.Series) -> pd.Series:
        """Normalize column to 0-100 scale."""
        if col.max() == col.min():
            return pd.Series([50] * len(col))
        return ((col - col.min()) / (col.max() - col.min())) * 100
    
    def assign_boroughs(self, geojson_path: Optional[str] = None) -> None:
        """Assign properties to London boroughs using geospatial mapping."""
        logger.info("Assigning properties to boroughs...")
        
        # Create GeoDataFrame from properties
        self.gdf = gpd.GeoDataFrame(
            self.df_features,
            geometry=gpd.points_from_xy(self.df_features['longitude'], 
                                       self.df_features['latitude']),
            crs='EPSG:4326'
        )
        
        # Try to load borough boundaries from GeoJSON
        if geojson_path and Path(geojson_path).exists():
            try:
                logger.info(f"  Loading borough boundaries from {geojson_path}...")
                boroughs_gdf = gpd.read_file(geojson_path)
                
                # Spatial join
                self.gdf = gpd.sjoin(self.gdf, boroughs_gdf, how='left', predicate='within')
                
                # Rename borough column if needed
                if 'name' in self.gdf.columns:
                    self.gdf['borough'] = self.gdf['name']
                elif 'NAME' in self.gdf.columns:
                    self.gdf['borough'] = self.gdf['NAME']
                
                logger.info(f"✓ Assigned {self.gdf['borough'].notna().sum()} properties to boroughs")
            except Exception as e:
                logger.warning(f"⚠ Could not load GeoJSON: {str(e)}, using fallback method")
                self._assign_boroughs_fallback()
        else:
            logger.info("  Using fallback borough assignment method")
            self._assign_boroughs_fallback()
        
        # Update main dataframe
        self.df_features['borough'] = self.gdf['borough'].values
    
    def _assign_boroughs_fallback(self) -> None:
        """Fallback method to assign boroughs based on postcode or random approximation."""
        if 'zipcode' in self.df_features.columns:
            # Simple mapping based on postcode prefixes
            postcode_borough_map = {
                'SW': 'Wandsworth', 'SE': 'Southwark', 'N': 'Islington',
                'E': 'Tower Hamlets', 'W': 'Westminster', 'WC': 'Westminster',
                'EC': 'City of London', 'NW': 'Camden'
            }
            
            def map_postcode_to_borough(postcode):
                if pd.isna(postcode):
                    return np.random.choice(self.DEFAULT_BOROUGHS)
                postcode_str = str(postcode).upper()
                for prefix, borough in postcode_borough_map.items():
                    if postcode_str.startswith(prefix):
                        return borough
                return np.random.choice(self.DEFAULT_BOROUGHS)
            
            self.gdf['borough'] = self.gdf['zipcode'].apply(map_postcode_to_borough)
        else:
            self.gdf['borough'] = np.random.choice(self.DEFAULT_BOROUGHS, size=len(self.gdf))
        
        logger.info(f"✓ Assigned {len(self.gdf)} properties to boroughs (fallback method)")
    
    def compute_borough_metrics(self) -> pd.DataFrame:
        """Aggregate property-level data to borough level."""
        logger.info("Computing borough-level metrics...")
        
        borough_metrics = []
        
        for borough in self.gdf['borough'].unique():
            if pd.isna(borough):
                continue
            
            borough_data = self.gdf[self.gdf['borough'] == borough]
            
            # Compute aggregated metrics
            metrics = {
                'borough_name': borough,
                'property_count': len(borough_data),
                'avg_price': borough_data['price'].mean(),
                'avg_price_growth': borough_data['price_growth'].mean(),
                'avg_demand_score': borough_data['demand_score'].mean(),
                'avg_mobility_score': borough_data['mobility_score'].mean(),
                'avg_climate_risk_score': borough_data['climate_risk_score'].mean(),
                'avg_quality_score': borough_data['property_quality_score'].mean(),
                'median_price': borough_data['price'].median(),
                'price_range_min': borough_data['price'].min(),
                'price_range_max': borough_data['price'].max(),
                'avg_days_on_market': borough_data['daysOnZillow'].mean(),
                'avg_bedrooms': borough_data['bedrooms'].mean(),
                'avg_bathrooms': borough_data['bathrooms'].mean(),
            }
            
            # Compute opportunity score for borough
            metrics['opportunity_score'] = (
                settings.WEIGHT_PRICE_GROWTH * self._normalize_value(metrics['avg_price_growth'], 0, 20) +
                settings.WEIGHT_DEMAND_SCORE * metrics['avg_demand_score'] +
                settings.WEIGHT_MOBILITY_SCORE * metrics['avg_mobility_score'] +
                settings.WEIGHT_CLIMATE_RISK * (100 - metrics['avg_climate_risk_score'])
            ) / 1.0
            metrics['opportunity_score'] = max(0, min(100, metrics['opportunity_score']))
            
            metrics['created_at'] = datetime.utcnow()
            metrics['updated_at'] = datetime.utcnow()
            
            borough_metrics.append(metrics)
        
        metrics_df = pd.DataFrame(borough_metrics)
        
        # Add rankings
        metrics_df = metrics_df.sort_values('opportunity_score', ascending=False).reset_index(drop=True)
        metrics_df['rank'] = range(1, len(metrics_df) + 1)
        
        logger.info(f"✓ Computed metrics for {len(metrics_df)} boroughs")
        return metrics_df
    
    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to 0-100 scale."""
        if max_val == min_val:
            return 50
        return ((value - min_val) / (max_val - min_val)) * 100
    
    def get_properties_dict(self) -> List[Dict[str, Any]]:
        """Convert properties DataFrame to list of dictionaries for MongoDB."""
        if self.df_features is None:
            return []
        
        properties = []
        for _, row in self.df_features.iterrows():
            prop_dict = {
                'zpid': str(row.get('zpid', '')),
                'latitude': float(row.get('latitude', 0)),
                'longitude': float(row.get('longitude', 0)),
                'borough': row.get('borough', 'Unknown'),
                'price': float(row.get('price', 0)),
                'zestimate': float(row.get('zestimate', 0)) if pd.notna(row.get('zestimate')) else None,
                'bedrooms': float(row.get('bedrooms', 0)) if pd.notna(row.get('bedrooms')) else None,
                'bathrooms': float(row.get('bathrooms', 0)) if pd.notna(row.get('bathrooms')) else None,
                'sqft': float(row.get('sqft', 0)) if pd.notna(row.get('sqft')) else None,
                'demand_score': float(row.get('demand_score', 50)),
                'mobility_score': float(row.get('mobility_score', 50)),
                'climate_risk_score': float(row.get('climate_risk_score', 25)),
                'property_quality_score': float(row.get('property_quality_score', 50)),
                'opportunity_score': float(row.get('opportunity_score', 50)),
                'price_per_sqft': float(row.get('price_per_sqft', 0)) if pd.notna(row.get('price_per_sqft')) else None,
                'price_growth': float(row.get('price_growth', 0)),
                'daysOnZillow': int(row.get('daysOnZillow', 0)),
                'tourViewCount': int(row.get('tourViewCount', 0)),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            properties.append(prop_dict)
        
        return properties
    
    def process_full_pipeline(self, geojson_path: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
        """Run complete data processing pipeline. Returns (properties_list, borough_metrics_list)."""
        if not self.load_data():
            return [], []
        
        self.filter_columns()
        self.clean_data()
        self.engineer_features()
        self.assign_boroughs(geojson_path)
        
        borough_metrics_df = self.compute_borough_metrics()
        properties_list = self.get_properties_dict()
        borough_list = borough_metrics_df.to_dict('records')
        
        logger.info(f"✓ Processing complete: {len(properties_list)} properties, {len(borough_list)} boroughs")
        
        return properties_list, borough_list
