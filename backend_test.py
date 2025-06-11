
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
    
    # Test 2: Get Vehicles
    success, vehicles_data = tester.run_test("Get Vehicles", "GET", "vehicles")
    
    # Test 3: Get Deals
    success, deals_data = tester.run_test("Get Deals", "GET", "deals")
    
    # Test 4: Get Trending
    success, trending_data = tester.run_test("Get Trending", "GET", "trending")
    
    # Test 5: Search Functionality
    success, search_data = tester.run_test("Search Functionality", "GET", "search", params={"q": "BMW"})
    
    # Test 6: Get Stats
    success, stats_data = tester.run_test("Get Stats", "GET", "stats")
    
    # Test 7: Test Scrapers
    success, scraper_test_data = tester.run_test("Test Scrapers", "GET", "scrape/test")
    
    # Test 8: Quick Scrape
    success, quick_scrape_data = tester.run_test(
        "Quick Scrape", 
        "POST", 
        "scrape/quick", 
        params={"query": "BMW", "location": "90210", "max_results": 5}
    )
    
    # Test 9: Get Scraping Stats
    success, scraping_stats_data = tester.run_test("Get Scraping Stats", "GET", "scrape/stats")
    
    # Print summary
    return tester.print_summary()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
