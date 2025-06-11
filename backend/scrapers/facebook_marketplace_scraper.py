"""
Facebook Marketplace Scraper for FlipBot AI
Scrapes vehicle listings from Facebook Marketplace - essential for private party deals
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, VehicleData
from ..models import Source, SellerType

logger = logging.getLogger(__name__)

class FacebookMarketplaceScraper(BaseScraper):
    """Facebook Marketplace vehicle scraper"""
    
    def __init__(self):
        super().__init__(Source.FACEBOOK)
        self.base_url = "https://www.facebook.com"
        
        # Facebook Marketplace-specific selectors
        self.selectors = {
            'listings': [
                '[data-testid="marketplace-item"]',
                '.x9f619',
                '.marketplace-item',
                '[role="article"]'
            ],
            'title': [
                '[data-testid="marketplace-item-title"]',
                '.x1lliihq',
                '.marketplace-item-title'
            ],
            'price': [
                '[data-testid="marketplace-item-price"]',
                '.marketplace-item-price',
                '.x193iq5w'
            ],
            'location': [
                '[data-testid="marketplace-item-location"]',
                '.marketplace-item-location',
                '.x1i10hfl'
            ]
        }
    
    def get_search_url(self, query: str, location: str = "") -> str:
        """Generate Facebook Marketplace search URL"""
        params = {
            'query': query,
            'category': 'vehicles',
            'sortBy': 'creation_time_descend'
        }
        
        if location:
            params['location'] = location
            
        return f"{self.base_url}/marketplace/search?" + urlencode(params)
    
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape Facebook Marketplace search results"""
        vehicles = []
        
        try:
            search_url = self.get_search_url(query, location)
            logger.info(f"Scraping Facebook Marketplace: {search_url}")
            
            # Facebook requires browser automation due to heavy JS
            html = await self.get_with_retry(search_url, use_browser=True)
            if not html:
                logger.error("Failed to get Facebook Marketplace HTML")
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
                logger.warning("No listings found on Facebook Marketplace")
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
            
            logger.info(f"Successfully scraped {len(vehicles)} vehicles from Facebook Marketplace")
            
        except Exception as e:
            logger.error(f"Facebook Marketplace scraping failed: {e}")
        
        return vehicles
    
    async def _parse_listing(self, listing_element) -> Optional[VehicleData]:
        """Parse individual vehicle listing"""
        vehicle = VehicleData()
        vehicle.source = Source.FACEBOOK
        vehicle.seller_type = SellerType.PRIVATE  # Facebook Marketplace is mostly private sellers
        
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
            
            # Extract location
            location_text = self.extract_with_fallback(listing_element, self.selectors['location'])
            if location_text:
                vehicle.location = location_text
                vehicle.zip_code = self.extract_zip_code(location_text)
            
            # Extract listing URL
            url_element = listing_element.select_one('a[href*="/marketplace/item/"]')
            if url_element and url_element.get('href'):
                vehicle.url = urljoin(self.base_url, url_element['href'])
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error parsing Facebook Marketplace listing: {e}")
            return None
