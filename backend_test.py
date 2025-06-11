
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
    
    # Test 2: Test Scrapers Status
    success, scraper_test_data = tester.run_test("Test Scrapers Status", "GET", "scrape/test")
    
    if success:
        working_scrapers = [source for source, status in scraper_test_data.items() if status]
        print(f"Working scrapers: {', '.join(working_scrapers)}")
    
    # Test 3: Live Scraping - 2021 RAM TRX (The main test case for the fix)
    print("\n🔍 Testing Live Scraping for 2021 RAM TRX...")
    success, ram_trx_scrape_data = tester.run_test(
        "2021 RAM TRX Live Scrape", 
        "POST", 
        "scrape/quick", 
        params={"query": "2021 ram trx", "max_results": 5}
    )
    
    if success and ram_trx_scrape_data:
        vehicles_found = ram_trx_scrape_data.get("vehicles_found", 0)
        vehicles = ram_trx_scrape_data.get("vehicles", [])
        
        print(f"Found {vehicles_found} 2021 RAM TRX vehicles")
        
        if vehicles:
            trx_count = 0
            ram_count = 0
            correct_year_count = 0
            price_in_range_count = 0
            
            for i, vehicle in enumerate(vehicles):
                print(f"\nVehicle {i+1}:")
                print(f"  Make/Model: {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')} {vehicle.get('trim', '')}")
                print(f"  Price: ${vehicle.get('asking_price', 'N/A')}")
                print(f"  Mileage: {vehicle.get('mileage', 'N/A')}")
                print(f"  Location: {vehicle.get('location', 'N/A')}")
                print(f"  Dealer: {vehicle.get('seller_type', 'N/A')}")
                print(f"  Source: {vehicle.get('source', 'N/A')}")
                print(f"  URL: {vehicle.get('url', 'N/A')}")
                print(f"  Est. Profit: ${vehicle.get('est_profit', 'N/A')}")
                print(f"  ROI: {vehicle.get('roi_percent', 'N/A')}%")
                
                # Count RAM vehicles
                if vehicle.get('make', '').lower() == 'ram':
                    ram_count += 1
                
                # Count TRX models
                model_trim = f"{vehicle.get('model', '')} {vehicle.get('trim', '')}".lower()
                if 'trx' in model_trim:
                    trx_count += 1
                
                # Count vehicles from 2021-2023
                year = vehicle.get('year')
                if year and (2021 <= year <= 2023):
                    correct_year_count += 1
                
                # Count vehicles in price range $70k-$110k
                price = vehicle.get('asking_price')
                if price and (70000 <= price <= 110000):
                    price_in_range_count += 1
                
                # Validate vehicle data
                tester.validate_vehicle_data(vehicle, "ram trx")
            
            print(f"\nSummary of 2021 RAM TRX search:")
            print(f"  Total vehicles found: {vehicles_found}")
            print(f"  RAM vehicles: {ram_count}/{len(vehicles)}")
            print(f"  TRX models: {trx_count}/{len(vehicles)}")
            print(f"  2021-2023 models: {correct_year_count}/{len(vehicles)}")
            print(f"  $70k-$110k price range: {price_in_range_count}/{len(vehicles)}")
            
            # Test is successful if we found at least 3 RAM TRX vehicles
            if ram_count >= 3 and trx_count >= 3:
                print("✅ 2021 RAM TRX search test PASSED")
                tester.tests_passed += 1
            else:
                print("❌ 2021 RAM TRX search test FAILED - Not enough matching vehicles found")
            
            tester.tests_run += 1
            tester.test_results["2021 RAM TRX Search Validation"] = {
                "success": ram_count >= 3 and trx_count >= 3,
                "ram_count": ram_count,
                "trx_count": trx_count
            }
    
    # Test 4: Live Scraping - RAM TRX (without year)
    print("\n🔍 Testing Live Scraping for RAM TRX (without year)...")
    success, ram_scrape_data = tester.run_test(
        "RAM TRX Live Scrape", 
        "POST", 
        "scrape/quick", 
        params={"query": "ram trx", "max_results": 3}
    )
    
    if success and ram_scrape_data:
        vehicles_found = ram_scrape_data.get("vehicles_found", 0)
        vehicles = ram_scrape_data.get("vehicles", [])
        
        print(f"Found {vehicles_found} RAM TRX vehicles")
        
        if vehicles:
            for i, vehicle in enumerate(vehicles):
                print(f"\nVehicle {i+1}:")
                print(f"  Make/Model: {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')} {vehicle.get('trim', '')}")
                print(f"  Price: ${vehicle.get('asking_price', 'N/A')}")
                print(f"  Mileage: {vehicle.get('mileage', 'N/A')}")
                print(f"  Location: {vehicle.get('location', 'N/A')}")
                print(f"  Dealer: {vehicle.get('seller_type', 'N/A')}")
                print(f"  Source: {vehicle.get('source', 'N/A')}")
                print(f"  URL: {vehicle.get('url', 'N/A')}")
                
                # Validate vehicle data
                tester.validate_vehicle_data(vehicle, "RAM TRX")
    
    # Test 5: Live Scraping - BMW M3
    print("\n🔍 Testing Live Scraping for BMW M3...")
    success, bmw_scrape_data = tester.run_test(
        "BMW M3 Live Scrape", 
        "POST", 
        "scrape/quick", 
        params={"query": "BMW M3", "max_results": 3}
    )
    
    if success and bmw_scrape_data:
        vehicles_found = bmw_scrape_data.get("vehicles_found", 0)
        vehicles = bmw_scrape_data.get("vehicles", [])
        
        print(f"Found {vehicles_found} BMW M3 vehicles")
        
        if vehicles:
            for i, vehicle in enumerate(vehicles):
                print(f"\nVehicle {i+1}:")
                print(f"  Make/Model: {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')} {vehicle.get('trim', '')}")
                print(f"  Price: ${vehicle.get('asking_price', 'N/A')}")
                print(f"  Mileage: {vehicle.get('mileage', 'N/A')}")
                print(f"  Location: {vehicle.get('location', 'N/A')}")
                
                # Validate vehicle data
                tester.validate_vehicle_data(vehicle, "BMW M3")
    
    # Test 6: Live Scraping - 2022 Porsche 911 (year-based search)
    print("\n🔍 Testing Live Scraping for 2022 Porsche 911...")
    success, porsche_scrape_data = tester.run_test(
        "2022 Porsche 911 Live Scrape", 
        "POST", 
        "scrape/quick", 
        params={"query": "2022 Porsche 911", "max_results": 3}
    )
    
    if success and porsche_scrape_data:
        vehicles_found = porsche_scrape_data.get("vehicles_found", 0)
        vehicles = porsche_scrape_data.get("vehicles", [])
        
        print(f"Found {vehicles_found} 2022 Porsche 911 vehicles")
        
        if vehicles:
            for i, vehicle in enumerate(vehicles):
                print(f"\nVehicle {i+1}:")
                print(f"  Make/Model: {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')} {vehicle.get('trim', '')}")
                print(f"  Price: ${vehicle.get('asking_price', 'N/A')}")
                print(f"  Mileage: {vehicle.get('mileage', 'N/A')}")
                print(f"  Location: {vehicle.get('location', 'N/A')}")
                
                # Validate vehicle data
                tester.validate_vehicle_data(vehicle, "Porsche 911")
    
    # Test 7: Live Scraping - Ford Raptor
    print("\n🔍 Testing Live Scraping for Ford Raptor...")
    success, raptor_scrape_data = tester.run_test(
        "Ford Raptor Live Scrape", 
        "POST", 
        "scrape/quick", 
        params={"query": "Ford Raptor", "max_results": 3}
    )
    
    if success and raptor_scrape_data:
        vehicles_found = raptor_scrape_data.get("vehicles_found", 0)
        vehicles = raptor_scrape_data.get("vehicles", [])
        
        print(f"Found {vehicles_found} Ford Raptor vehicles")
        
        if vehicles:
            for i, vehicle in enumerate(vehicles):
                print(f"\nVehicle {i+1}:")
                print(f"  Make/Model: {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')} {vehicle.get('trim', '')}")
                print(f"  Price: ${vehicle.get('asking_price', 'N/A')}")
                print(f"  Mileage: {vehicle.get('mileage', 'N/A')}")
                print(f"  Location: {vehicle.get('location', 'N/A')}")
                
                # Validate vehicle data
                tester.validate_vehicle_data(vehicle, "Ford Raptor")
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
