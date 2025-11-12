# File: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/models.py
from sqlmodel import SQLModel, Field as ORMField
from typing import Optional
from datetime import datetime

class Event(SQLModel, table=True):
    id: Optional[int] = ORMField(default=None, primary_key=True)
    client_id: Optional[str] = ORMField(index=True, nullable=True)
    action: str = ORMField(nullable=False)
    user: Optional[str] = None
    metadata: Optional[str] = None
    created_at: datetime = ORMField(default_factory=datetime.utcnow)
