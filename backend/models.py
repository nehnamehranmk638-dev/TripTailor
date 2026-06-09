from pydantic import BaseModel
from typing import Optional, Dict, List

class UserCreate(BaseModel):
    username: str

class ItineraryRequest(BaseModel):
    username: str
    city: str
    budget_per_day: int
    days: int = 3

class FeedbackRequest(BaseModel):
    username: str
    spot_id: int
    direction: str

class SlotInfo(BaseModel):
    spot_id: int
    day: int
    time_slot: str

class SmartReplanRequest(BaseModel):
    username: str
    city: str
    budget_per_day: int
    days: int = 3
    current_itinerary: dict = {}
    locked_spot_ids: List[int] = []
    disliked_spot_ids: List[int] = []

class ReplanRequest(BaseModel):
    username: str
    city: str
    budget_per_day: int
    days: int = 3