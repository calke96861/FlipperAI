
import requests
import sys
import json
import time
from datetime import datetime

class FlipBotAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = {}

    def run_test(self, name, method, endpoint, expected_status=200, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"Response: {json.dumps(response_data, indent=2)[:500]}...")
                except:
                    print(f"Response: {response.text[:500]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text[:500]}...")

            self.test_results[name] = {
                "success": success,
                "status_code": response.status_code,
                "expected_status": expected_status
            }
            
            if success:
                try:
                    return True, response.json()
                except:
                    return True, response.text
            return False, None

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results[name] = {
                "success": False,
                "error": str(e)
            }
            return False, None

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        for name, result in self.test_results.items():
            if result.get("success"):
                print(f"✅ {name}")
            else:
                error_msg = f"Expected {result.get('expected_status')}, got {result.get('status_code')}"
                print(f"❌ {name} - {result.get('error', error_msg)}") 
        
        print("="*50)
        return self.tests_passed == self.tests_run

    def validate_vehicle_data(self, vehicle_data, search_query):
        """Validate that vehicle data contains expected fields and values"""
        if not vehicle_data:
            print("❌ No vehicle data found")
            return False
            
        # Check if the vehicle data contains the expected fields
        required_fields = ["make", "model", "year", "asking_price", "location", "url"]
        for field in required_fields:
            if field not in vehicle_data:
                print(f"❌ Missing required field: {field}")
                return False
                
        # Check if the vehicle data matches the search query
        query_terms = search_query.lower().split()
        vehicle_name = f"{vehicle_data.get('make', '')} {vehicle_data.get('model', '')} {vehicle_data.get('trim', '')}".lower()
        
        match_found = any(term in vehicle_name for term in query_terms)
        if not match_found:
            print(f"❌ Vehicle {vehicle_name} does not match search query: {search_query}")
            return False
            
        # Check if the vehicle has a valid price
        if not vehicle_data.get("asking_price") or vehicle_data.get("asking_price") <= 0:
            print("❌ Invalid vehicle price")
            return False
            
        print(f"✅ Valid vehicle data found: {vehicle_data.get('year')} {vehicle_data.get('make')} {vehicle_data.get('model')} - {vehicle_data.get('asking_price')}")
        return True
        
    def test_sorting_filtering(self):
        """Test the sorting and filtering functionality"""
        print("\n🔍 Testing Sorting and Filtering Features...")
        
        # Test 1: High Profit Sorting
        success, high_profit_data = self.run_test(
            "High Profit Sorting", 
            "GET", 
            "vehicles", 
            params={"skip": 0, "limit": 10, "sort_by": "est_profit", "sort_order": "desc"}
        )
        
        if success and high_profit_data:
            # Verify sorting is correct
            is_sorted = all(high_profit_data[i].get('est_profit', 0) >= high_profit_data[i+1].get('est_profit', 0) 
                           for i in range(len(high_profit_data)-1))
            
            if is_sorted and len(high_profit_data) > 0:
                print("✅ High Profit sorting works correctly")
                self.test_results["High Profit Sorting Validation"] = {"success": True}
            else:
                print("❌ High Profit sorting failed - Results not properly sorted")
                self.test_results["High Profit Sorting Validation"] = {"success": False}
        
        # Test 2: High ROI Sorting
        success, high_roi_data = self.run_test(
            "High ROI Sorting", 
            "GET", 
            "vehicles", 
            params={"skip": 0, "limit": 10, "sort_by": "roi_percent", "sort_order": "desc"}
        )
        
        if success and high_roi_data:
            # Verify sorting is correct
            is_sorted = all(high_roi_data[i].get('roi_percent', 0) >= high_roi_data[i+1].get('roi_percent', 0) 
                           for i in range(len(high_roi_data)-1))
            
            if is_sorted and len(high_roi_data) > 0:
                print("✅ High ROI sorting works correctly")
                self.test_results["High ROI Sorting Validation"] = {"success": True}
            else:
                print("❌ High ROI sorting failed - Results not properly sorted")
                self.test_results["High ROI Sorting Validation"] = {"success": False}
        
        # Test 3: Under $50K Filtering
        success, under_50k_data = self.run_test(
            "Under $50K Filtering", 
            "GET", 
            "vehicles", 
            params={"skip": 0, "limit": 10, "price_max": 50000}
        )
        
        if success and under_50k_data:
            # Verify all vehicles are under $50K
            all_under_50k = all(vehicle.get('asking_price', 0) <= 50000 for vehicle in under_50k_data)
            
            if all_under_50k:
                print("✅ Under $50K filtering works correctly")
                self.test_results["Under $50K Filtering Validation"] = {"success": True}
            else:
                print("❌ Under $50K filtering failed - Some vehicles are over $50K")
                self.test_results["Under $50K Filtering Validation"] = {"success": False}
        
        # Test 4: Low Mileage Sorting
        success, low_mileage_data = self.run_test(
            "Low Mileage Sorting", 
            "GET", 
            "vehicles", 
            params={"skip": 0, "limit": 10, "sort_by": "mileage", "sort_order": "asc"}
        )
        
        if success and low_mileage_data:
            # Verify sorting is correct
            is_sorted = all(low_mileage_data[i].get('mileage', 0) <= low_mileage_data[i+1].get('mileage', 0) 
                           for i in range(len(low_mileage_data)-1))
            
            if is_sorted and len(low_mileage_data) > 0:
                print("✅ Low Mileage sorting works correctly")
                self.test_results["Low Mileage Sorting Validation"] = {"success": True}
            else:
                print("❌ Low Mileage sorting failed - Results not properly sorted")
                self.test_results["Low Mileage Sorting Validation"] = {"success": False}
        
        # Test 5: Newest Year Sorting
        success, newest_year_data = self.run_test(
            "Newest Year Sorting", 
            "GET", 
            "vehicles", 
            params={"skip": 0, "limit": 10, "sort_by": "year", "sort_order": "desc"}
        )
        
        if success and newest_year_data:
            # Verify sorting is correct
            is_sorted = all(newest_year_data[i].get('year', 0) >= newest_year_data[i+1].get('year', 0) 
                           for i in range(len(newest_year_data)-1))
            
            if is_sorted and len(newest_year_data) > 0:
                print("✅ Newest Year sorting works correctly")
                self.test_results["Newest Year Sorting Validation"] = {"success": True}
            else:
                print("❌ Newest Year sorting failed - Results not properly sorted")
                self.test_results["Newest Year Sorting Validation"] = {"success": False}
        
        return True
    
    def test_scraping_strategies(self):
        """Test the different scraping strategies"""
        print("\n🔍 Testing Multiple Scraping Strategies...")
        
        # Test 1: Quick Scrape - BMW M3
        success, bmw_quick_scrape = self.run_test(
            "Quick Scrape - BMW M3", 
            "POST", 
            "scrape/quick", 
            params={"query": "BMW M3", "location": "90210", "max_results": 5}
        )
        
        if success:
            vehicles_found = bmw_quick_scrape.get("vehicles_found", 0)
            print(f"Quick Scrape found {vehicles_found} BMW M3 vehicles")
            
            # Check if sources are from the quick scrape list
            quick_sources = ["cars_com", "carmax", "carvana"]
            sources_used = list(bmw_quick_scrape.get("source_results", {}).keys())
            
            quick_sources_used = any(source in quick_sources for source in sources_used)
            if quick_sources_used:
                print("✅ Quick Scrape used appropriate sources")
                self.test_results["Quick Scrape Sources"] = {"success": True}
            else:
                print("❌ Quick Scrape did not use expected sources")
                self.test_results["Quick Scrape Sources"] = {"success": False}
        
        # Test 2: Comprehensive Scrape - BMW M3
        success, bmw_comprehensive_scrape = self.run_test(
            "Comprehensive Scrape - BMW M3", 
            "POST", 
            "scrape/comprehensive", 
            params={"query": "BMW M3", "location": "90210", "max_results": 5}
        )
        
        if success:
            vehicles_found = bmw_comprehensive_scrape.get("vehicles_found", 0)
            print(f"Comprehensive Scrape found {vehicles_found} BMW M3 vehicles")
            
            # Check if categories are used
            categories = bmw_comprehensive_scrape.get("categories_used", [])
            if categories and len(categories) >= 2:
                print(f"✅ Comprehensive Scrape used categories: {', '.join(categories)}")
                self.test_results["Comprehensive Scrape Categories"] = {"success": True}
            else:
                print("❌ Comprehensive Scrape did not use expected categories")
                self.test_results["Comprehensive Scrape Categories"] = {"success": False}
        
        # Test 3: Enthusiast Scrape - Porsche 911
        success, porsche_enthusiast_scrape = self.run_test(
            "Enthusiast Scrape - Porsche 911", 
            "POST", 
            "scrape/enthusiast", 
            params={"query": "Porsche 911", "max_results": 5}
        )
        
        if success:
            vehicles_found = porsche_enthusiast_scrape.get("vehicles_found", 0)
            print(f"Enthusiast Scrape found {vehicles_found} Porsche 911 vehicles")
            
            # Check if categories are used
            categories = porsche_enthusiast_scrape.get("categories_used", [])
            if "auction" in categories or "enthusiast" in categories:
                print(f"✅ Enthusiast Scrape used appropriate categories: {', '.join(categories)}")
                self.test_results["Enthusiast Scrape Categories"] = {"success": True}
            else:
                print("❌ Enthusiast Scrape did not use expected categories")
                self.test_results["Enthusiast Scrape Categories"] = {"success": False}
        
        # Test 4: Private Party Scrape - Ford Raptor
        success, raptor_private_scrape = self.run_test(
            "Private Party Scrape - Ford Raptor", 
            "POST", 
            "scrape/private-party", 
            params={"query": "Ford Raptor", "location": "90210", "max_results": 5}
        )
        
        if success:
            vehicles_found = raptor_private_scrape.get("vehicles_found", 0)
            print(f"Private Party Scrape found {vehicles_found} Ford Raptor vehicles")
            
            # Check if categories are used
            categories = raptor_private_scrape.get("categories_used", [])
            if "marketplace" in categories:
                print(f"✅ Private Party Scrape used marketplace category")
                self.test_results["Private Party Scrape Category"] = {"success": True}
            else:
                print("❌ Private Party Scrape did not use marketplace category")
                self.test_results["Private Party Scrape Category"] = {"success": False}
        
        return True
    
    def test_available_sources(self):
        """Test the available sources endpoint"""
        print("\n🔍 Testing Available Sources Endpoint...")
        
        success, sources_data = self.run_test("Get Available Sources", "GET", "scrape/sources")
        
        if success:
            # Check if we have all the expected categories
            expected_categories = [
                "retail_platforms", 
                "online_retailers", 
                "marketplace_platforms", 
                "enthusiast_auction", 
                "analytics_platforms", 
                "dealer_networks", 
                "valuation_services"
            ]
            
            categories_found = list(sources_data.keys())
            all_categories_present = all(category in categories_found for category in expected_categories)
            
            if all_categories_present:
                print(f"✅ All expected source categories are present")
                self.test_results["Source Categories"] = {"success": True}
            else:
                missing = [cat for cat in expected_categories if cat not in categories_found]
                print(f"❌ Missing source categories: {', '.join(missing)}")
                self.test_results["Source Categories"] = {"success": False}
            
            # Count total sources
            total_sources = sum(len(sources) for sources in sources_data.values())
            print(f"Total sources available: {total_sources}")
            
            if total_sources >= 22:
                print(f"✅ At least 22 sources are available")
                self.test_results["Source Count"] = {"success": True}
            else:
                print(f"❌ Only {total_sources} sources found, expected at least 22")
                self.test_results["Source Count"] = {"success": False}
            
            # Check for specific important sources
            important_sources = ["cars_com", "autotrader", "cargurus", "facebook", "bring_a_trailer"]
            found_sources = []
            
            for category in sources_data.values():
                for source in category:
                    if source.get("source") in important_sources:
                        found_sources.append(source.get("source"))
            
            if len(found_sources) >= 3:
                print(f"✅ Found important sources: {', '.join(found_sources)}")
                self.test_results["Important Sources"] = {"success": True}
            else:
                print(f"❌ Missing important sources. Only found: {', '.join(found_sources)}")
                self.test_results["Important Sources"] = {"success": False}
        
        return True

