!pip install faster-whisper torch

from faster_whisper import WhisperModel
import requests
import json

# Load the model (this will download ~1.5GB)
model = WhisperModel("base", device="cuda" if torch.cuda.is_available() else "cpu", compute_type="float16")

# Download the audio
audio_url = "https://pdst.fm/e/pscrb.fm/rss/p/mgln.ai/e/1390/claritaspod.com/measure/p.podderapp.com/2544644999/episode.flightcast.com/01KK9Q3P2XBKGST2RRVG9QPQA4.mp3"
response = requests.get(audio_url)
with open("episode.mp3", "wb") as f:
    f.write(response.content)

print("Audio downloaded, starting transcription...")

# Transcribe
segments, info = model.transcribe("episode.mp3", vad_filter=True)

transcript_segments = []
for segment in segments:
    transcript_segments.append({
        "start": segment.start,
        "end": segment.end,
        "text": segment.text
    })

# Save to JSON
with open("transcript.json", "w") as f:
    json.dump(transcript_segments, f)

print("Transcription complete!")
print(f"Total segments: {len(transcript_segments)}")

# Download the file
from google.colab import files
files.download("transcript.json")