import os
import httpx
from flask import Flask, request, jsonify

WHISPER_URL = os.getenv("WHISPER_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
MODEL_NAME = os.getenv("OLLAMA_MODEL")
VIKUNJA_URL = os.getenv("VIKUNJA_URL")
VIKUNJA_TOKEN = os.getenv("VIKUNJA_TOKEN")

app = Flask(__name__)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    data = file.read()

    # Using httpx in synchronous mode
    with httpx.Client() as client:
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
        result = response.text
    except Exception as e:
        return jsonify({"error": "Invalid JSON from Whisper", "details": str(e)}), 500

    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)