def main():
    # Get the backend URL from the frontend .env file
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                backend_url = line.strip().split('=')[1].strip('"\'')
                break
    
    print(f"Using backend URL: {backend_url}")
    
    # Setup API tester
    tester = FlipBotAPITester(backend_url)
    
    # Test 1: API Health Check
    tester.run_test("API Health Check", "GET", "")
    
    # Test 2: Initialize mock data
    tester.run_test("Initialize Mock Data", "POST", "initialize-data")
    
    # Test 3: Test Scrapers Status
    success, scraper_test_data = tester.run_test("Test Scrapers Status", "GET", "scrape/test")
    
    if success:
        working_scrapers = [source for source, status in scraper_test_data.items() if status]
        print(f"Working scrapers: {', '.join(working_scrapers)}")
    
    # Test 4: Test the new sorting and filtering features
    tester.test_sorting_filtering()
    
    # Test 5: Test the deals endpoint
    success, deals_data = tester.run_test("Get Deals", "GET", "deals")
    
    if success and deals_data:
        print(f"Found {len(deals_data)} deals")
        
        # Verify deals have profit and ROI data
        all_have_profit = all('est_profit' in vehicle for vehicle in deals_data)
        all_have_roi = all('roi_percent' in vehicle for vehicle in deals_data)
        
        if all_have_profit and all_have_roi:
            print("✅ All deals have profit and ROI data")
            tester.test_results["Deals Data Validation"] = {"success": True}
        else:
            print("❌ Some deals are missing profit or ROI data")
            tester.test_results["Deals Data Validation"] = {"success": False}
    
    # Test 6: Test the trending endpoint
    success, trending_data = tester.run_test("Get Trending", "GET", "trending")
    
    if success and trending_data:
        print(f"Found {len(trending_data)} trending vehicle types")
        
        # Verify trending data has required fields
        all_have_required = all(all(field in item for field in ['make_model', 'avg_price', 'price_change_percent', 'total_listings']) 
                               for item in trending_data)
        
        if all_have_required:
            print("✅ All trending items have required data")
            tester.test_results["Trending Data Validation"] = {"success": True}
        else:
            print("❌ Some trending items are missing required data")
            tester.test_results["Trending Data Validation"] = {"success": False}
    
    # Test 7: Test the available sources endpoint
    tester.test_available_sources()
    
    # Test 8: Test the different scraping strategies
    tester.test_scraping_strategies()
    
    # Test 9: Comprehensive BMW M3 Search with Location
    print("\n🔍 Testing Comprehensive BMW M3 Search with Location...")
    success, bmw_m3_data = tester.run_test(
        "BMW M3 Comprehensive Search", 
        "POST", 
        "scrape/comprehensive", 
        params={"query": "BMW M3", "location": "90210", "max_results": 10}
    )
    
    if success and bmw_m3_data:
        vehicles_found = bmw_m3_data.get("vehicles_found", 0)
        vehicles = bmw_m3_data.get("vehicles", [])
        
        print(f"Found {vehicles_found} BMW M3 vehicles")
        
        if vehicles:
            for i, vehicle in enumerate(vehicles[:3]):  # Show first 3 vehicles
                print(f"\nVehicle {i+1}:")
                print(f"  Make/Model: {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')} {vehicle.get('trim', '')}")
                print(f"  Price: ${vehicle.get('asking_price', 'N/A')}")
                print(f"  Mileage: {vehicle.get('mileage', 'N/A')}")
                print(f"  Location: {vehicle.get('location', 'N/A')}")
                print(f"  Source: {vehicle.get('source', 'N/A')}")
                print(f"  Est. Profit: ${vehicle.get('est_profit', 'N/A')}")
                print(f"  ROI: {vehicle.get('roi_percent', 'N/A')}%")
                print(f"  Flip Score: {vehicle.get('flip_score', 'N/A')}/10")
                
                # Validate vehicle data
                tester.validate_vehicle_data(vehicle, "BMW M3")
            
            # Test is successful if we found at least 1 BMW M3
            if len(vehicles) >= 1:
                print("✅ BMW M3 comprehensive search test PASSED")
                tester.tests_passed += 1
            else:
                print("❌ BMW M3 comprehensive search test FAILED - Not enough matching vehicles found")
            
            tester.tests_run += 1
            tester.test_results["BMW M3 Comprehensive Search Validation"] = {
                "success": len(vehicles) >= 1
            }
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
