"""
Scraping Manager for FlipBot AI
Coordinates all vehicle scrapers and manages scraping operations
"""

import asyncio
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from .base_scraper import VehicleData
from .autotrader_scraper import AutoTraderScraper
from .cars_scraper import CarsScraper
from .cargurus_scraper import CarGurusScraper
from .craigslist_scraper import CraigslistScraper
from ..models import Source, Vehicle, calculate_market_metrics

logger = logging.getLogger(__name__)

@dataclass
class ScrapingJob:
    """Represents a scraping job"""
    query: str
    location: str = ""
    max_results_per_source: int = 20
    sources: List[Source] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.sources is None:
            self.sources = [Source.AUTOTRADER, Source.CARS_COM, Source.CARGURUS, Source.CRAIGSLIST]

@dataclass
class ScrapingResult:
    """Results of a scraping operation"""
    job: ScrapingJob
    vehicles: List[VehicleData]
    source_results: Dict[Source, int]
    errors: Dict[Source, str]
    duration: float
    completed_at: datetime
    
class ScrapingManager:
    """Manages all vehicle scraping operations"""
    
    def __init__(self, db):
        self.db = db
        self.scrapers = {}
        self.active_jobs: Set[str] = set()
        self.job_history: List[ScrapingResult] = []
        self.max_concurrent_scrapers = 3
        
    async def initialize_scrapers(self):
        """Initialize all available scrapers"""
        scraper_classes = {
            Source.AUTOTRADER: AutoTraderScraper,
            Source.CARS_COM: CarsScraper,
            Source.CARGURUS: CarGurusScraper,
            Source.CRAIGSLIST: CraigslistScraper
        }
        
        for source, scraper_class in scraper_classes.items():
            try:
                scraper = scraper_class()
                await scraper.initialize()
                self.scrapers[source] = scraper
                logger.info(f"Initialized {source.value} scraper")
            except Exception as e:
                logger.error(f"Failed to initialize {source.value} scraper: {e}")
    
    async def cleanup_scrapers(self):
        """Cleanup all scrapers"""
        for scraper in self.scrapers.values():
            try:
                await scraper.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up scraper: {e}")
        self.scrapers.clear()
    
    async def scrape_vehicles(self, job: ScrapingJob) -> ScrapingResult:
        """Execute a scraping job across multiple sources"""
        job_id = f"{job.query}_{job.location}_{job.created_at.timestamp()}"
        
        if job_id in self.active_jobs:
            raise ValueError(f"Job {job_id} is already running")
        
        self.active_jobs.add(job_id)
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting scraping job: {job.query} in {job.location or 'all locations'}")
            
            # Prepare tasks for concurrent scraping
            tasks = []
            for source in job.sources:
                if source in self.scrapers:
                    task = self._scrape_source(source, job)
                    tasks.append(task)
                else:
                    logger.warning(f"Scraper for {source.value} not available")
            
            # Execute scraping tasks with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent_scrapers)
            
            async def limited_scrape(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(*[limited_scrape(task) for task in tasks], return_exceptions=True)
            
            # Process results
            all_vehicles = []
            source_results = {}
            errors = {}
            
            for i, result in enumerate(results):
                source = job.sources[i]
                if isinstance(result, Exception):
                    errors[source] = str(result)
                    source_results[source] = 0
                    logger.error(f"Scraping failed for {source.value}: {result}")
                else:
                    vehicles, error = result
                    all_vehicles.extend(vehicles)
                    source_results[source] = len(vehicles)
                    if error:
                        errors[source] = error
            
            # Remove duplicates based on URL and VIN
            unique_vehicles = self._deduplicate_vehicles(all_vehicles)
            
            # Store results in database
            stored_count = await self._store_vehicles(unique_vehicles)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            completed_at = datetime.utcnow()
            
            result = ScrapingResult(
                job=job,
                vehicles=unique_vehicles,
                source_results=source_results,
                errors=errors,
                duration=duration,
                completed_at=completed_at
            )
            
            self.job_history.append(result)
            
            logger.info(f"Scraping job completed: {len(unique_vehicles)} unique vehicles found, "
                       f"{stored_count} stored in database, took {duration:.2f}s")
            
            return result
            
        finally:
            self.active_jobs.discard(job_id)
    
    async def _scrape_source(self, source: Source, job: ScrapingJob) -> tuple[List[VehicleData], Optional[str]]:
        """Scrape vehicles from a single source"""
        scraper = self.scrapers[source]
        error = None
        
        try:
            vehicles = await scraper.scrape_search_results(
                query=job.query,
                location=job.location,
                max_results=job.max_results_per_source
            )
            logger.info(f"Scraped {len(vehicles)} vehicles from {source.value}")
            return vehicles, error
            
        except Exception as e:
            error = str(e)
            logger.error(f"Error scraping {source.value}: {e}")
            return [], error
    
    def _deduplicate_vehicles(self, vehicles: List[VehicleData]) -> List[VehicleData]:
        """Remove duplicate vehicles based on URL and VIN"""
        seen_urls = set()
        seen_vins = set()
        unique_vehicles = []
        
        for i, vehicle in enumerate(vehicles):
            logger.info(f"Processing vehicle {i+1}: make={vehicle.make}, model={vehicle.model}, price={vehicle.asking_price}, url={vehicle.url}")
            
            # Skip if we've seen this URL before
            if vehicle.url and vehicle.url in seen_urls:
                logger.info(f"Skipping vehicle {i+1}: duplicate URL")
                continue
            
            # Skip if we've seen this VIN before (and VIN exists)
            if vehicle.vin and vehicle.vin in seen_vins:
                logger.info(f"Skipping vehicle {i+1}: duplicate VIN")
                continue
            
            # Skip if essential data is missing
            if not vehicle.asking_price:
                logger.info(f"Skipping vehicle {i+1}: missing asking_price")
                continue
            if not vehicle.make:
                logger.info(f"Skipping vehicle {i+1}: missing make")
                continue
            if not vehicle.model:
                logger.info(f"Skipping vehicle {i+1}: missing model")
                continue
            
            if vehicle.url:
                seen_urls.add(vehicle.url)
            if vehicle.vin:
                seen_vins.add(vehicle.vin)
                
            unique_vehicles.append(vehicle)
            logger.info(f"Added vehicle {i+1}: {vehicle.year} {vehicle.make} {vehicle.model}")
        
        logger.info(f"Deduplicated {len(vehicles)} vehicles to {len(unique_vehicles)} unique vehicles")
        return unique_vehicles
    
    async def _store_vehicles(self, vehicles: List[VehicleData]) -> int:
        """Store vehicles in database"""
        stored_count = 0
        
        for vehicle_data in vehicles:
            try:
                # Convert to Vehicle model
                vehicle_dict = vehicle_data.to_dict()
                vehicle = Vehicle(**vehicle_dict)
                
                # Calculate market metrics
                vehicle = calculate_market_metrics(vehicle)
                
                # Check if vehicle already exists (by URL)
                existing = await self.db.vehicles.find_one({"url": vehicle.url})
                if existing:
                    # Update existing vehicle
                    await self.db.vehicles.update_one(
                        {"url": vehicle.url},
                        {"$set": vehicle.dict()}
                    )
                else:
                    # Insert new vehicle
                    await self.db.vehicles.insert_one(vehicle.dict())
                    stored_count += 1
                    
            except Exception as e:
                logger.error(f"Error storing vehicle: {e}")
                continue
        
        return stored_count
    
    async def test_all_scrapers(self) -> Dict[Source, bool]:
        """Test all scrapers to see which are working"""
        results = {}
        
        for source, scraper in self.scrapers.items():
            try:
                test_result = await scraper.test_scraper()
                results[source] = test_result
                logger.info(f"{source.value} scraper test: {'PASS' if test_result else 'FAIL'}")
            except Exception as e:
                results[source] = False
                logger.error(f"{source.value} scraper test failed: {e}")
        
        return results
    
    def get_scraping_stats(self) -> Dict:
        """Get statistics about scraping operations"""
        if not self.job_history:
            return {"total_jobs": 0, "total_vehicles": 0, "avg_duration": 0}
        
        total_vehicles = sum(len(result.vehicles) for result in self.job_history)
        avg_duration = sum(result.duration for result in self.job_history) / len(self.job_history)
        
        source_stats = defaultdict(int)
        for result in self.job_history:
            for source, count in result.source_results.items():
                source_stats[source.value] += count
        
        return {
            "total_jobs": len(self.job_history),
            "total_vehicles": total_vehicles,
            "avg_duration": round(avg_duration, 2),
            "active_jobs": len(self.active_jobs),
            "source_stats": dict(source_stats),
            "last_job": self.job_history[-1].completed_at.isoformat() if self.job_history else None
        }
