import os
from faster_whisper import WhisperModel
from groq import Groq

# Load Whisper model once at startup
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

# Groq client — requires GROQ_API_KEY environment variable
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_audio_local(audio_path: str):
    """Transcribe audio using local Whisper model. Returns list of segments."""
    segments, _ = whisper_model.transcribe(audio_path, vad_filter=True)

    transcript_segments = []
    for segment in segments:
        transcript_segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
        })

    return transcript_segments


def generate_notes(text: str, full_episode: bool = False) -> str:
    """Generate structured bullet-point notes using Groq."""
    if full_episode:
        system_prompt = (
            "You are a podcast note-taking assistant. "
            "Create comprehensive, structured notes for the full episode using:\n"
            "- ## headings for main topics\n"
            "- Bullet points starting with '- ' for key insights\n"
            "- **bold** for important terms\n"
            "Keep it concise and easy to scan."
        )
    else:
        system_prompt = (
            "You are a podcast note-taking assistant. "
            "Create brief, focused notes for this specific moment in the podcast. "
            "Use 3-5 bullet points starting with '- ' to capture the key idea being discussed right now."
        )

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content


def extract_chunk(transcript_segments, timestamp: float, window: int = 20) -> str:
    """Extract transcript text within ±window seconds of timestamp."""
    chunk = [
        seg["text"]
        for seg in transcript_segments
        if (timestamp - window) <= seg["start"] <= (timestamp + window)
    ]
    return " ".join(chunk)
