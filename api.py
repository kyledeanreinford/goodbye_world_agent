import os
import re
import json
import httpx
from flask import Flask, request, jsonify
from httpx import Timeout

WHISPER_URL   = os.getenv("WHISPER_URL", "http://localhost:9000/asr")
OLLAMA_URL    = os.getenv("OLLAMA_URL",  "http://localhost:11434/api/chat")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL","qwen3")

app = Flask(__name__)

@app.route("/", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    data = file.read()

    timeout = Timeout(60.0, connect=10.0)
    with httpx.Client(timeout=timeout) as client:
        # 1. Send to Whisper
        resp = client.post(
            WHISPER_URL,
            files={"audio_file": (file.filename, data, file.content_type)}
        )
        if resp.status_code != 200:
            return jsonify({
                "error": "Whisper API failed",
                "status_code": resp.status_code,
                "response": resp.text
            }), resp.status_code

        try:
            transcript = resp.json().get("text", resp.text)
        except Exception:
            transcript = resp.text

        # 2. Build Ollama payload
        ollama_payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Given the input, respond ONLY with a tool call in the form. "
                        "Only add a label if I specify. Due date is optional: \\n"
                        "<tool_call> {\"name\": \"create_task\", \"arguments\": "
                        "{\"title\": \"Buy milk\", \"label\": \"next\", "
                        "\"due_date\": \"2025-05-01T12:00:00Z\"}} "
                        "</tool_call>\\n/no_think"
                    )
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],
            "stream": False
        }

        # 3. Send to Ollama
        ollama_resp = client.post(OLLAMA_URL, json=ollama_payload)

        # 4. Parse Ollama response
        try:
            data = ollama_resp.json()
            if "choices" in data:
                content = data["choices"][0]["message"]["content"]
            elif "message" in data and "content" in data["message"]:
                content = data["message"]["content"]
            else:
                raise ValueError("Unexpected Ollama response structure")

            # Extract JSON from <tool_call>...</tool_call>
            m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
            if not m:
                raise ValueError("Missing <tool_call> wrapper in Ollama response")
            json_str = m.group(1)

            task = json.loads(json_str)
        except Exception as e:
            return jsonify({
                "error": "Invalid JSON from Ollama",
                "details": str(e),
                "raw_response": ollama_resp.text
            }), 500

        return jsonify({
            "transcript": transcript,
            "task": task
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)