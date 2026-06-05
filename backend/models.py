from pydantic import BaseModel
from typing import Optional

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

class ReplanRequest(BaseModel):
    username: str
    city: str
    budget_per_day: int
    days: int = 3