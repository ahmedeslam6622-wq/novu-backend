import os
import json
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-3.5-flash")

BULLETS = {
    "short": "3-4",
    "medium": "5-7",
    "detailed": "8-12"
}

def handler(request):
    if request.method == "OPTIONS":
        return Response("", headers=cors_headers(), status=200)

    if request.method == "GET":
        return Response(json.dumps({"status": "ok"}), headers=cors_headers(), status=200)

    if request.method == "POST":
        data = request.json()
        transcript = (data.get("transcript") or "").strip()
        length = data.get("length", "medium")

        if not transcript:
            return Response(json.dumps({"error": "Transcript is empty"}), headers=cors_headers(), status=400)

        n = BULLETS.get(length, "5-7")
        prompt = f"""You are a smart study assistant for school students.
A student recorded their class and produced this transcript:
{transcript}
Summarize the key points in clear simple language a student can study from.
Write {n} bullet points each starting with a hyphen (-).
No introduction or conclusion, just the bullet points."""

        try:
            response = model.generate_content(prompt)
            return Response(json.dumps({"summary": response.text.strip()}), headers=cors_headers(), status=200)
        except Exception:
            return Response(json.dumps({"error": "Summarization failed. Try again."}), headers=cors_headers(), status=500)

def cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
