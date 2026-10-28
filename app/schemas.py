from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


WardName = Literal[
    "Ward 1",
    "Ward 2",
    "Ward 3",
    "Ward 4",
    "Ward 5",
]


class TicketCreate(BaseModel):
    complaint: str = Field(
        min_length=10,
        max_length=2000,
    )
    ward: WardName


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    complaint: str
    ward: str
    department: str
    priority: str
    department_confidence: float
    priority_confidence: float
    manual_review: bool
    status: str
    created_at: datetime