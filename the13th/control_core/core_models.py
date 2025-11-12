from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class EventCreate(BaseModel):
    client_id: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    user: Optional[str]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: Optional[str] = None

class EventRead(EventCreate):
    id: int
    created_at: str

class AggregateReport(BaseModel):
    total_events: int
    unique_clients: int
    top_actions: List[Dict[str, Any]] = []
