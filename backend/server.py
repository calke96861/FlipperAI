from fastapi import FastAPI, APIRouter, HTTPException, Query, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import random

# Import scraping system
from .scrapers.scraping_manager import ScrapingManager, ScrapingJob
from .models import Source, SellerType, ListingStatus, Vehicle, calculate_market_metrics

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="FlipBot AI - Premium Vehicle Intelligence", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize scraping manager
scraping_manager = None

@app.on_event("startup")
async def startup_event():
    global scraping_manager
    scraping_manager = ScrapingManager(db)
    try:
        await scraping_manager.initialize_scrapers()
        logger.info("Scraping system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize scraping system: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global scraping_manager
    if scraping_manager:
        await scraping_manager.cleanup_scrapers()
    client.close()

# Enums for vehicle data

# Pydantic Models

class VehicleCreate(BaseModel):
    make: str
    model: str
    trim: Optional[str] = None
    year: int
    mileage: Optional[int] = None
    asking_price: float
    location: str
    zip_code: str
    seller_type: SellerType
    source: Source
    url: str
    date_listed: Optional[datetime] = None
    vin: Optional[str] = None
    notes: Optional[str] = None

class VehicleUpdate(BaseModel):
    status: Optional[ListingStatus] = None
    notes: Optional[str] = None
    market_value: Optional[float] = None
    transport_cost: Optional[float] = None

class SearchFilters(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    mileage_max: Optional[int] = None
    zip_code: Optional[str] = None
    distance_miles: Optional[int] = None
    source: Optional[Source] = None
    seller_type: Optional[SellerType] = None
    status: Optional[ListingStatus] = None
    min_profit: Optional[float] = None
    min_roi: Optional[float] = None

class MarketTrend(BaseModel):
    make_model: str
    avg_price: float
    price_change_percent: float
    total_listings: int
    avg_days_on_market: Optional[int] = None

class ScrapingJobCreate(BaseModel):
    query: str
    location: Optional[str] = ""
    max_results_per_source: Optional[int] = 20
    sources: Optional[List[Source]] = None
    source_categories: Optional[List[str]] = None  # New field for category-based scraping

class ScrapingJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    vehicles_found: Optional[int] = None
    duration: Optional[float] = None
    source_results: Optional[Dict[str, int]] = None
    categories_used: Optional[List[str]] = None

# Helper Functions
def process_scraped_vehicle(vehicle_data):
    """Convert VehicleData to dict with calculated metrics"""
    try:
        # Convert to Vehicle model for calculations
        vehicle_dict = vehicle_data.to_dict()
        vehicle = Vehicle(**vehicle_dict)
        
        # Calculate market metrics
        vehicle = calculate_market_metrics(vehicle)
        
        return vehicle.dict()
    except Exception as e:
        logger.error(f"Error processing vehicle: {e}")
        # Return basic dict if calculations fail
        return vehicle_data.to_dict()

async def generate_mock_vehicles():
    """Generate mock vehicle data for demonstration"""
    makes_models = [
        ("Porsche", "911", ["Carrera", "Turbo", "GT3"]),
        ("BMW", "M3", ["Competition", "CS"]),
        ("Mercedes", "AMG GT", ["S", "R", "Black Series"]),
        ("Ford", "Raptor", ["SuperCrew", "SuperCab"]),
        ("Chevrolet", "Corvette", ["Stingray", "Z06", "ZR1"]),
        ("Audi", "R8", ["V10", "V10 Plus"]),
        ("Ferrari", "488", ["GTB", "Spider"]),
        ("Lamborghini", "Huracan", ["LP610-4", "Performante"]),
        ("McLaren", "720S", ["Coupe", "Spider"]),
        ("Tesla", "Model S", ["Plaid", "Long Range"])
    ]
    
    locations = [
        ("Los Angeles", "90210"),
        ("Miami", "33101"),
        ("New York", "10001"),
        ("Chicago", "60601"),
        ("Houston", "77001"),
        ("Phoenix", "85001"),
        ("Philadelphia", "19101"),
        ("San Antonio", "78201"),
        ("San Diego", "92101"),
        ("Dallas", "75201")
    ]
    
    sources = list(Source)
    seller_types = list(SellerType)
    
    vehicles = []
    for _ in range(50):
        make, model, trims = random.choice(makes_models)
        location, zip_code = random.choice(locations)
        
        vehicle_data = {
            "make": make,
            "model": model,
            "trim": random.choice(trims),
            "year": random.randint(2018, 2024),
            "mileage": random.randint(5000, 80000),
            "asking_price": random.randint(30000, 200000),
            "location": location,
            "zip_code": zip_code,
            "seller_type": random.choice(seller_types),
            "source": random.choice(sources),
            "url": f"https://example.com/listing/{uuid.uuid4()}",
            "date_listed": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            "transport_cost": random.randint(500, 2000) if random.random() > 0.5 else None
        }
        
        vehicle = Vehicle(**vehicle_data)
        vehicle = calculate_market_metrics(vehicle)
        vehicles.append(vehicle)
    
    return vehicles

# API Routes
@api_router.get("/")
async def root():
    return {"message": "FlipBot AI - Premium Vehicle Intelligence Platform"}

@api_router.get("/vehicles", response_model=List[Vehicle])
async def get_vehicles(
    skip: int = 0,
    limit: int = 20,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    zip_code: Optional[str] = None,
    distance_miles: Optional[int] = None,
    min_profit: Optional[float] = None,
    status: Optional[ListingStatus] = None
):
    """Get vehicles with optional filtering"""
    query = {}
    
    if make:
        query["make"] = {"$regex": make, "$options": "i"}
    if model:
        query["model"] = {"$regex": model, "$options": "i"}
    if year_min:
        query["year"] = {"$gte": year_min}
    if year_max:
        if "year" in query:
            query["year"]["$lte"] = year_max
        else:
            query["year"] = {"$lte": year_max}
    if price_min:
        query["asking_price"] = {"$gte": price_min}
    if price_max:
        if "asking_price" in query:
            query["asking_price"]["$lte"] = price_max
        else:
            query["asking_price"] = {"$lte": price_max}
    if zip_code:
        query["zip_code"] = zip_code
    if min_profit:
        query["est_profit"] = {"$gte": min_profit}
    if status:
        query["status"] = status
    
    vehicles = await db.vehicles.find(query).skip(skip).limit(limit).to_list(None)
    return [Vehicle(**vehicle) for vehicle in vehicles]

@api_router.post("/vehicles", response_model=Vehicle)
async def create_vehicle(vehicle_data: VehicleCreate):
    """Create a new vehicle listing"""
    vehicle = Vehicle(**vehicle_data.dict())
    vehicle = calculate_market_metrics(vehicle)
    
    await db.vehicles.insert_one(vehicle.dict())
    return vehicle

@api_router.get("/vehicles/{vehicle_id}", response_model=Vehicle)
async def get_vehicle(vehicle_id: str):
    """Get a specific vehicle by ID"""
    vehicle = await db.vehicles.find_one({"id": vehicle_id})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return Vehicle(**vehicle)

@api_router.put("/vehicles/{vehicle_id}", response_model=Vehicle)
async def update_vehicle(vehicle_id: str, updates: VehicleUpdate):
    """Update a vehicle listing"""
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    
    result = await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle = await db.vehicles.find_one({"id": vehicle_id})
    return Vehicle(**vehicle)

@api_router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: str):
    """Delete a vehicle listing"""
    result = await db.vehicles.delete_one({"id": vehicle_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"message": "Vehicle deleted successfully"}

@api_router.get("/deals", response_model=List[Vehicle])
async def get_deals(
    min_profit: float = 5000,
    min_roi: float = 10,
    limit: int = 20
):
    """Get top deal opportunities based on profit and ROI"""
    query = {
        "est_profit": {"$gte": min_profit},
        "roi_percent": {"$gte": min_roi}
    }
    
    vehicles = await db.vehicles.find(query).sort("flip_score", -1).limit(limit).to_list(None)
    return [Vehicle(**vehicle) for vehicle in vehicles]

@api_router.get("/trending", response_model=List[MarketTrend])
async def get_trending():
    """Get trending vehicle market data"""
    # Mock trending data - in real app, this would analyze market trends
    trending = [
        MarketTrend(make_model="Porsche 911", avg_price=95000, price_change_percent=4.2, total_listings=15),
        MarketTrend(make_model="BMW M3", avg_price=72000, price_change_percent=3.1, total_listings=23),
        MarketTrend(make_model="Corvette", avg_price=68000, price_change_percent=-1.4, total_listings=18),
        MarketTrend(make_model="Tesla Model S", avg_price=85000, price_change_percent=2.8, total_listings=12),
        MarketTrend(make_model="Ford Raptor", avg_price=58000, price_change_percent=5.7, total_listings=31),
        MarketTrend(make_model="Mercedes AMG GT", avg_price=110000, price_change_percent=1.9, total_listings=8)
    ]
    return trending

@api_router.get("/search")
async def search_vehicles(
    q: str = Query(..., description="Search query for make/model"),
    zip_code: Optional[str] = None,
    distance: Optional[int] = None,
    price_max: Optional[float] = None,
    year_min: Optional[int] = None
):
    """Search vehicles by query string with location and filters"""
    query = {
        "$or": [
            {"make": {"$regex": q, "$options": "i"}},
            {"model": {"$regex": q, "$options": "i"}},
            {"trim": {"$regex": q, "$options": "i"}}
        ]
    }
    
    if zip_code:
        query["zip_code"] = zip_code
    if price_max:
        query["asking_price"] = {"$lte": price_max}
    if year_min:
        query["year"] = {"$gte": year_min}
    
    vehicles = await db.vehicles.find(query).limit(30).to_list(None)
    return [Vehicle(**vehicle) for vehicle in vehicles]

@api_router.post("/initialize-data")
async def initialize_mock_data():
    """Initialize the database with mock vehicle data"""
    # Clear existing data
    await db.vehicles.delete_many({})
    
    # Generate and insert mock data
    mock_vehicles = await generate_mock_vehicles()
    vehicle_dicts = [vehicle.dict() for vehicle in mock_vehicles]
    
    await db.vehicles.insert_many(vehicle_dicts)
    
    return {"message": f"Initialized {len(mock_vehicles)} mock vehicles"}

@api_router.get("/stats")
async def get_stats():
    """Get platform statistics"""
    total_vehicles = await db.vehicles.count_documents({})
    total_deals = await db.vehicles.count_documents({"est_profit": {"$gt": 5000}})
    avg_profit = await db.vehicles.aggregate([
        {"$match": {"est_profit": {"$gt": 0}}},
        {"$group": {"_id": None, "avg_profit": {"$avg": "$est_profit"}}}
    ]).to_list(1)
    
    return {
        "total_vehicles": total_vehicles,
        "deal_opportunities": total_deals,
        "avg_profit": round(avg_profit[0]["avg_profit"], 2) if avg_profit else 0,
        "sources_tracked": len(Source),
        "last_updated": datetime.utcnow()
    }

# ============== LIVE SCRAPING ENDPOINTS ==============

@api_router.post("/scrape", response_model=ScrapingJobResponse)
async def start_scraping(job_data: ScrapingJobCreate, background_tasks: BackgroundTasks):
    """Start a new vehicle scraping job"""
    global scraping_manager
    
    if not scraping_manager:
        raise HTTPException(status_code=503, detail="Scraping system not available")
    
    try:
        # Create scraping job
        job = ScrapingJob(
            query=job_data.query,
            location=job_data.location or "",
            max_results_per_source=job_data.max_results_per_source or 20,
            sources=job_data.sources or [Source.AUTOTRADER, Source.CARS_COM, Source.CARGURUS, Source.CRAIGSLIST]
        )
        
        # Start scraping in background
        job_id = f"{job.query}_{job.location}_{job.created_at.timestamp()}"
        
        # For demo, run synchronously but in production this would be background
        result = await scraping_manager.scrape_vehicles(job)
        
        return ScrapingJobResponse(
            job_id=job_id,
            status="completed",
            message=f"Successfully scraped {len(result.vehicles)} vehicles",
            vehicles_found=len(result.vehicles),
            duration=result.duration,
            source_results={k.value: v for k, v in result.source_results.items()}
        )
        
    except Exception as e:
        logger.error(f"Scraping job failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@api_router.get("/scrape/test", response_model=Dict[str, bool])
async def test_scrapers():
    """Test all scrapers to see which are working"""
    global scraping_manager
    
    if not scraping_manager:
        raise HTTPException(status_code=503, detail="Scraping system not available")
    
    try:
        results = await scraping_manager.test_all_scrapers()
        return {source.value: status for source, status in results.items()}
    except Exception as e:
        logger.error(f"Scraper test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraper test failed: {str(e)}")

@api_router.get("/scrape/stats")
async def get_scraping_stats():
    """Get scraping operation statistics"""
    global scraping_manager
    
    if not scraping_manager:
        raise HTTPException(status_code=503, detail="Scraping system not available")
    
    try:
        stats = scraping_manager.get_scraping_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get scraping stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scraping stats: {str(e)}")

@api_router.post("/scrape/quick")
async def quick_scrape(query: str, location: str = "", max_results: int = 10):
    """Quick scrape for immediate results (limited scope)"""
    global scraping_manager
    
    if not scraping_manager:
        raise HTTPException(status_code=503, detail="Scraping system not available")
    
    try:
        # Quick scrape with most reliable sources
        job = ScrapingJob(
            query=query,
            location=location,
            max_results_per_source=max_results,
            sources=[Source.CARS_COM, Source.CARMAX, Source.CARVANA]  # Fast, reliable sources
        )
        
        result = await scraping_manager.scrape_vehicles(job)
        
        return {
            "query": query,
            "location": location,
            "vehicles_found": len(result.vehicles),
            "duration": result.duration,
            "vehicles": [process_scraped_vehicle(vehicle) for vehicle in result.vehicles[:10]],
            "source_results": {k.value: v for k, v in result.source_results.items()}
        }
        
    except Exception as e:
        logger.error(f"Quick scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick scrape failed: {str(e)}")

@api_router.post("/scrape/comprehensive")
async def comprehensive_scrape(query: str, location: str = "", max_results: int = 20):
    """Comprehensive scrape across all major platforms"""
    global scraping_manager
    
    if not scraping_manager:
        raise HTTPException(status_code=503, detail="Scraping system not available")
    
    try:
        # Comprehensive scrape with all available sources
        job = ScrapingJob(
            query=query,
            location=location,
            max_results_per_source=max_results,
            source_categories=["retail", "marketplace"]  # Broad coverage
        )
        
        result = await scraping_manager.scrape_vehicles(job)
        
        return {
            "query": query,
            "location": location,
            "vehicles_found": len(result.vehicles),
            "duration": result.duration,
            "vehicles": [process_scraped_vehicle(vehicle) for vehicle in result.vehicles[:50]],
            "source_results": {k.value: v for k, v in result.source_results.items()},
            "categories_used": ["retail", "marketplace"]
        }
        
    except Exception as e:
        logger.error(f"Comprehensive scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comprehensive scrape failed: {str(e)}")

@api_router.post("/scrape/enthusiast")
async def enthusiast_scrape(query: str, max_results: int = 15):
    """Scrape enthusiast and auction platforms for special vehicles"""
    global scraping_manager
    
    if not scraping_manager:
        raise HTTPException(status_code=503, detail="Scraping system not available")
    
    try:
        # Enthusiast-focused scrape
        job = ScrapingJob(
            query=query,
            location="",  # Auctions are typically nationwide
            max_results_per_source=max_results,
            source_categories=["auction", "enthusiast"]
        )
        
        result = await scraping_manager.scrape_vehicles(job)
        
        return {
            "query": query,
            "vehicles_found": len(result.vehicles),
            "duration": result.duration,
            "vehicles": [process_scraped_vehicle(vehicle) for vehicle in result.vehicles],
            "source_results": {k.value: v for k, v in result.source_results.items()},
            "categories_used": ["auction", "enthusiast"],
            "note": "Auction and enthusiast platform data - prices may reflect final sale values"
        }
        
    except Exception as e:
        logger.error(f"Enthusiast scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Enthusiast scrape failed: {str(e)}")

@api_router.post("/scrape/private-party")
async def private_party_scrape(query: str, location: str = "", max_results: int = 25):
    """Scrape private party platforms for best deals"""
    global scraping_manager
    
    if not scraping_manager:
        raise HTTPException(status_code=503, detail="Scraping system not available")
    
    try:
        # Private party focused scrape
        job = ScrapingJob(
            query=query,
            location=location,
            max_results_per_source=max_results,
            source_categories=["marketplace"]
        )
        
        result = await scraping_manager.scrape_vehicles(job)
        
        return {
            "query": query,
            "location": location,
            "vehicles_found": len(result.vehicles),
            "duration": result.duration,
            "vehicles": [process_scraped_vehicle(vehicle) for vehicle in result.vehicles],
            "source_results": {k.value: v for k, v in result.source_results.items()},
            "categories_used": ["marketplace"],
            "note": "Private party listings - typically offer best profit margins"
        }
        
    except Exception as e:
        logger.error(f"Private party scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Private party scrape failed: {str(e)}")

@api_router.get("/scrape/sources")
async def get_available_sources():
    """Get all available scraping sources organized by category"""
    return {
        "retail_platforms": [
            {"source": "cars_com", "name": "Cars.com", "description": "Major automotive marketplace"},
            {"source": "autotrader", "name": "AutoTrader", "description": "Leading automotive marketplace"},
            {"source": "cargurus", "name": "CarGurus", "description": "Automotive research and shopping"},
            {"source": "carmax", "name": "CarMax", "description": "Large used car retailer"},
            {"source": "carvana", "name": "Carvana", "description": "Online car retailer with delivery"},
            {"source": "truecar", "name": "TrueCar", "description": "Car buying and pricing platform"},
            {"source": "edmunds", "name": "Edmunds", "description": "Automotive information and classifieds"},
            {"source": "kbb", "name": "Kelley Blue Book", "description": "Vehicle valuation and classifieds"}
        ],
        "online_retailers": [
            {"source": "carmax", "name": "CarMax", "description": "No-haggle used car retailer"},
            {"source": "carvana", "name": "Carvana", "description": "Buy online, delivered to you"},
            {"source": "vroom", "name": "Vroom", "description": "Online car retailer"},
            {"source": "shift", "name": "Shift", "description": "Peer-to-peer car marketplace"}
        ],
        "marketplace_platforms": [
            {"source": "facebook", "name": "Facebook Marketplace", "description": "Local private party deals"},
            {"source": "craigslist", "name": "Craigslist", "description": "Local classified advertisements"},
            {"source": "ebay_motors", "name": "eBay Motors", "description": "Online auction and sales"}
        ],
        "enthusiast_auction": [
            {"source": "bring_a_trailer", "name": "Bring a Trailer", "description": "Enthusiast auction platform"},
            {"source": "cars_and_bids", "name": "Cars & Bids", "description": "Modern enthusiast auctions"},
            {"source": "hemmings", "name": "Hemmings", "description": "Classic and muscle car marketplace"}
        ],
        "analytics_platforms": [
            {"source": "iseecars", "name": "iSeeCars", "description": "Automotive analytics and deals"},
            {"source": "caredge", "name": "CarEdge", "description": "Vehicle analytics and insights"}
        ],
        "dealer_networks": [
            {"source": "autonation", "name": "AutoNation", "description": "Major automotive retailer network"}
        ],
        "valuation_services": [
            {"source": "peddle", "name": "Peddle", "description": "Instant cash offers"},
            {"source": "carsdirect", "name": "CarsDirect", "description": "New car incentives and quotes"}
        ]
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
