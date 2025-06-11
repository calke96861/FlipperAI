"""
Bring a Trailer Scraper for FlipBot AI
Scrapes auction data from BringATrailer.com - premium enthusiast auction platform
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup
from datetime import datetime

from .base_scraper import BaseScraper, VehicleData
from ..models import Source, SellerType

logger = logging.getLogger(__name__)

class BringATrailerScraper(BaseScraper):
    """BringATrailer.com auction scraper"""
    
    def __init__(self):
        super().__init__(Source.BRING_A_TRAILER)
        self.base_url = "https://bringatrailer.com"
        
        # BaT-specific selectors
        self.selectors = {
            'listings': [
                '.auction-item',
                '.auctions-item',
                '.listing-item'
            ],
            'title': [
                '.auction-title',
                '.listing-title',
                'h3 a'
            ],
            'price': [
                '.current-bid',
                '.bid-amount',
                '.price-current'
            ],
            'end_time': [
                '.auction-end',
                '.time-left',
                '.listing-end'
            ],
            'status': [
                '.auction-status',
                '.bid-status'
            ]
        }
    
    def get_search_url(self, query: str, location: str = "") -> str:
        """Generate BaT search URL"""
        params = {
            's': query,
            'show_sold': 'true'  # Include sold auctions for comps
        }
        
        return f"{self.base_url}/search?" + urlencode(params)
    
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape BaT auction results"""
        vehicles = []
        
        try:
            search_url = self.get_search_url(query, location)
            logger.info(f"Scraping Bring a Trailer: {search_url}")
            
            html = await self.get_with_retry(search_url, use_browser=True)
            if not html:
                logger.error("Failed to get BaT HTML")
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
                logger.warning("No listings found on Bring a Trailer")
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
            
            logger.info(f"Successfully scraped {len(vehicles)} vehicles from Bring a Trailer")
            
        except Exception as e:
            logger.error(f"Bring a Trailer scraping failed: {e}")
        
        return vehicles
    
    async def _parse_listing(self, listing_element) -> Optional[VehicleData]:
        """Parse individual auction listing"""
        vehicle = VehicleData()
        vehicle.source = Source.BRING_A_TRAILER
        vehicle.seller_type = SellerType.AUCTION
        
        try:
            # Extract title/vehicle info
            title_text = self.extract_with_fallback(listing_element, self.selectors['title'])
            if title_text:
                year, make, model = self.extract_year_make_model(title_text)
                vehicle.year = year
                vehicle.make = make
                vehicle.model = model
            
            # Extract current bid/final price
            price_text = self.extract_with_fallback(listing_element, self.selectors['price'])
            vehicle.asking_price = self.clean_price(price_text)
            
            # BaT is nationwide
            vehicle.location = "Auction Platform"
            
            # Extract listing URL
            url_element = listing_element.select_one('a[href*="/auction/"]')
            if url_element and url_element.get('href'):
                vehicle.url = urljoin(self.base_url, url_element['href'])
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error parsing BaT listing: {e}")
            return None
