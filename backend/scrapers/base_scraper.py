"""
Base Scraper Class for FlipBot AI
Provides common functionality for all vehicle scrapers
"""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.async_api import async_playwright, Browser, Page
import httpx

from ..models import Source, SellerType

logger = logging.getLogger(__name__)

class VehicleData:
    """Standardized vehicle data structure"""
    def __init__(self):
        self.make: Optional[str] = None
        self.model: Optional[str] = None
        self.trim: Optional[str] = None
        self.year: Optional[int] = None
        self.mileage: Optional[int] = None
        self.asking_price: Optional[float] = None
        self.location: Optional[str] = None
        self.zip_code: Optional[str] = None
        self.seller_type: Optional[SellerType] = None
        self.source: Optional[Source] = None
        self.url: Optional[str] = None
        self.date_listed: Optional[datetime] = None
        self.vin: Optional[str] = None
        self.images: List[str] = []
        self.description: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "make": self.make,
            "model": self.model,
            "trim": self.trim,
            "year": self.year,
            "mileage": self.mileage,
            "asking_price": self.asking_price,
            "location": self.location,
            "zip_code": self.zip_code,
            "seller_type": self.seller_type.value if self.seller_type else None,
            "source": self.source.value if self.source else None,
            "url": self.url,
            "date_listed": self.date_listed,
            "vin": self.vin,
            "images": self.images,
            "description": self.description
        }

class BaseScraper(ABC):
    """Base class for all vehicle scrapers"""
    
    def __init__(self, source: Source):
        self.source = source
        self.ua = UserAgent()
        self.session: Optional[aiohttp.ClientSession] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.request_delay = (1, 3)  # Random delay between requests
        self.max_retries = 3
        self.timeout = 30
        
        # Common selectors that work across multiple sites
        self.common_selectors = {
            'price': [
                '[data-test*="price"]',
                '.price',
                '[class*="price"]',
                '[id*="price"]',
                '.listing-price',
                '.vehicle-price'
            ],
            'mileage': [
                '[data-test*="mileage"]',
                '.mileage',
                '[class*="mileage"]',
                '[class*="odometer"]',
                '.vehicle-mileage'
            ],
            'location': [
                '[data-test*="location"]',
                '.location',
                '[class*="location"]',
                '.dealer-location',
                '.seller-location'
            ],
            'year': [
                '[data-test*="year"]',
                '.year',
                '[class*="year"]'
            ],
            'make_model': [
                '[data-test*="vehicle-title"]',
                '.vehicle-title',
                '.listing-title',
                'h1',
                'h2'
            ]
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize scraper resources"""
        # Initialize HTTP session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': self.ua.random}
        )
        
        # Initialize Playwright browser for dynamic content
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-zygote',
                '--single-process'
            ]
        )
        
        # Create page with random user agent
        self.page = await self.browser.new_page()
        await self.page.set_user_agent(self.ua.random)
        
        # Set viewport to avoid mobile detection
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        
        logger.info(f"Initialized {self.source.value} scraper")
    
    async def cleanup(self):
        """Cleanup scraper resources"""
        if self.session:
            await self.session.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info(f"Cleaned up {self.source.value} scraper")
    
    async def get_with_retry(self, url: str, use_browser: bool = False) -> Optional[str]:
        """Get webpage content with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if use_browser and self.page:
                    await self.page.goto(url, wait_until='domcontentloaded')
                    # Random delay to avoid detection
                    await asyncio.sleep(random.uniform(*self.request_delay))
                    return await self.page.content()
                else:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            await asyncio.sleep(random.uniform(*self.request_delay))
                            return await response.text()
                        elif response.status == 429:
                            # Rate limited, wait longer
                            wait_time = 2 ** attempt
                            logger.warning(f"Rate limited, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
    def extract_with_fallback(self, soup: BeautifulSoup, selectors: List[str], 
                             text_only: bool = True) -> Optional[str]:
        """Extract text using multiple fallback selectors"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True) if text_only else str(element)
                    if text:
                        return text
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        return None
    
    def clean_price(self, price_text: str) -> Optional[float]:
        """Clean and convert price text to float"""
        if not price_text:
            return None
        
        # Remove common price prefixes/suffixes and keep only digits and decimal
        cleaned = re.sub(r'[^\d.,]', '', price_text)
        cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def clean_mileage(self, mileage_text: str) -> Optional[int]:
        """Clean and convert mileage text to int"""
        if not mileage_text:
            return None
        
        # Extract numbers from mileage text
        numbers = re.findall(r'\d+', mileage_text.replace(',', ''))
        if numbers:
            try:
                return int(numbers[0])
            except (ValueError, TypeError):
                pass
        return None
    
    def extract_year_make_model(self, title_text: str) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """Extract year, make, and model from title text"""
        if not title_text:
            return None, None, None
        
        # Common pattern: "2023 Ford F-150" or "2022 Porsche 911"
        match = re.match(r'(\d{4})\s+([A-Za-z]+)\s+(.+)', title_text.strip())
        if match:
            year = int(match.group(1))
            make = match.group(2)
            model = match.group(3).split()[0]  # Take first word of model
            return year, make, model
        
        return None, None, None
    
    def extract_zip_code(self, location_text: str) -> Optional[str]:
        """Extract zip code from location text"""
        if not location_text:
            return None
        
        # Look for 5-digit zip codes
        zip_match = re.search(r'\b\d{5}\b', location_text)
        if zip_match:
            return zip_match.group()
        return None
    
    @abstractmethod
    async def scrape_search_results(self, query: str, location: str = "", 
                                   max_results: int = 50) -> List[VehicleData]:
        """Scrape search results for vehicles"""
        pass
    
    @abstractmethod
    def get_search_url(self, query: str, location: str = "") -> str:
        """Generate search URL for the platform"""
        pass
    
    async def test_scraper(self) -> bool:
        """Test if scraper is working correctly"""
        try:
            test_results = await self.scrape_search_results("BMW", max_results=1)
            return len(test_results) > 0
        except Exception as e:
            logger.error(f"Scraper test failed: {e}")
            return False
