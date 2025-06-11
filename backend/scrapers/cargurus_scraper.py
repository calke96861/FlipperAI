"""
CarGurus Scraper for FlipBot AI
Scrapes vehicle listings from CarGurus.com
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, VehicleData
from ..server import Source, SellerType

logger = logging.getLogger(__name__)

class CarGurusScraper(BaseScraper):
    """CarGurus.com vehicle scraper"""
    
    def __init__(self):
        super().__init__(Source.CARGURUS)
        self.base_url = "https://www.cargurus.com"
        
        # CarGurus-specific selectors
        self.selectors = {
            'listings': [
                '[data-cg-ft="srp-listing-row"]',
                '.srp-listing',
                '.listing-row',
                '.cargurus-listing'
            ],
            'title': [
                '[data-cg-ft="srp-listing-title"]',
                '.listing-title',
                'h4',
                '.vehicle-title'
            ],
            'price': [
                '[data-cg-ft="srp-listing-price"]',
                '.listing-price',
                '.price-section'
            ],
            'mileage': [
                '[data-cg-ft="srp-listing-mileage"]',
                '.listing-mileage',
                '.mileage'
            ],
            'location': [
                '.listing-dealer',
                '.dealer-distance',
                '.location-text'
            ]
        }
    
    def get_search_url(self, query: str, location: str = "") -> str:
        """Generate CarGurus search URL"""
        params = {
            'searchId': '1',
            'sortDir': 'ASC',
            'sortType': 'DEAL_SCORE',
            'maxResults': '100'
        }
        
        if query:
            # Parse make/model from query
            query_parts = query.strip().split()
            if len(query_parts) >= 1:
                params['inventorySearchWidgetType'] = 'AUTO'
                
        if location:
            params['zip'] = location
            params['distance'] = '500'
        
        return f"{self.base_url}/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action?" + urlencode(params)
    
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape CarGurus search results"""
        vehicles = []
        
        try:
            search_url = self.get_search_url(query, location)
            logger.info(f"Scraping CarGurus: {search_url}")
            
            html = await self.get_with_retry(search_url, use_browser=True)
            if not html:
                logger.error("Failed to get CarGurus HTML")
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
                logger.warning("No listings found on CarGurus")
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
            
            logger.info(f"Successfully scraped {len(vehicles)} vehicles from CarGurus")
            
        except Exception as e:
            logger.error(f"CarGurus scraping failed: {e}")
        
        return vehicles
    
    async def _parse_listing(self, listing_element) -> Optional[VehicleData]:
        """Parse individual vehicle listing"""
        vehicle = VehicleData()
        vehicle.source = Source.CARGURUS
        
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
            url_element = listing_element.select_one('a[href*="/VehicleDetails/"]')
            if url_element and url_element.get('href'):
                vehicle.url = urljoin(self.base_url, url_element['href'])
            
            # Default to dealer for CarGurus
            vehicle.seller_type = SellerType.DEALER
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error parsing CarGurus listing: {e}")
            return None
