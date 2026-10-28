from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import joblib
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import TicketModel
from app.schemas import TicketCreate, TicketResponse


ROOT = Path(__file__).resolve().parent.parent

DEPARTMENT_MODEL_PATH = (
    ROOT / "artifacts" / "department_classifier.joblib"
)
PRIORITY_MODEL_PATH = (
    ROOT / "artifacts" / "priority_classifier.joblib"
)

# Initial demonstration thresholds, not calibrated confidence guarantees.
DEPARTMENT_THRESHOLD = 0.55
PRIORITY_THRESHOLD = 0.55

WARDS = [
    "Ward 1",
    "Ward 2",
    "Ward 3",
    "Ward 4",
    "Ward 5",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DEPARTMENT_MODEL_PATH.exists():
        raise RuntimeError(
            f"Department model missing: {DEPARTMENT_MODEL_PATH}. "
            "Run python train_model.py first."
        )

    if not PRIORITY_MODEL_PATH.exists():
        raise RuntimeError(
            f"Priority model missing: {PRIORITY_MODEL_PATH}. "
            "Run python train_model.py first."
        )

    app.state.department_model = joblib.load(
        DEPARTMENT_MODEL_PATH
    )
    app.state.priority_model = joblib.load(
        PRIORITY_MODEL_PATH
    )

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Smart Municipal Complaint Management System",
    description=(
        "AI-based prediction of municipal complaint department "
        "and priority."
    ),
    version="0.5.0",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {
        "application": "Smart Municipal Complaint Management System",
        "municipality": "Greenfield Municipal Council",
        "stage": 4,
        "message": "Application is running",
        "api_docs": "/docs",
    }


@app.get("/wards")
def list_wards():
    return {"wards": WARDS}


@app.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    request: TicketCreate,
    db: Session = Depends(get_db),
):
    complaint = request.complaint.strip()

    try:
        # Predict department.
        department_model = app.state.department_model
        department_probs = department_model.predict_proba(
            [complaint]
        )[0]

        department_index = int(department_probs.argmax())
        department = str(
            department_model.classes_[department_index]
        )
        department_confidence = float(
            department_probs[department_index]
        )

        # Predict priority independently.
        priority_model = app.state.priority_model
        priority_probs = priority_model.predict_proba(
            [complaint]
        )[0]

        priority_index = int(priority_probs.argmax())
        priority = str(
            priority_model.classes_[priority_index]
        )
        priority_confidence = float(
            priority_probs[priority_index]
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not classify the complaint",
        )

    # Flag a ticket if either prediction has low confidence.
    manual_review = (
        department_confidence < DEPARTMENT_THRESHOLD
        or priority_confidence < PRIORITY_THRESHOLD
    )

    now = datetime.now(timezone.utc)

    ticket = TicketModel(
        ticket_id=f"GMC-{uuid4().hex[:8].upper()}",
        complaint=complaint,
        ward=request.ward,
        department=department,
        priority=priority,
        department_confidence=department_confidence,
        priority_confidence=priority_confidence,
        manual_review=manual_review,
        status=(
            "Needs manual review"
            if manual_review
            else "Submitted"
        ),
        created_at=now,
    )

    try:
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the ticket",
        )


@app.get("/tickets")
def list_tickets(db: Session = Depends(get_db)):
    statement = select(TicketModel).order_by(
        TicketModel.created_at.desc()
    )

    tickets = db.scalars(statement).all()

    return {
        "count": len(tickets),
        "tickets": tickets,
    }


@app.get(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    ticket = db.get(TicketModel, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return ticket