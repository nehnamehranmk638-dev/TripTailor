from pydantic import BaseModel
from typing import Optional, Dict, List

class SignupRequest(BaseModel):
    username: str
    password: str
    country: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ItineraryRequest(BaseModel):
    username: str
    city: str
    budget_per_day_usd: float
    days: int = 3
    food_type: Optional[str] = None
    hotel_type: Optional[str] = None
    bedrooms: Optional[int] = 1

class FeedbackRequest(BaseModel):
    username: str
    spot_id: int
    direction: str

class SmartReplanRequest(BaseModel):
    username: str
    city: str
    budget_per_day_usd: float
    days: int = 3
    current_itinerary: dict = {}
    locked_spot_ids: List[int] = []
    disliked_spot_ids: List[int] = []

class NaturalLanguageRequest(BaseModel):
    username: str
    message: str

class MidTripRequest(BaseModel):
    username: str
    message: str
    city: str
    current_itinerary: dict
    day: Optional[int] = None

class SaveTripRequest(BaseModel):
    username: str
    city: str
    country: str
    days: int
    budget_per_day_usd: float
    budget_per_day_local: float
    currency_code: str
    currency_symbol: str
    hotel_type: Optional[str] = None
    bedrooms: Optional[int] = 1
    food_type: Optional[str] = None
    itinerary_data: dict = {}
    hotel_data: dict = {}
    restaurant_data: dict = {}
    trip_name: Optional[str] = None