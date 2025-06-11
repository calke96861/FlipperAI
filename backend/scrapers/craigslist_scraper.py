"""
Craigslist Scraper for FlipBot AI
Scrapes vehicle listings from Craigslist
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlencode, urljoin, urlparse
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, VehicleData
from ..server import Source, SellerType

logger = logging.getLogger(__name__)

class CraigslistScraper(BaseScraper):
    """Craigslist vehicle scraper"""
    
    def __init__(self):
        super().__init__(Source.CRAIGSLIST)
        self.base_url = "https://craigslist.org"
        
        # Major metro areas for better coverage
        self.metro_areas = [
            'newyork', 'losangeles', 'chicago', 'houston', 'phoenix',
            'philadelphia', 'sanantonio', 'sandiego', 'dallas', 'seattle',
            'denver', 'boston', 'atlanta', 'miami', 'detroit'
        ]
        
        # Craigslist-specific selectors
        self.selectors = {
            'listings': [
                '.cl-static-search-result',
                '.result-row',
                'li.result-row'
            ],
            'title': [
                '.titlestring',
                '.result-title',
                'a.titlestring'
            ],
            'price': [
                '.result-price',
                '.price'
            ],
            'location': [
                '.result-hood',
                '.hood'
            ],
            'date': [
                '.result-date',
                'time'
            ]
        }
    
    def get_search_url(self, query: str, location: str = "", metro_area: str = "newyork") -> str:
        """Generate Craigslist search URL"""
        params = {
            'sort': 'date',
            'searchNearby': '1',
            'nearbyArea': '680'
        }
        
        if query:
            params['query'] = query
        
        return f"https://{metro_area}.craigslist.org/search/cta?" + urlencode(params)
    
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape Craigslist search results across multiple metro areas"""
        vehicles = []
        
        # Search across multiple metro areas for better coverage
        for metro in self.metro_areas[:3]:  # Limit to 3 metros to avoid overwhelming
            try:
                search_url = self.get_search_url(query, location, metro)
                logger.info(f"Scraping Craigslist {metro}: {search_url}")
                
                html = await self.get_with_retry(search_url, use_browser=False)
                if not html:
                    logger.error(f"Failed to get Craigslist HTML for {metro}")
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find listing containers
                listing_elements = []
                for selector in self.selectors['listings']:
                    listing_elements = soup.select(selector)
                    if listing_elements:
                        logger.info(f"Found {len(listing_elements)} listings in {metro} with selector: {selector}")
                        break
                
                if not listing_elements:
                    logger.warning(f"No listings found on Craigslist {metro}")
                    continue
                
                # Process each listing
                metro_vehicles = []
                for i, listing in enumerate(listing_elements[:max_results//3]):  # Distribute across metros
                    try:
                        vehicle = await self._parse_listing(listing, metro)
                        if vehicle and vehicle.asking_price:
                            metro_vehicles.append(vehicle)
                            logger.debug(f"Parsed vehicle {i+1}: {vehicle.year} {vehicle.make} {vehicle.model}")
                    except Exception as e:
                        logger.error(f"Error parsing listing {i+1} in {metro}: {e}")
                        continue
                
                vehicles.extend(metro_vehicles)
                logger.info(f"Successfully scraped {len(metro_vehicles)} vehicles from Craigslist {metro}")
                
            except Exception as e:
                logger.error(f"Craigslist {metro} scraping failed: {e}")
                continue
        
        logger.info(f"Total Craigslist vehicles scraped: {len(vehicles)}")
        return vehicles
    
    async def _parse_listing(self, listing_element, metro_area: str) -> Optional[VehicleData]:
        """Parse individual vehicle listing"""
        vehicle = VehicleData()
        vehicle.source = Source.CRAIGSLIST
        vehicle.seller_type = SellerType.PRIVATE  # Craigslist is mostly private sellers
        
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
                vehicle.location = f"{location_text}, {metro_area}"
                vehicle.zip_code = self.extract_zip_code(location_text)
            else:
                vehicle.location = metro_area
            
            # Extract listing URL
            url_element = listing_element.select_one('a.titlestring')
            if url_element and url_element.get('href'):
                href = url_element['href']
                if href.startswith('/'):
                    vehicle.url = f"https://{metro_area}.craigslist.org{href}"
                else:
                    vehicle.url = href
            
            return vehicle
            
        except Exception as e:
            logger.error(f"Error parsing Craigslist listing: {e}")
            return None
