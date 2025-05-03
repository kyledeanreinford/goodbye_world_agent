import os
import httpx
import json
from flask import Flask, request, jsonify
from httpx import Timeout

WHISPER_URL = os.getenv("WHISPER_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
VIKUNJA_URL = os.getenv("VIKUNJA_URL")
VIKUNJA_TOKEN = os.getenv("VIKUNJA_TOKEN")

app = Flask(__name__)


@app.route("/", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    data = file.read()

    timeout = Timeout(60.0, connect=10.0)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            WHISPER_URL,
            files={"audio_file": (file.filename, data, file.content_type)}
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Whisper API failed",
                "status_code": response.status_code,
                "response": response.text
            }), response.status_code

        try:
            transcript = response.json().get("text", response.text)
        except Exception as e:
            transcript = response.text

        # Send transcript to Ollama for task parsing
        ollama_payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a task parser. "
                        "Parse the following transcript into a JSON object representing a task. "
                        "The JSON should have keys: 'title' (string), "
                        "'due_date' (ISO 8601 string or null), "
                        "and 'label' (string or null). "
                    )
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ]
        }
        ollama_response = client.post(OLLAMA_URL, json=ollama_payload)
        if ollama_response.status_code != 200:
            return jsonify({
                "error": "Ollama API failed",
                "status_code": ollama_response.status_code,
                "response": ollama_response.text
            }), ollama_response.status_code

        try:
            llm_result = ollama_response.json()["choices"][0]["message"]["content"]
            task = json.loads(llm_result)
        except Exception as e:
            return jsonify({"error": "Invalid JSON from Ollama", "details": str(e), "raw_response": ollama_response.text}), 500

        return jsonify({
            "transcript": transcript,
            "task": task
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)