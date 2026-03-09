# Urban Pulse Backend - System Architecture & Overview

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                      │
│  (Web Frontend, Mobile App, Dashboard, Third-party Integrations) │
└────────────────────────────┬──────────────────────────────────────┘
                             │
                   HTTP/REST (FastAPI)
                             │
┌────────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Backend (app.py)                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Health Check │ Borough Endpoints │ Property Endpoints      │ │
│  │  Search       │ Analytics          │ Admin Operations       │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────┬──────────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    │                │                │
┌───▼────┐    ┌─────▼──────┐    ┌────▼─────┐
│ Models │    │  Database  │    │ Data     │
│ (Pydantic) │    │ (Motor)    │    │ Processor│
└────────┘    └────────────┘    └──────────┘
                     │
                     │
        MongoDB (Async)
        ├─ collections.properties
        └─ collections.borough_metrics
```

## 📁 Project Structure

```
urban_pulse_backend/
├── app.py                      # FastAPI application (500+ lines)
│   ├── Health & Status endpoints
│   ├── Borough management endpoints
│   ├── Property search & retrieval
│   ├── Analytics endpoints
│   └── Admin operations
│
├── models.py                   # Pydantic data models (400+ lines)
│   ├── Property model
│   ├── BoroughMetrics model
│   ├── PropertyStatus enum
│   └── Response models
│
├── database.py                 # MongoDB operations (400+ lines)
│   ├── MongoDatabase class
│   ├── Connection management
│   ├── CRUD operations
│   ├── Index creation
│   └── Aggregation queries
│
├── data_processor.py           # Data pipeline (500+ lines)
│   ├── DataProcessor class
│   ├── Data loading
│   ├── Data cleaning
│   ├── Feature engineering
│   ├── Geospatial mapping
│   └── Borough aggregation
│
├── config.py                   # Configuration management
│   └── Settings class (Pydantic)
│
├── setup.py                    # Database initialization
├── cli.py                      # CLI tool
├── api_examples.py             # API client & examples
├── QUICKSTART.py               # Interactive quick start guide
│
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
│
├── Dockerfile                  # Docker image
├── docker-compose.yml          # Local development stack
│
├── .env                        # (Local) Environment variables
├── .env.example                # Environment template
│
├── README_BACKEND.md           # Full documentation
├── API_DOCUMENTATION.md        # API endpoint reference
│
├── zillow_properties_listing.csv        # Input data
├── urban_pulse_properties_clean.csv     # Processed properties
└── urban_pulse_borough_metrics.csv      # Borough metrics
```

## 🔄 Data Processing Pipeline

### Stage 1: Data Loading

- **Input**: `zillow_properties_listing.csv` (50,000+ properties)
- **Output**: Pandas DataFrame
- **Actions**:
  - Read CSV file
  - Log shape and memory usage
  - Extract essential columns (25+)

### Stage 2: Data Cleaning

- **Input**: Raw DataFrame
- **Output**: Cleaned DataFrame
- **Actions**:
  - Remove rows with missing location/price
  - Convert date columns to datetime
  - Convert numeric columns
  - Fill missing values with median/mode
  - Validate data ranges

### Stage 3: Feature Engineering

- **Input**: Cleaned DataFrame
- **Output**: Features-enriched DataFrame
- **Actions**:
  - `price_per_sqft`: price / sqft
  - `price_growth`: (current_price - last_sold) / last_sold \* 100
  - `demand_score` (0-100):
    - 25% Days On Zillow (inverse)
    - 35% Tour View Count
    - 20% Number of Contacts
    - 20% Number of Applications
  - `mobility_score`: Extracted from getting_around_scores
  - `climate_risk_score`: Extracted from climate_risks
  - `property_quality_score`: 20% beds + 20% baths + 30% age + 30% area
  - `opportunity_score`: Weighted combination

### Stage 4: Geospatial Mapping

- **Input**: Features DataFrame with lat/lon
- **Output**: GeoDataFrame with borough assignment
- **Methods**:
  - Convert to GeoDataFrame (EPSG:4326)
  - Spatial join with borough boundaries (GeoJSON)
  - Fallback: Postcode-based assignment
  - Default: Random borough assignment

### Stage 5: Borough Aggregation

- **Input**: Property-level data
- **Output**: Borough-level metrics
- **Metrics**:
  - `property_count`: Number of properties
  - `avg_price`, `median_price`, `price_range`
  - `avg_price_growth`, `avg_demand_score`, `avg_mobility_score`
  - `avg_climate_risk_score`, `avg_quality_score`
  - `avg_days_on_market`, `avg_bedrooms`, `avg_bathrooms`
  - `opportunity_score`: Weighted metric
  - `rank`: 1-27 ranking

### Stage 6: MongoDB Storage

- **Input**: Properties and borough metrics lists
- **Output**: Indexed collections
- **Actions**:
  - Upsert properties (by zpid)
  - Upsert borough metrics (by borough_name)
  - Create indexes for fast queries

## 🎯 Opportunity Score Calculation

### Formula

```
Opportunity Score =
  0.25 * Normalized(Price Growth) +
  0.25 * Demand Score +
  0.20 * Mobility Score -
  0.10 * (100 - Climate Risk Score)
