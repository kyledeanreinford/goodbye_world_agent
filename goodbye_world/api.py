import logging
import os
import re
import json
from functools import wraps

import httpx
from flask import Flask, request, jsonify, abort
from httpx import Timeout

from goodbye_world.tools import TOOLS
from goodbye_world.vikunja import create_vikunja_task

# --- Logging configuration and logger setup ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("API_TOKEN")
WHISPER_URL = os.getenv("WHISPER_URL", "http://localhost:9000/asr")
ANYLIST_URL = os.getenv("ANYLIST_URL", "http://localhost:3000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3")

if not API_TOKEN:
    logger.error("API_TOKEN environment variable is not set")
    raise RuntimeError("API_TOKEN environment variable is required")

app = Flask(__name__)

with open("goodbye_world/system_prompt.txt", "r") as f:
    system_prompt = f.read()

def require_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Bearer token?
        auth = request.headers.get("Authorization", "")
        token = None
        if auth.startswith("Bearer "):
            token = auth.split(None, 1)[1].strip()

        # Or X-API-KEY header
        if not token:
            token = request.headers.get("X-API-KEY", "").strip()

        if token != API_TOKEN:
            logger.warning("Unauthorized request from %s", request.remote_addr)
            abort(401, description="Invalid or missing API token")
        return func(*args, **kwargs)

    return wrapper


def to_camel_case(snake_str: str) -> str:
    parts = snake_str.split('_')
    return parts[0] + ''.join(word.title() for word in parts[1:])


def extract_anylist_payload(tool_call: dict) -> dict:
    args = tool_call.get("arguments", {})
    return {
        to_camel_case(key): value
        for key, value in args.items()
    }


def call_ollama(user_content: str) -> dict:
    """
    Sends a user prompt plus a fixed system prompt and tool definitions to Ollama,
    returns its JSON response, and if a tool call is present, executes it.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "functions": TOOLS,
        "function_call": "auto",
        "stream": False
    }
    logger.debug("Ollama payload: %s", payload)
    with httpx.Client(timeout=Timeout(None)) as client:
        resp = client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        resp_json = resp.json()

    # 2. Extract assistant content
    content = ""
    if isinstance(resp_json.get("message"), dict):
        content = resp_json["message"]["content"]
    elif "choices" in resp_json and resp_json["choices"]:
        content = resp_json["choices"][0]["message"]["content"]

    # 3. Parse for <tool_call>
    m = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL)
    if m:
        logger.info("Tool call: %s", m.group(1))
        try:
            tool_call = json.loads(m.group(1))
        except json.JSONDecodeError:
            resp_json["tool_error"] = "Invalid JSON in tool_call"
            return resp_json

        name = tool_call.get("name")
        args = tool_call.get("arguments", {})
        print("Args: ", args)
        tool_result = None

        if name == "add_anylist_item":
            logger.info("Using add_anylist_item tool")
            try:
                r = httpx.post(f"{ANYLIST_URL}/items", json=extract_anylist_payload(tool_call))
                tool_result = (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)
            except Exception as e:
                tool_result = {"error": str(e)}

        elif name == "add_vikunja_task":
            logger.info("Using add_vikunja_task tool via create_vikunja_task()")
            try:
                tool_result = create_vikunja_task(args)
            except Exception as e:
                logger.error("Error in Vikunja helper: %s", e)
                tool_result = {"error": str(e)}

        else:
            logger.error("Unknown tool requested: %s", name)
            tool_result = {"error": f"Unknown tool: {name}"}

        # 4. Attach results
        resp_json["tool_call"] = tool_call
        resp_json["tool_response"] = tool_result

    return resp_json


@app.route("/", methods=["POST"])
@require_token
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
@require_token
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
    logger.debug("Whisper response: %s", whisper_resp)
    if whisper_resp.status_code != 200:
        return jsonify({
            "error": "Whisper API failed",
            "status_code": whisper_resp.status_code,
            "response": whisper_resp.text
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
