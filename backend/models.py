"""
Shared models for FlipBot AI
Contains enums and data structures used across the application
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import random

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
    zip_code: Optional[str] = None
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