```

### Interpretation Scale

- **90-100**: Exceptional growth opportunity
- **75-89**: Strong growth potential
- **60-74**: Moderate opportunity
- **45-59**: Mixed market signals
- **Below 45**: Higher risk, lower potential

### Example Calculation

Borough: Westminster

- Price Growth: 5.2% → Normalized to 65/100
- Demand Score: 78.5/100
- Mobility Score: 92.3/100
- Climate Risk: 18.5/100

```
Score = 0.25 * 65 + 0.25 * 78.5 + 0.20 * 92.3 - 0.10 * (100 - 18.5)
      = 16.25 + 19.625 + 18.46 - 8.15
      = 46.185
```

**Final Score: 46.2/100** (rounded)

## 🗄️ Database Schema

### Collections

#### `properties` (50,000+ documents)

```javascript
{
  _id: ObjectId,
  zpid: String (unique),
  latitude: Double,
  longitude: Double,
  borough: String,
  price: Double,
  zestimate: Double,
  rentZestimate: Double,
  lastSoldPrice: Double,

  bedrooms: Double,
  bathrooms: Double,
  livingArea: Double,
  sqft: Double,
  lotSize: Double,
  yearBuilt: Int32,
  homeType: String,

  daysOnZillow: Int32,
  tourViewCount: Int32,
  num_of_contacts: Int32,
  num_of_applications: Int32,
  sold_to_list_ratio: Double,

  price_per_sqft: Double,
  price_growth: Double,
  demand_score: Double (0-100),
  mobility_score: Double (0-100),
  climate_risk_score: Double (0-100),
  property_quality_score: Double (0-100),
  opportunity_score: Double (0-100),

  created_at: DateTime,
  updated_at: DateTime
}
```

**Indexes:**

- `zpid` (unique)
- `borough` (ascending)
- `opportunity_score` (descending)
- `latitude, longitude` (compound)
- `demand_score` (descending)

#### `borough_metrics` (27 documents)

```javascript
{
  _id: ObjectId,
  borough_name: String (unique),
  property_count: Int32,

  avg_price: Double,
  median_price: Double,
  price_range_min: Double,
  price_range_max: Double,

  avg_price_growth: Double,
  avg_demand_score: Double,
  avg_mobility_score: Double,
  avg_climate_risk_score: Double,
  avg_quality_score: Double,

  avg_days_on_market: Double,
  avg_bedrooms: Double,
  avg_bathrooms: Double,

  opportunity_score: Double (0-100),
  rank: Int32 (1-27),

  created_at: DateTime,
  updated_at: DateTime
}
```

**Indexes:**

- `borough_name` (unique)
- `opportunity_score` (descending)
- `rank` (ascending)

## 🔌 API Layer Architecture

### Request Flow

1. **Client Request** → FastAPI receives HTTP request
2. **Pydantic Validation** → Request parameters validated
3. **Database Query** → Async MongoDB operation via Motor
4. **Response Serialization** → Convert to JSON response model
5. **Client Response** → Return to client

### Endpoint Categories

#### Health (2 endpoints)

- System health status
- API version/status

#### Boroughs (4 endpoints)

- All boroughs with pagination/sorting
- Single borough details
- Top opportunities
- Price-range filters

#### Properties (4 endpoints)

- Properties by borough
- Top-rated properties
- Individual property details
- Advanced search with filters

#### Analytics (2 endpoints)

- System-wide summary
- Market overview

#### Admin (3 endpoints)

- Data loading
- Metric recalculation
- Data clearing

## 🚀 Deployment Architecture

### Docker Compose (Development)

```yaml
Services:
├── mongodb (mongo:latest)
│   └── Port 27017
└── api (FastAPI)
    └── Port 8000

