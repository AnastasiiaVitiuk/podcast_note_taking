from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import requests
import certifi
import json
import os
import tempfile
import uuid
from threading import Lock

from app.db import SessionLocal
from app import models
from app.services import generate_notes, extract_chunk, groq_client, transcribe_audio_local

router = APIRouter()

# ── In-memory transcription job tracking ────────────────────────────────────
_jobs: dict = {}
_jobs_lock = Lock()

AUDIO_URL = "https://pdst.fm/e/pscrb.fm/rss/p/mgln.ai/e/1390/claritaspod.com/measure/p.podderapp.com/2544644999/episode.flightcast.com/01KK9Q3P2XBKGST2RRVG9QPQA4.mp3"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Background transcription task ────────────────────────────────────────────

def _run_transcription(job_id: str):
    db = SessionLocal()
    temp_path = None
    try:
        with _jobs_lock:
            _jobs[job_id] = {"status": "downloading", "message": "Downloading audio…"}

        print(f"[{job_id}] Downloading audio from {AUDIO_URL}")
        response = requests.get(
            AUDIO_URL,
            verify=certifi.where(),
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=120,
        )
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(response.content)
            temp_path = tmp.name
        print(f"[{job_id}] Downloaded {len(response.content)} bytes to {temp_path}")

        with _jobs_lock:
            _jobs[job_id] = {"status": "transcribing", "message": "Transcribing with Whisper (this may take a few minutes)…"}

        print(f"[{job_id}] Starting Whisper transcription…")
        transcript_segments = transcribe_audio_local(temp_path)
        print(f"[{job_id}] Transcription done: {len(transcript_segments)} segments")

        transcript_json = json.dumps(transcript_segments)
        episode = models.Episode(title="Podcast Episode", transcript=transcript_json)
        db.add(episode)
        db.commit()
        db.refresh(episode)

        with _jobs_lock:
            _jobs[job_id] = {"status": "done", "episode_id": episode.id, "message": "Transcript saved"}

    except Exception as e:
        print(f"[{job_id}] Failed: {e}")
        with _jobs_lock:
            _jobs[job_id] = {"status": "error", "message": str(e)}
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        db.close()


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/transcript-status")
def transcript_status(db: Session = Depends(get_db)):
    episode = db.query(models.Episode).order_by(models.Episode.id.desc()).first()
    if not episode:
        return {"has_transcript": False}
    return {"has_transcript": True, "episode_id": episode.id, "title": episode.title}


@router.post("/transcribe")
def transcribe_episode(background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "starting", "message": "Starting…"}
    background_tasks.add_task(_run_transcription, job_id)
    return {"job_id": job_id}


@router.get("/transcribe/status/{job_id}")
def transcribe_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/upload-transcript")
def upload_transcript(transcript_data: dict, db: Session = Depends(get_db)):
    transcript_json = json.dumps(transcript_data.get("segments", []))

    episode = models.Episode(title="Podcast Episode", transcript=transcript_json)
    db.add(episode)
    db.commit()
    db.refresh(episode)

    return {"episode_id": episode.id, "message": "Transcript uploaded successfully"}


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


@router.get("/episodes/{episode_id}/notes")
def get_episode_notes(episode_id: int, db: Session = Depends(get_db)):
    notes = db.query(models.Note).filter(models.Note.episode_id == episode_id).all()
    return {
        "full_notes": next((n.content for n in notes if n.is_full), None),
        "timestamp_notes": [
            {"timestamp": n.timestamp, "content": n.content}
            for n in notes if not n.is_full
        ],
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
            raise HTTPException(status_code=400, detail="No transcript available. Please transcribe the episode first.")

        transcript_payload = episode.transcript
    else:
        episode = None

    transcript_segments = None
    transcript_text = None

    if isinstance(transcript_payload, list):
        transcript_segments = transcript_payload
        transcript_text = " ".join([str(seg.get("text", "")) for seg in transcript_segments])
    elif isinstance(transcript_payload, str):
        try:
            parsed = json.loads(transcript_payload)
            if isinstance(parsed, list):
                transcript_segments = parsed
                # Extract actual spoken text — not the raw JSON string
                transcript_text = " ".join([str(seg.get("text", "")) for seg in transcript_segments])
            else:
                transcript_text = transcript_payload
        except Exception:
            transcript_text = transcript_payload
    else:
        raise HTTPException(status_code=422, detail="Invalid transcript payload")

    if full_episode:
        text = transcript_text
    else:
        if transcript_segments and timestamp is not None:
            text = extract_chunk(transcript_segments=transcript_segments, timestamp=timestamp)
            if not text.strip():
                raise HTTPException(status_code=400, detail="No transcript content found near this timestamp.")
        else:
            text = f"[timestamp: {timestamp}]\n" + (transcript_text or "")

    notes = generate_notes(text, full_episode=full_episode)

    note_record = models.Note(
        episode_id=episode.id if episode is not None else episode_id,
        content=notes,
        timestamp=timestamp,
        is_full=full_episode,
    )
    db.add(note_record)
    db.commit()

    return {"notes": notes}


@router.get("/debug")
def debug_info():
    return {
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
        "groq_available": groq_client is not None,
        "whisper_model": "faster-whisper base (local)",
    }
