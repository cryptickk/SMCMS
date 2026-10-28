from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TicketModel(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(
        String(20), primary_key=True
    )
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    ward: Mapped[str] = mapped_column(String(30), nullable=False)

    department: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    department_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    priority_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    manual_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="Submitted"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )