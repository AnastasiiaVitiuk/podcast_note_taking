from fastapi import FastAPI 
from pydantic import BaseModel
from fastapi.middleware import CORSMiddleware
import json
import requests

app = FastAPI()

# connecting to frondend
app.add.middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("..data/transcript.json") as f:
    transcript = json.load(f)["segments"]

class NoteRequest(BaseModel):
    timestamp: float = None
    full_episode: bool = False

# for more precision, extracting hte time chunk around the timestamp
def around_chunck(timestamp, window=20):
    chunk = []
    for segment in transcript:
        if (timestamp - window) <= segment["start"] <= (timestamp + window):
            chunk.append(segment)

    return "".join([segment["text"] for segment in chunk])

def note_taking(text):
    prompt = f"""You are a helpful assistant that take notes for a podcast episode. 
    It should be in a consice and clear format, with bullet points and headings if necessary.
    Here is the text you need to take notes from: {text}. """

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"       },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7
        }
    )

    return response.json()["choices"][0]["message"]["content"]

@app.post("genetaye-note")
def generate_note(request: NoteRequest):
    if request.full_episode:
        text = " ".join([seg["text"] for seg in transcript])
    else:
        text = around_chunck(request.timestamp)

    notes = note_taking(text)

    return {"notes": notes}

