import os
import json
from http.server import BaseHTTPRequestHandler
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3.5-flash")

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
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        data = json.loads(body)
        transcript = data.get("transcript", "")
        summary_length = data.get("length", "medium")

        if not transcript:
            self._respond(400, {"error": "Transcript is empty"})
            return

        n = BULLETS.get(summary_length, "5-7")

        prompt = f"""You are a smart study assistant for school students.
A student recorded their class and produced this transcript:
{transcript}
Summarize the key points in clear simple language a student can study from.
Write {n} bullet points each starting with a hyphen (-).
No introduction or conclusion, just the bullet points."""

        try:
            response = model.generate_content(prompt)
            self._respond(200, {"summary": response.text.strip()})
        except Exception:
            self._respond(500, {"error": "Summarization failed. Try again."})

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
