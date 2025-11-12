
from pydantic import BaseModel, Field
from typing import Optional

class EventPayload(BaseModel):
    source: str = Field(..., min_length=1, description="Source of the event")
    message: str = Field(..., min_length=1)
    metadata: Optional[dict] = None
