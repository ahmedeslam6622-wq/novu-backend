import os
import time
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

app = FastAPI(title="Novu API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# Simple in-memory rate limiter: max 20 requests per IP per hour
rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 20
RATE_WINDOW = 3600

def check_rate(ip: str):
    now = time.time()
    hits = [t for t in rate_store[ip] if now - t < RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
    hits.append(now)
    rate_store[ip] = hits

LENGTH_INSTRUCTIONS = {
    "short":    "Write 3-4 bullet points covering only the most critical ideas.",
    "medium":   "Write 5-7 bullet points covering the key concepts and important details.",
    "detailed": "Write 8-12 bullet points covering all major concepts, examples, and details mentioned.",
}

class SummarizeRequest(BaseModel):
    transcript: str
    length: str = "medium"

@app.post("/summarize")
async def summarize(req: SummarizeRequest, request: Request):
    ip = request.client.host
    check_rate(ip)

    transcript = req.transcript.strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript is empty.")
    if len(transcript) > 50000:
        raise HTTPException(status_code=400, detail="Transcript too long.")

    length_instruction = LENGTH_INSTRUCTIONS.get(req.length, LENGTH_INSTRUCTIONS["medium"])

    prompt = f"""You are a smart study assistant for school students.
A student recorded their class and the speech recognition produced this transcript:

---
{transcript}
---

Summarize the key points from this class in clear, simple language a student can study from.
{length_instruction}
Each bullet point should start with a hyphen (-).
Do not include any introduction or conclusion — just the bullet points.
If the transcript is unclear or too short, do your best with what's there."""

    try:
        response = model.generate_content(prompt)
        summary = response.text.strip()
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Summarization failed. Try again.")

@app.get("/health")
async def health():
    return {"status": "ok"}