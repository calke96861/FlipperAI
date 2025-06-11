"""
Carvana Scraper for FlipBot AI
Scrapes vehicle listings from Carvana.com - online car retailer
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, VehicleData
from ..models import Source, SellerType

logger = logging.getLogger(__name__)

class CarvanaScraper(BaseScraper):
    """Carvana.com vehicle scraper"""
    
    def __init__(self):
        super().__init__(Source.CARVANA)
        self.base_url = "https://www.carvana.com"
        
        # Carvana-specific selectors
        self.selectors = {
            'listings': [
                '[data-test="result-tile"]',
                '.result-tile',
                '.vehicle-card',
                '.inventory-card'
            ],
            'title': [
                '[data-test="vehicle-year-make-model"]',
                '.result-tile-title',
                '.vehicle-card-title'
            ],
            'price': [
                '[data-test="result-tile-price"]',
                '.result-tile-price',
                '.vehicle-card-price'
            ],
            'mileage': [
                '[data-test="result-tile-mileage"]',
                '.result-tile-mileage',
                '.vehicle-card-mileage'
            ]
        }
    
    def get_search_url(self, query: str, location: str = "") -> str:
        """Generate Carvana search URL"""
        params = {
            'search': query,
            'sort': 'best_match'
        }
        
        if location:
            params['location'] = location
            
        return f"{self.base_url}/cars?" + urlencode(params)
    
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape Carvana search results"""
        vehicles = []
        
        try:
            search_url = self.get_search_url(query, location)
            logger.info(f"Scraping Carvana: {search_url}")
            
            html = await self.get_with_retry(search_url, use_browser=True)
            if not html:
                logger.error("Failed to get Carvana HTML")
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
                logger.warning("No listings found on Carvana")
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
            
            logger.info(f"Successfully scraped {len(vehicles)} vehicles from Carvana")
            
        except Exception as e:
            logger.error(f"Carvana scraping failed: {e}")
        
        return vehicles
    
    async def _parse_listing(self, listing_element) -> Optional[VehicleData]:
        """Parse individual vehicle listing"""
        vehicle = VehicleData()
        vehicle.source = Source.CARVANA
        vehicle.seller_type = SellerType.DEALER  # Carvana is always a dealer
        
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
            
            # Carvana delivers nationwide
            vehicle.location = "Nationwide Delivery"
            
            # Extract listing URL
            url_element = listing_element.select_one('a[href*="/vehicle/"]')
            if url_element and url_element.get('href'):
                vehicle.url = urljoin(self.base_url, url_element['href'])
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error parsing Carvana listing: {e}")
            return None
