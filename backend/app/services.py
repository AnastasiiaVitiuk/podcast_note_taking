import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#generating structures notes from transcript text
def generate_notes(text: str) -> str:

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Create concise, structured podcast notes using bullet points and headings.",
            },
            {
                "role": "user",
                "content": text,
            },
        ],
    )

    return response.choices[0].message.content


def extract_chunk(transcript_segments, timestamp: float, window: int = 20) -> str:

    chunk = [
        seg["text"]
        for seg in transcript_segments
        if (timestamp - window) <= seg["start"] <= (timestamp + window)
    ]

    return " ".join(chunk)