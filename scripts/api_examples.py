"""
API Testing Examples for Urban Pulse Backend
Demonstrates how to use all API endpoints.
"""

import requests
import json
from typing import Dict, Any


class UrbanPulseAPIClient:
    """Client for interacting with Urban Pulse API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # HEALTH & STATUS
    # ========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        return self._request("GET", "/health")
    
    def api_status(self) -> Dict[str, Any]:
        """Get API status"""
        return self._request("GET", "/api/status")
    
    # ========================================================================
    # BOROUGHS
    # ========================================================================
    
    def get_all_boroughs(self, sort_by: str = "opportunity_score") -> list:
        """Get all boroughs"""
        return self._request("GET", f"/api/boroughs?sort_by={sort_by}")
    
    def get_borough(self, borough_name: str) -> Dict[str, Any]:
        """Get specific borough details"""
        return self._request("GET", f"/api/boroughs/{borough_name}")
    
    def get_top_growth_zones(self, limit: int = 5) -> list:
        """Get top growth opportunities"""
        return self._request("GET", f"/api/top-growth-zones?limit={limit}")
    
    def get_boroughs_by_price(self, min_price: float, max_price: float) -> list:
        """Filter boroughs by price range"""
        return self._request(
            "GET",
            f"/api/boroughs-by-price-range?min_price={min_price}&max_price={max_price}"
        )
    
    # ========================================================================
    # PROPERTIES
    # ========================================================================
    
    def get_properties_by_borough(self, borough_name: str, skip: int = 0, limit: int = 20) -> Dict:
        """Get properties in borough"""
        return self._request(
            "GET",
            f"/api/properties/borough/{borough_name}?skip={skip}&limit={limit}"
        )
    
    def get_top_properties(self, limit: int = 20) -> Dict:
        """Get top-rated properties"""
        return self._request("GET", f"/api/properties/top?limit={limit}")
    
    def get_property(self, zpid: str) -> Dict[str, Any]:
        """Get specific property details"""
        return self._request("GET", f"/api/properties/{zpid}")
    
    def search_properties(
        self,
        borough: str = None,
        min_price: float = None,
        max_price: float = None,
        min_demand_score: float = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict:
        """Search properties with filters"""
        params = {}
        if borough:
            params["borough"] = borough
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if min_demand_score is not None:
            params["min_demand_score"] = min_demand_score
        params["skip"] = skip
        params["limit"] = limit
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return self._request("GET", f"/api/properties/search?{query_string}")
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get system analytics"""
        return self._request("GET", "/api/analytics")
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get market summary"""
        return self._request("GET", "/api/market-summary")
    
    # ========================================================================
    # ADMIN
    # ========================================================================
    
    def load_data(self, clear_existing: bool = False) -> Dict[str, Any]:
        """Load Zillow data"""
        return self._request(
            "POST",
            f"/api/admin/load-data?clear_existing={'true' if clear_existing else 'false'}"
        )
    
    def refresh_metrics(self) -> Dict[str, Any]:
        """Refresh borough metrics"""
        return self._request("POST", "/api/admin/refresh-borough-metrics")
    
    def clear_data(self) -> Dict[str, Any]:
        """Clear all data"""
        return self._request("DELETE", "/api/admin/clear-data")


def print_result(title: str, data: Any, indent: int = 0):
    """Pretty print result"""
    print("\n" + " " * indent + f"{'='*50}")
    print(" " * indent + f"► {title}")
    print(" " * indent + f"{'='*50}")
    print(json.dumps(data, indent=2, default=str))


def main():
    """Run example tests"""
    print("\n" + "="*70)
    print("Urban Pulse API - Example Usage")
    print("="*70)
    
    client = UrbanPulseAPIClient()
    
    # Test 1: Health Check
    print("\n1. Health Check")
    try:
        result = client.health_check()
        print(f"✓ API Status: {result['status']}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 2: Get All Boroughs
    print("\n2. Get All Boroughs")
    try:
        boroughs = client.get_all_boroughs()
        print(f"✓ Found {len(boroughs)} boroughs")
        if boroughs:
            top_borough = boroughs[0]
            print(f"  Top Borough: {top_borough['borough_name']}")
            print(f"  Opportunity Score: {top_borough['opportunity_score']:.1f}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: Get Top Growth Zones
    print("\n3. Top Growth Zones")
    try:
        top = client.get_top_growth_zones(limit=5)
        print(f"✓ Top {len(top)} growth opportunities:")
        for i, borough in enumerate(top, 1):
            print(f"  {i}. {borough['borough_name']}: {borough['opportunity_score']:.1f}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 4: Get Specific Borough
    print("\n4. Get Specific Borough Details")
    try:
        if boroughs:
            borough_name = boroughs[0]['borough_name']
            borough = client.get_borough(borough_name)
            print(f"✓ Borough: {borough['borough_name']}")
            print(f"  Properties: {borough['property_count']}")
            print(f"  Avg Price: ${borough['avg_price']:,.0f}")
            print(f"  Demand Score: {borough['avg_demand_score']:.1f}")
            print(f"  Opportunity Score: {borough['opportunity_score']:.1f}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 5: Get Properties by Borough
    print("\n5. Get Properties in a Borough")
    try:
        if boroughs:
            borough_name = boroughs[0]['borough_name']
            result = client.get_properties_by_borough(borough_name, skip=0, limit=5)
            print(f"✓ Found {result['total']} properties")
            print(f"  Showing {len(result['items'])} on page {result['page']}")
            if result['items']:
                prop = result['items'][0]
                print(f"  Sample property:")
                print(f"    ZPID: {prop['zpid']}")
                print(f"    Price: ${prop['price']:,.0f}")
                print(f"    Demand Score: {prop['demand_score']:.1f}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 6: Search Properties
    print("\n6. Search Properties")
    try:
        results = client.search_properties(
            min_price=500000,
            max_price=1000000,
            min_demand_score=70,
            limit=5
        )
        print(f"✓ Found {results['total']} properties matching criteria")
        print(f"  Showing {len(results['items'])} results")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 7: Get Analytics
    print("\n7. System Analytics")
    try:
        analytics = client.get_analytics()
        print(f"✓ System Analytics:")
        print(f"  Total Properties: {analytics['total_properties']}")
        print(f"  Total Boroughs: {analytics['total_boroughs']}")
        print(f"  Avg Borough Score: {analytics['avg_borough_opportunity_score']:.1f}")
        print(f"  Best Borough: {analytics['highest_opportunity_borough']}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 8: Market Summary
    print("\n8. Market Summary")
    try:
        summary = client.get_market_summary()
        if 'data' in summary:
            data = summary['data']
            print(f"✓ Market Summary:")
            print(f"  Avg Price: ${data.get('avg_price', 0):,.0f}")
            print(f"  Avg Demand Score: {data.get('avg_demand_score', 0):.1f}")
            print(f"  Avg Mobility Score: {data.get('avg_mobility_score', 0):.1f}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)
    print("✓ Testing complete!")
    print("="*70)
    print("\nNext steps:")
    print("  • Visit http://localhost:8000/docs for interactive API documentation")
    print("  • Check README_BACKEND.md for detailed endpoint documentation")
    print("  • Modify this script to test other endpoints")
    print("\n")


if __name__ == "__main__":
    main()
