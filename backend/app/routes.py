from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app import models
from app.services import generate_notes, extract_chunk

router = APIRouter(prefix="/api")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/generate-note")
def generate_note(request: dict, db: Session = Depends(get_db)):
    """
    Generate notes from either full episode or a timestamp segment.
    """

    transcript = request.get("transcript")

    if request.get("full_episode"):
        text = " ".join([seg["text"] for seg in transcript])
    else:
        text = extract_chunk(
            transcript_segments=transcript,
            timestamp=request.get("timestamp"),
        )

    notes = generate_notes(text)

    note = models.Note(
        content=notes,
        timestamp=request.get("timestamp"),
        is_full=request.get("full_episode"),
    )

    db.add(note)
    db.commit()

    return {"note": notes}