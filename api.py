import os
import re
import json
import httpx
from flask import Flask, request, jsonify
from httpx import Timeout
from ollama import Client

WHISPER_URL    = os.getenv("WHISPER_URL",    "http://localhost:9000/asr")
OLLAMA_URL     = os.getenv("OLLAMA_URL",     "http://localhost:11434/api/chat")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL",   "qwen3")
OLLAMA_HEADERS = {"x-some-header": "some-value"}

app = Flask(__name__)

ollama_client = Client(
    host='http://localhost:11434',
    headers=OLLAMA_HEADERS
)

SYSTEM_PROMPT = (
    "Given the input, respond ONLY with a tool call in the form. "
    "Only add a label if I specify. Due date is optional:\n"
    "<tool_call> {\"name\": \"create_task\", \"arguments\": "
    "{\"title\": \"Buy milk\", \"label\": \"next\", "
    "\"due_date\": \"2025-05-01T12:00:00Z\"}} "
    "</tool_call>\n/no_think"
)

def call_ollama(user_content: str):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": user_content}
        ],
        "stream": False
    }
    resp = ollama_client.post(OLLAMA_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    # unwrap either /choices[0]/message/content or /message/content
    content = (
        data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        or data.get("message", {}).get("content")
        or ""
    )

    m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
    if not m:
        raise ValueError("Missing <tool_call> wrapper in Ollama response")
    return json.loads(m.group(1))


@app.route('/test', methods=['GET'])
def test():
    resp = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": "What is the capital of France? /no_think"}],
        stream=False
    )
    return resp.message.content, 200


@app.route('/', methods=['POST'])
def text_input():
    """
    Expects JSON: { "text": "Your task description here" }
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    body = request.get_json()
    text = body.get("text", "").strip()
    if not text:
        return jsonify({"error": "No 'text' field provided"}), 400

    try:
        task = call_ollama(text)
    except Exception as e:
        return jsonify({
            "error": "Failed to parse Ollama response",
            "details": str(e)
        }), 500

    return jsonify({
        "input": text,
        "task": task
    })


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Same as your old '/', but moved to /transcribe.
    Expects form‑data with key 'file'.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    data = file.read()

    # 1. Send to Whisper
    timeout = Timeout(60.0, connect=10.0)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            WHISPER_URL,
            files={"audio_file": (file.filename, data, file.content_type)}
        )
    if resp.status_code != 200:
        return jsonify({
            "error":          "Whisper API failed",
            "status_code":    resp.status_code,
            "response":       resp.text
        }), resp.status_code

    try:
        transcript = resp.json().get("text", resp.text)
    except ValueError:
        transcript = resp.text

    # 2–4. Call Ollama & parse out the <tool_call>
    try:
        task = call_ollama(transcript)
    except Exception as e:
        return jsonify({
            "error":        "Invalid JSON from Ollama",
            "details":      str(e),
            "raw_response": None
        }), 500

    return jsonify({
        "transcript": transcript,
        "task":       task
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)