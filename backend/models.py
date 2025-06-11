"""
Shared models for FlipBot AI
Contains enums and data structures used across the application
"""

from enum import Enum

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
