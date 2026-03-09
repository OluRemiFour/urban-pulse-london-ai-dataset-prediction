"""
Urban Pulse London - Investment Intelligence Platform
Data Pipeline for Housing Market Analysis

This pipeline processes Zillow property data and generates borough-level
investment opportunity scores based on housing market signals.
"""

import pandas as pd
import numpy as np
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_FILE = 'zillow_properties_listing.csv'
OUTPUT_FILE = 'urban_pulse_borough_metrics.csv'
PROPERTY_LEVEL_OUTPUT = 'urban_pulse_properties_clean.csv'

# Essential columns to keep for analysis
ESSENTIAL_COLS = [
    "zpid", "latitude", "longitude", "city", "zipcode", "county",
    "price", "zestimate", "rentZestimate", "lastSoldPrice", "priceHistory",
    "bedrooms", "bathrooms", "livingArea", "sqft", "lotSize", "yearBuilt", "homeType",
    "daysOnZillow", "tourViewCount", "num_of_contacts", "num_of_applications",
    "sold_to_list_ratio", "getting_around_scores", "climate_risks",
    "homeStatus", "listingTypeDimension", "isOffMarket", "dateSold", "availability_date"
]

# ============================================================================
# STEP 1: LOAD DATASET
# ============================================================================

def load_dataset(filepath):
    """Load Zillow dataset from CSV."""
    print("\n" + "="*70)
    print("STEP 1: LOADING DATASET")
    print("="*70)
    
    try:
        df = pd.read_csv(filepath)
        print(f"✓ Dataset loaded successfully")
        print(f"  Shape: {df.shape} (rows, columns)")
        print(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        return df
    except FileNotFoundError:
        print(f"✗ Error: File '{filepath}' not found")
        raise


# ============================================================================
# STEP 2: FILTER COLUMNS
# ============================================================================

def filter_columns(df, essential_cols):
    """Keep only essential columns for urban analysis."""
    print("\n" + "="*70)
    print("STEP 2: FILTERING COLUMNS")
    print("="*70)
    
    # Check which columns exist
    missing_cols = [col for col in essential_cols if col not in df.columns]
    available_cols = [col for col in essential_cols if col in df.columns]
    
    if missing_cols:
        print(f"⚠ Missing columns ({len(missing_cols)}): {missing_cols}")
    
    df_filtered = df[available_cols].copy()
    
    print(f"✓ Filtered to {len(available_cols)} essential columns")
    print(f"  Shape: {df_filtered.shape}")
    
    return df_filtered


# ============================================================================
# STEP 3: CLEAN DATA
# ============================================================================

def clean_data(df):
    """Clean and prepare data for analysis."""
    print("\n" + "="*70)
    print("STEP 3: CLEANING DATA")
    print("="*70)
    
    df_clean = df.copy()
    initial_rows = len(df_clean)
    
    # 3.1: Remove rows with missing critical location and pricing data
    print("\n3.1: Removing rows with missing critical data...")
    df_clean = df_clean.dropna(subset=['latitude', 'longitude', 'price'])
    print(f"  Rows after removing missing location/price: {len(df_clean)} (removed: {initial_rows - len(df_clean)})")
    
    # 3.2: Convert date columns to datetime
    print("\n3.2: Converting date columns to datetime...")
    date_cols = ['dateSold', 'availability_date']
    for col in date_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
    print(f"  ✓ Date columns converted")
    
    # 3.3: Ensure numeric columns are numeric
    print("\n3.3: Converting numeric columns...")
    numeric_cols = ['price', 'zestimate', 'rentZestimate', 'lastSoldPrice', 
                    'bedrooms', 'bathrooms', 'livingArea', 'sqft', 'lotSize', 
                    'yearBuilt', 'daysOnZillow', 'tourViewCount', 
                    'num_of_contacts', 'num_of_applications', 'sold_to_list_ratio',
                    'latitude', 'longitude']
    
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    print(f"  ✓ Numeric columns converted")
    
    # 3.4: Handle missing values strategically
    print("\n3.4: Handling missing values...")
    
    # Fill numeric columns with median
    for col in numeric_cols:
        if col in df_clean.columns and df_clean[col].dtype in ['float64', 'int64']:
            missing_before = df_clean[col].isnull().sum()
            if missing_before > 0:
                median_val = df_clean[col].median()
                df_clean[col].fillna(median_val, inplace=True)
                print(f"  - {col}: filled {missing_before} NaNs with median ({median_val:.2f})")
    
    # Fill categorical/text columns with 'Unknown'
    categorical_cols = ['homeStatus', 'listingTypeDimension', 'homeType', 'city', 'county']
    for col in categorical_cols:
        if col in df_clean.columns:
            missing_before = df_clean[col].isnull().sum()
            if missing_before > 0:
                df_clean[col].fillna('Unknown', inplace=True)
                print(f"  - {col}: filled {missing_before} NaNs with 'Unknown'")
    
    print(f"\n✓ Data cleaning complete")
    print(f"  Final shape: {df_clean.shape}")
    print(f"  Remaining NaN count: {df_clean.isnull().sum().sum()}")
    
    return df_clean


# ============================================================================
# STEP 4: FEATURE ENGINEERING
# ============================================================================

def engineer_features(df):
    """Create derived features for analysis."""
    print("\n" + "="*70)
    print("STEP 4: FEATURE ENGINEERING")
    print("="*70)
    
    df_fe = df.copy()
    
    # 4.1: Price Per Square Foot
    print("\n4.1: Creating price_per_sqft...")
    df_fe['price_per_sqft'] = np.where(
        df_fe['sqft'] > 0,
        df_fe['price'] / df_fe['sqft'],
        np.nan
    )
    print(f"  ✓ price_per_sqft created")
    
    # 4.2: Price Growth (estimated from lastSoldPrice and current price if available)
    print("\n4.2: Estimating price_growth...")
    df_fe['price_growth'] = np.where(
        (df_fe['lastSoldPrice'] > 0) & (df_fe['price'] > 0),
        ((df_fe['price'] - df_fe['lastSoldPrice']) / df_fe['lastSoldPrice']) * 100,
        np.nan
    )
    # Fill missing price growth with median
    median_growth = df_fe['price_growth'].median()
    df_fe['price_growth'].fillna(median_growth, inplace=True)
    print(f"  ✓ price_growth created (median: {median_growth:.2f}%)")
    
    # 4.3: Demand Score (normalized 0-100)
    print("\n4.3: Creating demand_score...")
    demand_score = normalize_demand_score(df_fe)
    df_fe['demand_score'] = demand_score
    print(f"  ✓ demand_score created (mean: {demand_score.mean():.2f}, range: {demand_score.min():.2f}-{demand_score.max():.2f})")
    
    # 4.4: Mobility Score (extract from getting_around_scores)
    print("\n4.4: Creating mobility_score...")
    mobility_score = extract_mobility_score(df_fe)
    df_fe['mobility_score'] = mobility_score
    print(f"  ✓ mobility_score created (mean: {mobility_score.mean():.2f})")
    
    # 4.5: Climate Risk Score (extract and normalize)
    print("\n4.5: Creating climate_risk_score...")
    climate_risk = extract_climate_risk_score(df_fe)
    df_fe['climate_risk_score'] = climate_risk
    print(f"  ✓ climate_risk_score created (mean: {climate_risk.mean():.2f})")
    
    # 4.6: Listing Age (days on market)
    print("\n4.6: Creating listing_age_days...")
    df_fe['listing_age_days'] = df_fe['daysOnZillow'].fillna(df_fe['daysOnZillow'].median())
    print(f"  ✓ listing_age_days created")
    
    # 4.7: Property Quality Score (based on beds, baths, year built, area)
    print("\n4.7: Creating property_quality_score...")
    quality_score = create_property_quality_score(df_fe)
    df_fe['property_quality_score'] = quality_score
    print(f"  ✓ property_quality_score created (mean: {quality_score.mean():.2f})")
    
    print(f"\n✓ Feature engineering complete")
    print(f"  New features created: 7")
    print(f"  Total columns now: {len(df_fe.columns)}")
    
    return df_fe


def normalize_demand_score(df):
    """
    Create normalized demand score (0-100) from:
    - daysOnZillow (inverse - lower is better)
    - tourViewCount (higher is better)
    - num_of_contacts (higher is better)
    - num_of_applications (higher is better)
    """
    components = []
    
    # Days on Zillow (inverse) - normalize to 0-100
    if df['daysOnZillow'].notna().any():
        days_normalized = 100 - ((df['daysOnZillow'] - df['daysOnZillow'].min()) / 
                                 (df['daysOnZillow'].max() - df['daysOnZillow'].min() + 1)) * 100
        days_normalized = days_normalized.clip(0, 100)
        components.append(days_normalized * 0.25)
    
    # Tour View Count - normalize to 0-100
    if df['tourViewCount'].notna().any() and df['tourViewCount'].max() > 0:
        views_normalized = (df['tourViewCount'] - df['tourViewCount'].min()) / \
                          (df['tourViewCount'].max() - df['tourViewCount'].min() + 1) * 100
        views_normalized = views_normalized.clip(0, 100)
        components.append(views_normalized * 0.35)
    
    # Number of Contacts - normalize to 0-100
    if df['num_of_contacts'].notna().any() and df['num_of_contacts'].max() > 0:
        contacts_normalized = (df['num_of_contacts'] - df['num_of_contacts'].min()) / \
                             (df['num_of_contacts'].max() - df['num_of_contacts'].min() + 1) * 100
        contacts_normalized = contacts_normalized.clip(0, 100)
        components.append(contacts_normalized * 0.20)
    
    # Number of Applications - normalize to 0-100
    if df['num_of_applications'].notna().any() and df['num_of_applications'].max() > 0:
        apps_normalized = (df['num_of_applications'] - df['num_of_applications'].min()) / \
                         (df['num_of_applications'].max() - df['num_of_applications'].min() + 1) * 100
        apps_normalized = apps_normalized.clip(0, 100)
        components.append(apps_normalized * 0.20)
    
    if components:
        return pd.concat(components, axis=1).sum(axis=1).clip(0, 100)
    else:
        return pd.Series([50] * len(df))


def extract_mobility_score(df):
    """
    Extract mobility scores from getting_around_scores.
    This field typically contains JSON or comma-separated walk/transit/bike scores.
    """
    mobility_scores = []
    
    for score in df['getting_around_scores']:
        try:
            if pd.isna(score):
                mobility_scores.append(50)  # Default neutral score
            elif isinstance(score, str):
                # Try to extract numeric values
                import re
                numbers = re.findall(r'\d+', str(score))
                if numbers:
                    avg_score = np.mean([int(n) for n in numbers[:3]])  # Take first 3 (walk, transit, bike)
                    mobility_scores.append(min(avg_score, 100))
                else:
                    mobility_scores.append(50)
            else:
                mobility_scores.append(50)
        except:
            mobility_scores.append(50)
    
    return pd.Series(mobility_scores)


def extract_climate_risk_score(df):
    """
    Extract and normalize climate risk score from climate_risks field.
    Combines flood/heat/storm risk into single normalized score (0-100).
    """
    climate_scores = []
    
    for risk in df['climate_risks']:
        try:
            if pd.isna(risk):
                climate_scores.append(25)  # Default moderate risk
            elif isinstance(risk, str):
                # Try to extract numeric values
                import re
                numbers = re.findall(r'[\d.]+', str(risk))
                if numbers:
                    avg_risk = np.mean([float(n) for n in numbers[:3]])
                    climate_scores.append(min(max(avg_risk, 0), 100))
                else:
                    climate_scores.append(25)
            else:
                climate_scores.append(25)
        except:
            climate_scores.append(25)
    
    return pd.Series(climate_scores)


def create_property_quality_score(df):
    """
    Create property quality score based on:
    - Bedrooms
    - Bathrooms
    - Year Built (newer is better)
    - Living Area
    """
    quality_scores = []
    
    for idx, row in df.iterrows():
        try:
            score = 0
            
            # Bedrooms (max 5 bedrooms = 25 points)
            score += min((row['bedrooms'] or 0) * 5, 25)
            
            # Bathrooms (max 3 bathrooms = 25 points)
            score += min((row['bathrooms'] or 0) * 8.33, 25)
            
            # Year Built (0-25 points based on age)
            current_year = datetime.now().year
            age = current_year - (row['yearBuilt'] or 2000)
            age = max(0, min(age, 100))  # Cap between 0-100
            score += (100 - age) * 0.25
            
            # Living Area (0-25 points, 5000+ sqft = max points)
            living_area = row['livingArea'] or 0
            score += min((living_area / 5000) * 25, 25)
            
            quality_scores.append(score)
        except:
            quality_scores.append(50)  # Default score
    
    return pd.Series(quality_scores).clip(0, 100)


# ============================================================================
# STEP 5: GEOSPATIAL AGGREGATION (Borough Mapping)
# ============================================================================

def map_to_borough(df):
    """
    Map properties to London boroughs using latitude/longitude.
    Here we use city/county as proxy if available, or create zones based on location.
    """
    print("\n" + "="*70)
    print("STEP 5: GEOSPATIAL AGGREGATION (Borough Mapping)")
    print("="*70)
    
    df_geo = df.copy()
    
    # Method 1: Use city/county as borough proxy
    if 'city' in df_geo.columns:
        df_geo['borough'] = df_geo['city'].fillna('Unknown')
        print(f"✓ Mapped properties to {df_geo['borough'].nunique()} unique cities/boroughs")
    elif 'county' in df_geo.columns:
        df_geo['borough'] = df_geo['county'].fillna('Unknown')
        print(f"✓ Mapped properties to {df_geo['borough'].nunique()} unique counties/boroughs")
    else:
        print("⚠ No city/county found, creating geographic zones")
        # Create zones based on zipcode
        df_geo['borough'] = df_geo['zipcode'].fillna('Unknown')
    
    print(f"  Total properties mapped: {len(df_geo)}")
    print(f"  Top 5 boroughs: ")
    for borough, count in df_geo['borough'].value_counts().head().items():
        print(f"    - {borough}: {count} properties")
    
    return df_geo


# ============================================================================
# STEP 6: BOROUGH-LEVEL AGGREGATION
# ============================================================================

def aggregate_by_borough(df):
    """Aggregate property-level metrics to borough level."""
    print("\n" + "="*70)
    print("STEP 6: BOROUGH-LEVEL AGGREGATION")
    print("="*70)
    
    # Group by borough
    borough_groups = df.groupby('borough')
    
    # Create aggregated metrics
    borough_metrics = pd.DataFrame({
        'borough_name': borough_groups['borough'].first(),
        'property_count': borough_groups.size(),
        'avg_price': borough_groups['price'].mean(),
        'median_price': borough_groups['price'].median(),
        'avg_price_per_sqft': borough_groups['price_per_sqft'].mean(),
        'avg_price_growth': borough_groups['price_growth'].mean(),
        'avg_demand_score': borough_groups['demand_score'].mean(),
        'avg_mobility_score': borough_groups['mobility_score'].mean(),
        'avg_climate_risk_score': borough_groups['climate_risk_score'].mean(),
        'avg_property_quality': borough_groups['property_quality_score'].mean(),
        'avg_daysOnZillow': borough_groups['daysOnZillow'].mean(),
        'total_tourViewCount': borough_groups['tourViewCount'].sum(),
        'total_num_of_applications': borough_groups['num_of_applications'].sum(),
        'avg_bedrooms': borough_groups['bedrooms'].mean(),
        'avg_bathrooms': borough_groups['bathrooms'].mean(),
        'avg_livingArea': borough_groups['livingArea'].mean(),
    }).reset_index(drop=True)
    
    print(f"✓ Aggregated to {len(borough_metrics)} boroughs")
    print(f"\nBorough Summary Statistics:")
    print(f"  Average properties per borough: {borough_metrics['property_count'].mean():.0f}")
    print(f"  Borough price range: £{borough_metrics['avg_price'].min():,.0f} - £{borough_metrics['avg_price'].max():,.0f}")
    
    return borough_metrics


# ============================================================================
# STEP 7: CALCULATE OPPORTUNITY SCORE
# ============================================================================

def calculate_opportunity_score(df):
    """
    Calculate borough-level Opportunity Score.
    
    Formula:
    Opportunity Score = 
        0.25 * price_growth
        + 0.25 * demand_score
        + 0.20 * mobility_score
        + 0.20 * property_quality_score
        - 0.10 * climate_risk_score
    """
    print("\n" + "="*70)
    print("STEP 7: CALCULATING OPPORTUNITY SCORE")
    print("="*70)
    
    df_scores = df.copy()
    
    # Normalize all components to 0-100 scale
    def normalize_col(col, reverse=False):
        if col.max() - col.min() == 0:
            return pd.Series([50] * len(col))
        norm = (col - col.min()) / (col.max() - col.min()) * 100
        if reverse:
            norm = 100 - norm
        return norm
    
    # Build opportunity score
    df_scores['price_growth_norm'] = normalize_col(df_scores['avg_price_growth'])
    df_scores['demand_norm'] = normalize_col(df_scores['avg_demand_score'])
    df_scores['mobility_norm'] = normalize_col(df_scores['avg_mobility_score'])
    df_scores['quality_norm'] = normalize_col(df_scores['avg_property_quality'])
    df_scores['climate_norm'] = normalize_col(df_scores['avg_climate_risk_score'], reverse=True)
    
    # Calculate weighted opportunity score
    df_scores['opportunity_score'] = (
        0.25 * df_scores['price_growth_norm'] +
        0.25 * df_scores['demand_norm'] +
        0.20 * df_scores['mobility_norm'] +
        0.20 * df_scores['quality_norm'] -
        0.10 * df_scores['climate_norm']
    ).clip(0, 100)
    
    # Rank boroughs (MUST be before printing)
    df_scores['opportunity_rank'] = df_scores['opportunity_score'].rank(ascending=False)
    
    print(f"✓ Opportunity scores calculated")
    print(f"\nOpportunity Score Distribution:")
    print(f"  Mean: {df_scores['opportunity_score'].mean():.2f}")
    print(f"  Median: {df_scores['opportunity_score'].median():.2f}")
    print(f"  Std Dev: {df_scores['opportunity_score'].std():.2f}")
    print(f"  Range: {df_scores['opportunity_score'].min():.2f} - {df_scores['opportunity_score'].max():.2f}")
    
    # Print top 10
    print(f"\nTop 10 Investment Opportunities:")
    top_10 = df_scores.nlargest(10, 'opportunity_score')[['borough_name', 'opportunity_score', 'opportunity_rank', 'property_count', 'avg_price']]
    for idx, row in top_10.iterrows():
        print(f"  {int(row['opportunity_rank']):<2}. {row['borough_name']:<30} Score: {row['opportunity_score']:>6.2f} | Props: {row['property_count']:>4.0f} | Avg Price: £{row['avg_price']:>10,.0f}")
    
    return df_scores


# ============================================================================
# STEP 8: PREPARE OUTPUT DATASET
# ============================================================================

def prepare_output_dataset(df):
    """Prepare final dataset for export."""
    print("\n" + "="*70)
    print("STEP 8: PREPARING OUTPUT DATASET")
    print("="*70)
    
    # Select key columns for output
    output_cols = [
        'opportunity_rank',
        'borough_name',
        'property_count',
        'avg_price',
        'median_price',
        'avg_price_per_sqft',
        'avg_price_growth',
        'avg_demand_score',
        'avg_mobility_score',
        'avg_climate_risk_score',
        'avg_property_quality',
        'avg_daysOnZillow',
        'total_tourViewCount',
        'total_num_of_applications',
        'avg_bedrooms',
        'avg_bathrooms',
        'avg_livingArea',
        'opportunity_score'
    ]
    
    df_output = df[output_cols].copy()
    
    # Sort by opportunity score
    df_output = df_output.sort_values('opportunity_score', ascending=False).reset_index(drop=True)
    
    print(f"✓ Output dataset prepared")
    print(f"  Shape: {df_output.shape}")
    print(f"  Columns: {len(df_output.columns)}")
    
    return df_output


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Execute the complete Urban Pulse data pipeline."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "URBAN PULSE LONDON - DATA PIPELINE" + " "*19 + "║")
    print("║" + " "*20 + "Investment Intelligence Platform" + " "*16 + "║")
    print("╚" + "="*68 + "╝")
    
    start_time = datetime.now()
    
    try:
        # Step 1: Load
        df = load_dataset(INPUT_FILE)
        
        # Step 2: Filter columns
        df = filter_columns(df, ESSENTIAL_COLS)
        
        # Step 3: Clean data
        df = clean_data(df)
        
        # Save property-level clean data
        print(f"\n💾 Saving property-level data to {PROPERTY_LEVEL_OUTPUT}...")
        df.to_csv(PROPERTY_LEVEL_OUTPUT, index=False)
        print(f"✓ Saved: {PROPERTY_LEVEL_OUTPUT}")
        
        # Step 4: Feature engineering
        df = engineer_features(df)
        
        # Step 5: Geospatial aggregation
        df = map_to_borough(df)
        
        # Step 6: Borough-level aggregation
        borough_metrics = aggregate_by_borough(df)
        
        # Step 7: Calculate opportunity score
        df_output = calculate_opportunity_score(borough_metrics)
        
        # Step 8: Prepare output
        df_output = prepare_output_dataset(df_output)
        
        # ====== EXPORT ======
        print("\n" + "="*70)
        print("EXPORTING RESULTS")
        print("="*70)
        
        df_output.to_csv(OUTPUT_FILE, index=False)
        print(f"✓ Final dataset exported: {OUTPUT_FILE}")
        
        # Print summary
        print("\n" + "="*70)
        print("PIPELINE COMPLETE - SUMMARY")
        print("="*70)
        print(f"\n📊 Results:")
        print(f"  - Total properties processed: {len(df):,}")
        print(f"  - Unique boroughs analyzed: {len(df_output)}")
        print(f"  - Top opportunity borough: {df_output.iloc[0]['borough_name']} (Score: {df_output.iloc[0]['opportunity_score']:.2f})")
        print(f"  - Average opportunity score: {df_output['opportunity_score'].mean():.2f}")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n⏱ Execution time: {elapsed:.2f} seconds")
        
        print(f"\n📁 Output files generated:")
        print(f"  1. {OUTPUT_FILE} - Borough-level investment metrics")
        print(f"  2. {PROPERTY_LEVEL_OUTPUT} - Cleaned property-level data")
        
        print("\n✅ Urban Pulse pipeline executed successfully!\n")
        
        return df_output
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    results = main()
    
    # Display top results
    print("\n" + "="*70)
    print("TOP 15 INVESTMENT OPPORTUNITIES")
    print("="*70)
    print(results[['opportunity_rank', 'borough_name', 'opportunity_score', 
                   'property_count', 'avg_price', 'avg_price_growth']].to_string())
