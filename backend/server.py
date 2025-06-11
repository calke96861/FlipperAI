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

# Enums for vehicle data
class SellerType(str, Enum):
    PRIVATE = "private"
    DEALER = "dealer"
    AUCTION = "auction"

class Source(str, Enum):
    AUTOTRADER = "autotrader"
    CARS_COM = "cars_com"
    CARGURUS = "cargurus"
    CRAIGSLIST = "craigslist"
    FACEBOOK = "facebook"
    EBAY = "ebay"

class ListingStatus(str, Enum):
    NEW = "new"
    WATCHING = "watching"
    CONTACTED = "contacted"
    NEGOTIATING = "negotiating"
    PURCHASED = "purchased"
    LISTED_FOR_SALE = "listed_for_sale"
    SOLD = "sold"
    PASSED = "passed"

# Pydantic Models
class Vehicle(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vin: Optional[str] = None
    make: str
    model: str
    trim: Optional[str] = None
    year: int
    mileage: Optional[int] = None
    asking_price: float
    market_value: Optional[float] = None
    location: str
    zip_code: str
    distance_miles: Optional[int] = None
    seller_type: SellerType
    source: Source
    url: str
    date_listed: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    transport_cost: Optional[float] = None
    est_profit: Optional[float] = None
    roi_percent: Optional[float] = None
    flip_score: Optional[float] = None
    status: ListingStatus = ListingStatus.NEW
    notes: Optional[str] = None
    images: List[str] = Field(default_factory=list)

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

class DealOpportunity(BaseModel):
    vehicle: Vehicle
    opportunity_score: float
    profit_potential: float
    market_comparison: str

# Helper Functions
def calculate_market_metrics(vehicle: Vehicle) -> Vehicle:
    """Calculate market value, profit, ROI, and flip score for a vehicle"""
    if not vehicle.market_value:
        # Mock market value calculation (in real app, this would use ML/market data)
        base_value = vehicle.asking_price * random.uniform(0.9, 1.3)
        vehicle.market_value = round(base_value, 2)
    
    # Calculate estimated profit
    if vehicle.market_value:
        transport_cost = vehicle.transport_cost or 0
        vehicle.est_profit = vehicle.market_value - vehicle.asking_price - transport_cost
        
        # Calculate ROI percentage
        if vehicle.asking_price > 0:
            vehicle.roi_percent = (vehicle.est_profit / vehicle.asking_price) * 100
        
        # Calculate flip score (0-10 scale)
        profit_score = min(vehicle.est_profit / 5000, 5) if vehicle.est_profit > 0 else 0
        roi_score = min(vehicle.roi_percent / 10, 5) if vehicle.roi_percent and vehicle.roi_percent > 0 else 0
        vehicle.flip_score = round(profit_score + roi_score, 1)
    
    return vehicle

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
