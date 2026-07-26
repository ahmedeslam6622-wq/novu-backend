import os
import json
import tempfile
from http.server import BaseHTTPRequestHandler
from groq import Groq

groq = Groq(api_key=os.environ["GROQ_API_KEY"])

BULLETS = {
    "short": "3-4",
    "medium": "5-7",
    "detailed": "8-12"
}

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        self._respond(200, {"status": "ok"})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")

        if "audio" in content_type or "octet-stream" in content_type:
            audio_data = self.rfile.read(content_length)
            if not audio_data:
                self._respond(400, {"error": "No audio received"})
                return
            try:
                with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                    f.write(audio_data)
                    tmp_path = f.name
                with open(tmp_path, "rb") as f:
                    transcription = groq.audio.transcriptions.create(
                        file=("audio.webm", f, "audio/webm"),
                        model="whisper-large-v3",
                        response_format="text"
                    )
                os.unlink(tmp_path)
                self._respond(200, {"transcript": transcription.strip()})
            except Exception as e:
                self._respond(500, {"error": f"Transcription failed: {str(e)}"})
            return

        if "application/json" in content_type:
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except Exception:
                self._respond(400, {"error": "Invalid JSON"})
                return

            transcript = (data.get("transcript") or "").strip()
            length = data.get("length", "medium")

            if not transcript:
                self._respond(400, {"error": "Transcript is empty"})
                return

            n = BULLETS.get(length, "5-7")
            prompt = f"""You are a smart study assistant for school students.
A student recorded their class and produced this transcript:
{transcript}
Summarize ONLY what was said in class. Do not add, change, or correct any facts from the transcript.
If something sounds wrong, summarize it exactly as the teacher said it.
Write {n} bullet points in clear simple language a student can study from.
Each bullet point starts with a hyphen (-).
No introduction or conclusion, just the bullet points."""

            try:
                response = groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1024
                )
                summary = response.choices[0].message.content.strip()
                self._respond(200, {"summary": summary})
            except Exception as e:
                self._respond(500, {"error": f"Summarization failed: {str(e)}"})
            return

        self._respond(400, {"error": "Unsupported content type"})

    def _respond(self, code, body):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
