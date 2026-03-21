from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
import json
import io

from app.db import SessionLocal
from app import models
from app.services import generate_notes, extract_chunk, client

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/transcribe")
def transcribe_episode(db: Session = Depends(get_db)):
    audio_url = "https://traffic.megaphone.fm/SCIM9175684945.mp3"
    try:
        response = requests.get(audio_url)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download audio: {str(e)}")

    audio_data = io.BytesIO(response.content)
    audio_data.name = "episode.mp3"

    try:
        transcript_response = client.audio.transcriptions.create(
            file=audio_data,
            model="whisper-1",
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    transcript_segments = transcript_response.segments
    transcript_json = json.dumps(transcript_segments)

    episode = models.Episode(title="Podcast Episode", transcript=transcript_json)
    db.add(episode)
    db.commit()
    db.refresh(episode)

    return {"episode_id": episode.id, "message": "Transcription completed"}

@router.post("/episodes")
def create_episode(payload: dict, db: Session = Depends(get_db)):
    title = payload.get("title", "Untitled Episode")
    transcript = payload.get("transcript")

    if not transcript:
        raise HTTPException(status_code=422, detail="Episode transcript is required")

    episode = models.Episode(title=title, transcript=transcript)
    db.add(episode)
    db.commit()
    db.refresh(episode)

    return {"episode_id": episode.id, "title": episode.title}


@router.get("/episodes/latest")
def latest_episode(db: Session = Depends(get_db)):
    episode = db.query(models.Episode).order_by(models.Episode.id.desc()).first()
    if not episode:
        raise HTTPException(status_code=404, detail="No episode found")

    return {
        "episode_id": episode.id,
        "title": episode.title,
        "transcript": episode.transcript,
    }


@router.post("/generate-note")
def generate_note(request: dict, db: Session = Depends(get_db)):
    full_episode = request.get("full_episode", False)
    timestamp = request.get("timestamp")
    episode_id = request.get("episode_id")
    transcript_payload = request.get("transcript")

    if transcript_payload is None:
        if episode_id is not None:
            episode = db.query(models.Episode).filter(models.Episode.id == episode_id).first()
        else:
            episode = db.query(models.Episode).order_by(models.Episode.id.desc()).first()

        if not episode or not episode.transcript:
            raise HTTPException(status_code=400, detail="No transcript available")

        transcript_payload = episode.transcript
    else:
        episode = None

    # normalize transcript payload to text and optionally segments
    transcript_segments = None
    transcript_text = None

    if isinstance(transcript_payload, list):
        transcript_segments = transcript_payload
        transcript_text = " ".join([str(seg.get("text", "")) for seg in transcript_segments])
    elif isinstance(transcript_payload, str):
        transcript_text = transcript_payload
        # try to parse JSON list if serialized list is stored as text
        try:
            import json

            parsed = json.loads(transcript_payload)
            if isinstance(parsed, list):
                transcript_segments = parsed
            # keep transcript_text as str, not losing the raw value
        except Exception:
            pass
    else:
        raise HTTPException(status_code=422, detail="Invalid transcript payload")

    if full_episode:
        text = transcript_text
    else:
        if transcript_segments and timestamp is not None:
            text = extract_chunk(transcript_segments=transcript_segments, timestamp=timestamp)
        else:
            text = f"[timestamp: {timestamp}]\n" + (transcript_text or "")

    notes = generate_notes(text)

    note_record = models.Note(
        episode_id=episode.id if episode is not None else episode_id,
        content=notes,
        timestamp=timestamp,
        is_full=full_episode,
    )

    db.add(note_record)
    db.commit()

    return {"notes": notes}