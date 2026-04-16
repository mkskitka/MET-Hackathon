#!/usr/bin/env python3
"""
Met Hackathon Server

Serves static files (survey, viewer, data) and provides
an API endpoint to convert survey answers into a personalized route.

Usage:
  python3 server.py
  # Then open http://localhost:8000
"""

import json
import sys
import os

sys.path.insert(0, "scripts")

from flask import Flask, request, jsonify, send_from_directory
from survey_to_route import generate_route_with_reasons

app = Flask(__name__, static_folder=".", static_url_path="")


# --- Static file serving ---

@app.route("/")
def index():
    return send_from_directory("viewer", "welcome.html")


@app.route("/survey")
@app.route("/survey/")
def survey():
    return send_from_directory("survey", "survey_test.html")


@app.route("/viewer")
@app.route("/viewer/")
def viewer():
    return send_from_directory("viewer", "index.html")


@app.route("/tour")
def tour():
    return send_from_directory("viewer", "tour.html")


# --- API ---

@app.route("/api/route", methods=["POST"])
def api_generate_route():
    """
    Takes survey answers, returns a personalized route with reasons.

    Input (JSON body):
    {
      "q1": 60,
      "q2": "balanced",
      "q3": "focused",
      "q4": ["ceramics", "jade_hardstone"],
      "q5": ["east_asia", "japan"],
      "q6": "39666",
      "q7": ["42229", "39844"],
      "q8": "207",
      "q9": ["Ancient", "Intricate", "Peaceful", "Elegant", "Spiritual"]
    }

    Output: Full route JSON with reasons, coordinates, artwork picks.
    """
    try:
        answers = request.get_json()
        if not answers:
            return jsonify({"error": "No JSON body provided"}), 400

        import traceback
        print(f"[API] Received survey answers: {json.dumps(answers)[:500]}")

        result = generate_route_with_reasons(answers)
        print(f"[API] Success: {result.get('route_summary', '')[:100]}")
        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# Serve all static files from repo root (MUST be after API routes)
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n  Met Hackathon Server")
    print(f"  ====================")
    print(f"  http://localhost:{port}          → Welcome page")
    print(f"  http://localhost:{port}/survey    → Take the survey")
    print(f"  http://localhost:{port}/viewer    → Map viewer")
    print(f"  http://localhost:{port}/api/route → POST survey answers → route JSON")
    print(f"  http://localhost:{port}/api/health → Health check")
    print()

    app.run(host="0.0.0.0", port=port, debug=False)
