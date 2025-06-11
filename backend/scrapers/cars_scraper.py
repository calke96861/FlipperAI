"""
Cars.com Scraper for FlipBot AI
Scrapes vehicle listings from Cars.com
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, VehicleData
from ..models import Source, SellerType

logger = logging.getLogger(__name__)

class CarsScraper(BaseScraper):
    """Cars.com vehicle scraper"""
    
    def __init__(self):
        super().__init__(Source.CARS_COM)
        self.base_url = "https://www.cars.com"
        
        # Cars.com-specific selectors
        self.selectors = {
            'listings': [
                '.vehicle-card',
                '.listing-row',
                '.srp-listing',
                '[data-test="vehicle-card"]'
            ],
            'title': [
                '.vehicle-card-link',
                '.vehicle-card-title',
                '.listing-title',
                'h3 a',
                '.vehicle-details h3 a',
                '.vehicle-card h3 a'
            ],
            'price': [
                '.primary-price',
                '.vehicle-card-price',
                '.listing-price'
            ],
            'mileage': [
                '.vehicle-card-mileage',
                '.mileage',
                '.odometer'
            ],
            'location': [
                '.dealer-name',
                '.vehicle-card-location',
                '.listing-location'
            ],
            'dealer_type': [
                '.dealer-type',
                '.seller-type'
            ]
        }
    
    def get_search_url(self, query: str, location: str = "") -> str:
        """Generate Cars.com search URL"""
        params = {
            'page_size': '100',
            'sort': 'best_match_desc'
        }
        
        if query:
            params['keyword'] = query
        
        if location:
            params['zip'] = location
            params['maximum_distance'] = '500'
        
        return f"{self.base_url}/shopping/results/?" + urlencode(params)
    
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape Cars.com search results"""
        vehicles = []
        
        try:
            search_url = self.get_search_url(query, location)
            logger.info(f"Scraping Cars.com: {search_url}")
            
            # Use browser for better compatibility
            html = await self.get_with_retry(search_url, use_browser=True)
            if not html:
                logger.error("Failed to get Cars.com HTML")
                return vehicles
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find listing containers
            listing_elements = []
            for selector in self.selectors['listings']:
                listing_elements = soup.select(selector)
                if listing_elements:
                    logger.info(f"Found {len(listing_elements)} listings with selector: {selector}")
                    break
            
            if not listing_elements:
                logger.warning("No listings found on Cars.com")
                return vehicles
            
            # Process each listing
            for i, listing in enumerate(listing_elements[:max_results]):
                try:
                    vehicle = await self._parse_listing(listing)
                    if vehicle and vehicle.asking_price:
                        vehicles.append(vehicle)
                        logger.debug(f"Parsed vehicle {i+1}: {vehicle.year} {vehicle.make} {vehicle.model}")
                except Exception as e:
                    logger.error(f"Error parsing listing {i+1}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(vehicles)} vehicles from Cars.com")
            
        except Exception as e:
            logger.error(f"Cars.com scraping failed: {e}")
        
        return vehicles
    
    async def _parse_listing(self, listing_element) -> Optional[VehicleData]:
        """Parse individual vehicle listing"""
        vehicle = VehicleData()
        vehicle.source = Source.CARS_COM
        
        try:
            # Extract title/vehicle info
            title_text = self.extract_with_fallback(listing_element, self.selectors['title'])
            if title_text:
                year, make, model = self.extract_year_make_model(title_text)
                vehicle.year = year
                vehicle.make = make
                vehicle.model = model
            
            # Extract price
            price_text = self.extract_with_fallback(listing_element, self.selectors['price'])
            vehicle.asking_price = self.clean_price(price_text)
            
            # Extract mileage
            mileage_text = self.extract_with_fallback(listing_element, self.selectors['mileage'])
            vehicle.mileage = self.clean_mileage(mileage_text)
            
            # Extract location
            location_text = self.extract_with_fallback(listing_element, self.selectors['location'])
            if location_text:
                vehicle.location = location_text
                vehicle.zip_code = self.extract_zip_code(location_text)
            
            # Extract listing URL
            url_element = listing_element.select_one('a[href*="/vehicledetail/"]')
            if url_element and url_element.get('href'):
                vehicle.url = urljoin(self.base_url, url_element['href'])
            
            # Default to dealer for Cars.com
            vehicle.seller_type = SellerType.DEALER
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error parsing Cars.com listing: {e}")
            return None