Networks:
└── urban-pulse-network
```

### Production Deployment Options

#### Option 1: Docker Swarm

```
Manager Nodes → API Service (3 replicas)
           ↓
       MongoDB (Replication Set)
```

#### Option 2: Kubernetes

```
Ingress → Service → Deployment (Replicas)
             ↓
       StatefulSet (MongoDB)
```

#### Option 3: Serverless (AWS Lambda)

```
API Gateway → Lambda Functions
         ↓
    DocumentDB (MongoDB-compatible)
```

## 📊 Performance Characteristics

### Query Performance

| Query                                 | Est. Time | Records  |
| ------------------------------------- | --------- | -------- |
| Get all boroughs                      | <50ms     | 27       |
| Get borough details                   | <50ms     | 1        |
| Get properties by borough (paginated) | <100ms    | ~20      |
| Top growth zones                      | <50ms     | 5        |
| Search with filters                   | 50-200ms  | Variable |
| Analytics summary                     | 100-300ms | 1        |

### Memory Usage

- API Process: ~150-200 MB
- MongoDB: ~500 MB - 1 GB (depends on data)
- Data Processor (during load): ~2-5 GB (depends on dataset size)

### Scalability

- **Vertical**: Increase CPU/RAM for API and MongoDB
- **Horizontal**: API: Load balancer + multiple instances
  MongoDB: Replica set + sharding

## 🔐 Security Considerations

### Current State

- ✅ Data validation (Pydantic models)
- ✅ CORS enabled (all origins)
- ✅ Error handling
- ✅ Async I/O (no blocking)

### For Production Add

- ✅ Authentication (JWT/OAuth)
- ✅ Rate limiting
- ✅ Input sanitization
- ✅ HTTPS/TLS
- ✅ Database authentication
- ✅ Admin endpoint protection
- ✅ CORS restrictions
- ✅ Request logging/audit trails
- ✅ SQL injection prevention (using ORM)
- ✅ API key versioning

## 🔄 Update & Maintenance Workflow

### Regular Updates

1. **Daily**: System is operational, serving requests
2. **Weekly**: Refresh borough metrics (recalculate from properties)
3. **Monthly**: Load new data (append/update properties)
4. **Quarterly**: Full data reload + validation

### Data Refresh Process

```
1. Download latest Zillow data
2. Run data processor pipeline
3. Upsert into MongoDB
4. Validate metrics
5. Update analytics cache
6. Notify clients
```

## 🎓 Technology Stack

| Component       | Technology    | Version |
| --------------- | ------------- | ------- |
| Framework       | FastAPI       | 0.104+  |
| Server          | Uvicorn       | 0.24+   |
| Database        | MongoDB       | 4.4+    |
| Async Driver    | Motor         | 3.3+    |
| Data Processing | Pandas        | 1.5+    |
| Geospatial      | GeoPandas     | 0.12+   |
| Validation      | Pydantic      | 2.0+    |
| HTTP            | HTTPX         | 0.24+   |
| Configuration   | python-dotenv | 1.0+    |
| CLI             | Click         | 8.1+    |

## 📈 Future Enhancements

### Phase 2

- [ ] User authentication & API keys
- [ ] Advanced filtering (custom queries)
- [ ] Caching (Redis for hot data)
- [ ] Real-time updates (WebSocket)
- [ ] Export functionality (CSV, JSON)

### Phase 3

- [ ] Machine learning models (price prediction)
- [ ] Investment recommendations
- [ ] Portfolio tracking
- [ ] Historical trend analysis
- [ ] Custom alerts/notifications

### Phase 4

- [ ] Mobile app
- [ ] Advanced visualization dashboard
- [ ] Comparative analysis tools
- [ ] Report generation
- [ ] Integration with other data sources

---

**For detailed endpoints, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md)**

**For quick start, see [README_BACKEND.md](README_BACKEND.md)**
