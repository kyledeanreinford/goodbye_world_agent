import logging
import os

import httpx
from flask import Flask, request, jsonify
from httpx import Timeout

from tools import TOOLS

# --- Logging configuration and logger setup ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Environment URLs and model
WHISPER_URL  = os.getenv("WHISPER_URL", "http://localhost:9000/asr")
OLLAMA_URL   = os.getenv("OLLAMA_URL",  "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL","qwen3")

app = Flask(__name__)


# --- Fixed system prompt including tool descriptions ---
SYSTEM_PROMPT = (
    "You are an assistant that picks exactly one tool to call from the list. Respond ONLY with a tool call wrapped in <tool_call> JSON, and no other text.\n\nExample:\n<tool_call> {\"name\": \"add_anylist_item\", \"arguments\": {\"list_name\": \"Grocery\", \"item_name\": \"Milk\", \"quantity\": 1}} </tool_call>\n /no_think"
)


def call_ollama(user_content: str) -> dict:
    """
    Sends a user prompt plus a fixed system prompt and tool definitions to Ollama,
    returning its JSON response.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content}
        ],
        "functions": TOOLS,
        "function_call": "auto",
        "stream": False
    }
    logger.debug("Ollama payload: %s", payload)
    with httpx.Client(timeout=Timeout(None)) as client:
        resp = client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


@app.route("/", methods=["POST"])
def text_endpoint():
    """
    Text‑input endpoint.
    Expects JSON: { "prompt": "Your prompt here" }
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    body = request.get_json()
    prompt = body.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "No 'prompt' field provided"}), 400

    logger.info("/text prompt: %s", prompt)
    try:
        result = call_ollama(prompt)
        return jsonify(result), 200
    except Exception as e:
        logger.error("Ollama error: %s", e)
        return jsonify({"error": "Ollama request failed", "details": str(e)}), 500


@app.route("/audio", methods=["POST"])
def audio_endpoint():
    """
    Audio‑upload endpoint.
    Expects multipart‑form with key 'file'.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    data = file.read()
    logger.info("/audio received file: %s (%d bytes)", file.filename, len(data))

    # Transcribe via Whisper
    with httpx.Client(timeout=Timeout(None)) as client:
        whisper_resp = client.post(
            WHISPER_URL,
            files={"audio_file": (file.filename, data, file.content_type)}
        )
    if whisper_resp.status_code != 200:
        return jsonify({
            "error":       "Whisper API failed",
            "status_code": whisper_resp.status_code,
            "response":    whisper_resp.text
        }), whisper_resp.status_code

    transcript = None
    try:
        transcript = whisper_resp.json().get("text", whisper_resp.text)
    except ValueError:
        transcript = whisper_resp.text

    logger.info("/audio transcript: %s", transcript)
    try:
        result = call_ollama(transcript)
        return jsonify({"transcript": transcript, "ollama_response": result}), 200
    except Exception as e:
        logger.error("Ollama error: %s", e)
        return jsonify({"error": "Ollama request failed", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
