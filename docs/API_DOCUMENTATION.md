# Urban Pulse API - Complete Endpoint Documentation

## Table of Contents

1. [Authentication](#authentication)
2. [Error Handling](#error-handling)
3. [Health & Status Endpoints](#health--status)
4. [Borough Endpoints](#boroughs)
5. [Property Endpoints](#properties)
6. [Search & Filter Endpoints](#search--filter)
7. [Analytics Endpoints](#analytics)
8. [Admin Endpoints](#admin)
9. [Response Models](#response-models)
10. [Code Examples](#code-examples)

---

## Authentication

Currently, the API does **not** require authentication. For production deployment, implement authentication:

```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials
security = HTTPBearer()

@app.get("/api/endpoint")
async def endpoint(credentials: HTTPAuthCredentials = Depends(security)):
    # Verify token
    pass
```

---

## Error Handling

All errors follow a standard format:

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "detail": {
    "type": "ErrorType",
    "timestamp": "2024-03-07T10:30:00.000000"
  }
}
```

### Common Status Codes

- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Health & Status

### GET /health

Check API and database health.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-03-07T10:30:00.000000",
  "database": "connected"
}
```

### GET /api/status

Get API version and status.

**Response:**

```json
{
  "title": "Urban Pulse Investment Intelligence API",
  "version": "1.0.0",
  "status": "operational",
  "timestamp": "2024-03-07T10:30:00.000000"
}
```

---

## Boroughs

### GET /api/boroughs

Get all boroughs with metrics.

**Query Parameters:**

- `sort_by` (string, optional): Sort results by field
  - `opportunity_score` (default) - Sort by opportunity score
  - `property_count` - Sort by property count
  - `avg_price` - Sort by average price

**Example:**

```bash
curl http://localhost:8000/api/boroughs?sort_by=opportunity_score
```

**Response:**

```json
[
  {
    "_id": "507f1f77bcf86cd799439011",
    "borough_name": "Westminster",
    "property_count": 1250,
    "avg_price": 850000.0,
    "avg_price_growth": 5.2,
    "avg_demand_score": 78.5,
    "avg_mobility_score": 92.3,
    "avg_climate_risk_score": 18.5,
    "opportunity_score": 72.3,
    "rank": 1
  }
]
```

### GET /api/boroughs/{borough_name}

Get detailed metrics for a specific borough.

**Path Parameters:**

- `borough_name` (string, required): Name of the borough (e.g., "Westminster")

**Example:**

```bash
curl http://localhost:8000/api/boroughs/Westminster
```

**Response:**

```json
{
  "_id": "507f1f77bcf86cd799439011",
  "borough_name": "Westminster",
  "property_count": 1250,
  "avg_price": 850000.0,
  "avg_price_growth": 5.2,
  "median_price": 825000.0,
  "price_range_min": 250000.0,
  "price_range_max": 2500000.0,
  "avg_demand_score": 78.5,
  "avg_mobility_score": 92.3,
  "avg_climate_risk_score": 18.5,
  "avg_quality_score": 75.2,
  "avg_days_on_market": 15.3,
  "avg_bedrooms": 2.8,
  "avg_bathrooms": 1.9,
  "opportunity_score": 72.3,
  "rank": 1
}
```

### GET /api/top-growth-zones

Get top boroughs by opportunity score.

**Query Parameters:**

- `limit` (integer, optional): Number of top zones to return (default: 5, max: 27)

**Example:**

```bash
curl http://localhost:8000/api/top-growth-zones?limit=10
```

**Response:**

```json
[
  {
    "borough_name": "Westminster",
    "opportunity_score": 72.3,
    "rank": 1,
    ...
  },
  {
    "borough_name": "City of London",
    "opportunity_score": 70.1,
    "rank": 2,
    ...
  }
]
```

### GET /api/boroughs-by-price-range

Get boroughs with average prices within a range.

**Query Parameters:**

- `min_price` (number, optional): Minimum average price (default: 0)
- `max_price` (number, optional): Maximum average price (default: 1,000,000)

**Example:**

```bash
curl "http://localhost:8000/api/boroughs-by-price-range?min_price=500000&max_price=1000000"
```

**Response:**

```json
[
  {
    "borough_name": "Westminster",
    "avg_price": 850000.0,
    "opportunity_score": 72.3,
    ...
  }
]
```

---

## Properties

### GET /api/properties/borough/{borough_name}

Get properties in a specific borough with pagination.

**Path Parameters:**

- `borough_name` (string, required): Name of the borough

**Query Parameters:**

- `skip` (integer, optional): Number of properties to skip (default: 0)
- `limit` (integer, optional): Properties per page (default: 20, max: 100)

**Example:**

```bash
curl "http://localhost:8000/api/properties/borough/Westminster?skip=0&limit=20"
```

**Response:**

```json
{
  "total": 1250,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "zpid": "12345678",
      "latitude": 51.5074,
      "longitude": -0.1278,
      "borough": "Westminster",
      "price": 750000.0,
      "bedrooms": 3.0,
      "bathrooms": 2.0,
      "demand_score": 75.0,
      "mobility_score": 85.0,
      "climate_risk_score": 20.0
    }
  ]
}
```

### GET /api/properties/top

Get top-rated properties.

**Query Parameters:**

- `limit` (integer, optional): Number of properties to return (default: 20, max: 100)
- `skip` (integer, optional): Pagination offset (default: 0)

**Example:**

```bash
curl "http://localhost:8000/api/properties/top?limit=50"
```

**Response:**

```json
{
  "total": 50000,
  "page": 1,
  "page_size": 20,
  "items": [...]
}
```

### GET /api/properties/{zpid}

Get detailed information for a specific property.

**Path Parameters:**

- `zpid` (string, required): Zillow Property ID

**Example:**

```bash
curl http://localhost:8000/api/properties/12345678
```

**Response:**

```json
{
  "_id": "507f1f77bcf86cd799439011",
  "zpid": "12345678",
  "latitude": 51.5074,
  "longitude": -0.1278,
  "borough": "Westminster",
  "price": 750000.0,
  "zestimate": 775000.0,
  "rentZestimate": 3500.0,
  "lastSoldPrice": 720000.0,
  "bedrooms": 3.0,
  "bathrooms": 2.0,
  "sqft": 1500.0,
  "lotSize": 2500.0,
  "yearBuilt": 1950,
  "daysOnZillow": 10,
  "tourViewCount": 45,
  "demand_score": 75.0,
  "mobility_score": 85.0,
  "climate_risk_score": 20.0,
  "property_quality_score": 72.0,
  "opportunity_score": 70.5,
  "price_per_sqft": 500.0,
  "price_growth": 4.17
}
```

---

## Search & Filter

### GET /api/properties/search

Advanced search with multiple filters.

**Query Parameters:**

- `borough` (string, optional): Borough name
- `min_price` (number, optional): Minimum property price
- `max_price` (number, optional): Maximum property price
- `min_demand_score` (number, optional): Minimum demand score (0-100)
- `skip` (integer, optional): Pagination offset (default: 0)
- `limit` (integer, optional): Results per page (default: 20, max: 100)

**Example:**

```bash
curl "http://localhost:8000/api/properties/search?borough=Westminster&min_price=500000&max_price=1000000&min_demand_score=70"
```

**Response:**

```json
{
  "total": 245,
  "page": 1,
  "page_size": 20,
  "items": [...]
}
```

---

## Analytics

### GET /api/analytics

Get system-wide analytics and market summary.

**Example:**

```bash
curl http://localhost:8000/api/analytics
```

**Response:**

```json
{
  "total_properties": 50000,
  "total_boroughs": 27,
  "avg_borough_opportunity_score": 65.5,
  "highest_opportunity_borough": "Westminster",
  "lowest_opportunity_borough": "Barking and Dagenham",
  "market_statistics": {
    "avg_price": 650000.0,
    "avg_demand_score": 62.3,
    "avg_mobility_score": 75.1,
    "avg_climate_risk": 28.4,
    "total_properties": 50000
  },
  "last_updated": "2024-03-07T10:30:00.000000"
}
```

### GET /api/market-summary

Get high-level market overview.

**Example:**

```bash
curl http://localhost:8000/api/market-summary
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "avg_price": 650000.0,
    "avg_demand_score": 62.3,
    "avg_mobility_score": 75.1,
    "avg_climate_risk": 28.4,
    "total_properties": 50000
  },
  "timestamp": "2024-03-07T10:30:00.000000"
}
```

---

## Admin

### POST /api/admin/load-data

Load and process Zillow property data.

**Query Parameters:**

- `clear_existing` (boolean, optional): Clear existing data before loading (default: false)

**Example:**

```bash
# Load new data (append/update)
curl -X POST http://localhost:8000/api/admin/load-data

# Clear all data first
curl -X POST http://localhost:8000/api/admin/load-data?clear_existing=true
```

**Response:**

```json
{
  "status": "success",
  "message": "Data loaded successfully",
  "properties_loaded": 50000,
  "boroughs_loaded": 27,
  "timestamp": "2024-03-07T10:30:00.000000"
}
```

### POST /api/admin/refresh-borough-metrics

Recalculate all borough-level metrics.

**Example:**

```bash
curl -X POST http://localhost:8000/api/admin/refresh-borough-metrics
```

**Response:**

```json
{
  "status": "success",
  "message": "Borough metrics refreshed",
  "properties_processed": 50000,
  "timestamp": "2024-03-07T10:30:00.000000"
}
```

### DELETE /api/admin/clear-data

Delete all data from database.

**⚠️ Warning:** This operation cannot be undone!

**Example:**

```bash
curl -X DELETE http://localhost:8000/api/admin/clear-data
```

**Response:**

```json
{
  "status": "success",
  "message": "All data cleared from database",
  "timestamp": "2024-03-07T10:30:00.000000"
}
```

---

## Response Models

### BoroughMetrics

```json
{
  "borough_name": "string",
  "property_count": 0,
  "avg_price": 0.0,
  "avg_price_growth": 0.0,
  "avg_demand_score": 0.0,
  "avg_mobility_score": 0.0,
  "avg_climate_risk_score": 0.0,
  "avg_quality_score": 0.0,
  "median_price": 0.0,
  "price_range_min": 0.0,
  "price_range_max": 0.0,
  "avg_days_on_market": 0.0,
  "avg_bedrooms": 0.0,
  "avg_bathrooms": 0.0,
  "opportunity_score": 0.0,
  "rank": 1
}
```

### Property

```json
{
  "zpid": "string",
  "latitude": 0.0,
  "longitude": 0.0,
  "borough": "string",
  "price": 0.0,
  "bedrooms": 0.0,
  "bathrooms": 0.0,
  "demand_score": 0.0,
  "mobility_score": 0.0,
  "climate_risk_score": 0.0,
  "opportunity_score": 0.0
}
```

### PaginatedResponse

```json
{
  "total": 0,
  "page": 1,
  "page_size": 20,
  "items": []
}
```

---

## Code Examples

### Python (requests)

```python
import requests

api_url = "http://localhost:8000"

# Get all boroughs
response = requests.get(f"{api_url}/api/boroughs")
boroughs = response.json()

# Get top growth zones
top = requests.get(f"{api_url}/api/top-growth-zones?limit=5").json()

# Search properties
search_params = {
    "borough": "Westminster",
    "min_price": 500000,
    "max_price": 1000000,
    "min_demand_score": 70
}
results = requests.get(f"{api_url}/api/properties/search", params=search_params).json()
```

### JavaScript/TypeScript

```javascript
const API_URL = "http://localhost:8000";

// Get all boroughs
const boroughs = await fetch(`${API_URL}/api/boroughs`).then((r) => r.json());

// Get top growth zones
const topZones = await fetch(`${API_URL}/api/top-growth-zones?limit=5`).then(
  (r) => r.json(),
);

// Search properties
const results = await fetch(
  `${API_URL}/api/properties/search?borough=Westminster&min_price=500000`,
).then((r) => r.json());
```

### cURL

```bash
# Get all boroughs
curl http://localhost:8000/api/boroughs

# Get specific borough
curl http://localhost:8000/api/boroughs/Westminster

# Get top growth zones
curl http://localhost:8000/api/top-growth-zones?limit=5

# Search with filters
curl "http://localhost:8000/api/properties/search?borough=Westminster&min_price=500000&max_price=1000000"

# Load data (admin)
curl -X POST http://localhost:8000/api/admin/load-data

# Get analytics
curl http://localhost:8000/api/analytics
```

### PowerShell

```powershell
$api = "http://localhost:8000"

# Get boroughs
$boroughs = Invoke-WebRequest "$api/api/boroughs" | ConvertFrom-Json

# Get top growth zones
$topZones = Invoke-WebRequest "$api/api/top-growth-zones?limit=5" | ConvertFrom-Json

# Load data
Invoke-WebRequest -Method Post "$api/api/admin/load-data"
```

---

## Rate Limiting

Currently, the API does **not** implement rate limiting. For production, add:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/endpoint")
@limiter.limit("100/minute")
async def limited_endpoint(request: Request):
    pass
```

---

## Pagination

All list endpoints support pagination:

```bash
# Get page 1 with 20 items (default)
curl "http://localhost:8000/api/properties/borough/Westminster"

# Get page 2 (skip first 20, take next 20)
curl "http://localhost:8000/api/properties/borough/Westminster?skip=20&limit=20"

# Get page 3 with 50 items per page
curl "http://localhost:8000/api/properties/borough/Westminster?skip=100&limit=50"
```

---

## Sorting

Properties are sorted by `demand_score` in descending order by default.

For boroughs, use the `sort_by` parameter:

```bash
curl "http://localhost:8000/api/boroughs?sort_by=opportunity_score"
```

---

## CORS

The API allows cross-origin requests from all domains by default. Configure CORS in production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

**For interactive API testing, visit: http://localhost:8000/docs**
