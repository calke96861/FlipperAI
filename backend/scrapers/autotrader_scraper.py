"""
AutoTrader Scraper for FlipBot AI
Scrapes vehicle listings from AutoTrader.com
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode, urlparse, parse_qs
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, VehicleData
from ..server import Source, SellerType

logger = logging.getLogger(__name__)

class AutoTraderScraper(BaseScraper):
    """AutoTrader.com vehicle scraper"""
    
    def __init__(self):
        super().__init__(Source.AUTOTRADER)
        self.base_url = "https://www.autotrader.com"
        
        # AutoTrader-specific selectors
        self.selectors = {
            'listings': [
                '[data-cmp="inventoryListing"]',
                '.inventory-listing',
                '.atc-listing-card',
                '.listing-container'
            ],
            'title': [
                '[data-cmp="inventoryListingTitle"]',
                '.listing-title',
                '.heading-3',
                'h3'
            ],
            'price': [
                '[data-cmp="inventoryListingPrice"]',
                '.first-price',
                '.listing-price',
                '.price-section'
            ],
            'mileage': [
                '[data-cmp="inventoryListingMileage"]',
                '.listing-mileage',
                '.odometer-display'
            ],
            'location': [
                '[data-cmp="inventoryListingLocation"]',
                '.listing-location',
                '.dealer-distance'
            ],
            'dealer_type': [
                '.listing-dealer-type',
                '.seller-type'
            ],
            'listing_url': [
                'a[href*="/cars-for-sale/"]',
                '.listing-title-link'
            ]
        }
    
    def get_search_url(self, query: str, location: str = "") -> str:
        """Generate AutoTrader search URL"""
        params = {
            'searchRadius': '500',
            'isNewSearch': 'true',
            'marketExtension': 'include',
            'showAccelerateBanner': 'false',
            'sortBy': 'relevance',
            'numRecords': '100'
        }
        
        if query:
            # Try to parse make/model from query
            query_parts = query.strip().split()
            if len(query_parts) >= 1:
                params['makeCodeList'] = query_parts[0].upper()
            if len(query_parts) >= 2:
                params['modelCodeList'] = query_parts[1].upper()
        
        if location:
            params['zip'] = location
        
        return f"{self.base_url}/cars-for-sale/all-cars?" + urlencode(params)
    
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape AutoTrader search results"""
        vehicles = []
        
        try:
            search_url = self.get_search_url(query, location)
            logger.info(f"Scraping AutoTrader: {search_url}")
            
            # Use browser for dynamic content
            html = await self.get_with_retry(search_url, use_browser=True)
            if not html:
                logger.error("Failed to get AutoTrader HTML")
                return vehicles
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find listing containers with fallback selectors
            listing_elements = []
            for selector in self.selectors['listings']:
                listing_elements = soup.select(selector)
                if listing_elements:
                    logger.info(f"Found {len(listing_elements)} listings with selector: {selector}")
                    break
            
            if not listing_elements:
                logger.warning("No listings found on AutoTrader")
                return vehicles
            
            # Process each listing
            for i, listing in enumerate(listing_elements[:max_results]):
                try:
                    vehicle = await self._parse_listing(listing, soup)
                    if vehicle and vehicle.asking_price:
                        vehicles.append(vehicle)
                        logger.debug(f"Parsed vehicle {i+1}: {vehicle.year} {vehicle.make} {vehicle.model}")
                except Exception as e:
                    logger.error(f"Error parsing listing {i+1}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(vehicles)} vehicles from AutoTrader")
            
        except Exception as e:
            logger.error(f"AutoTrader scraping failed: {e}")
        
        return vehicles
    
    async def _parse_listing(self, listing_element, full_soup: BeautifulSoup) -> Optional[VehicleData]:
        """Parse individual vehicle listing"""
        vehicle = VehicleData()
        vehicle.source = Source.AUTOTRADER
        
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
            url_element = listing_element.select_one('a[href*="/cars-for-sale/"]')
            if url_element and url_element.get('href'):
                vehicle.url = urljoin(self.base_url, url_element['href'])
            
            # Determine seller type (default to dealer for AutoTrader)
            dealer_type_text = self.extract_with_fallback(listing_element, self.selectors['dealer_type'])
            if dealer_type_text and 'private' in dealer_type_text.lower():
                vehicle.seller_type = SellerType.PRIVATE
            else:
                vehicle.seller_type = SellerType.DEALER
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error parsing AutoTrader listing: {e}")
            return None
