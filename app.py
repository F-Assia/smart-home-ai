import json
import os
import re
from threading import Lock

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai

from predictor import TemperaturePredictor


load_dotenv()

app = Flask(__name__)
predictor = TemperaturePredictor()
state_lock = Lock()

system_state = {
    "temperature": 0.0,
    "light": False,
    "fan": 0,
}


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def read_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "Request body must be a JSON object."}), 400)
    return data, None


def current_payload():
    prediction = predictor.predict_next()
    with state_lock:
        payload = dict(system_state)
    payload["predicted_temperature"] = prediction
    payload["history"] = predictor.history()
    return payload


def parse_action_with_rules(message):
    text = message.lower()

    if any(word in text for word in ("light", "lamp", "led", "lumiere", "eclairage")):
        if any(word in text for word in ("off", "disable", "eteins", "ferme")):
            return {"action": "light", "value": False}
        if any(word in text for word in ("on", "enable", "allume", "ouvre")):
            return {"action": "light", "value": True}

    if any(word in text for word in ("fan", "ventilation", "ventilateur", "servo")):
        number_match = re.search(r"(\d{1,3})", text)
        if number_match:
            return {"action": "fan", "value": clamp(int(number_match.group(1)), 0, 100)}
        if any(word in text for word in ("off", "stop", "arrete")):
            return {"action": "fan", "value": 0}
        if any(word in text for word in ("max", "full", "maximum")):
            return {"action": "fan", "value": 100}

    return {"action": "none", "value": None}


def extract_json(text):
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def ask_gemini_for_action(message):
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return parse_action_with_rules(message), "local-rules"

    prompt = f"""
You control a smart home dashboard. Convert the user command into exactly one JSON object.

Allowed responses:
{{"action":"light","value":true}}
{{"action":"light","value":false}}
{{"action":"fan","value":0}}
{{"action":"none","value":null}}

Rules:
- Only use action values: light, fan, none.
- Fan value must be an integer from 0 to 100.
- Return JSON only. No markdown, no explanation.

User command: {message}
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        action = extract_json(getattr(response, "text", ""))
        if action:
            return action, "gemini"
    except Exception as exc:
        app.logger.warning("Gemini request failed: %s", exc)

    return parse_action_with_rules(message), "local-rules"


def normalize_action(action):
    if not isinstance(action, dict):
        return {"action": "none", "value": None}

    name = str(action.get("action", "none")).lower()
    value = action.get("value")

    if name == "light":
        if isinstance(value, bool):
            return {"action": "light", "value": value}
        if isinstance(value, str):
            return {"action": "light", "value": value.lower() in ("true", "on", "1", "yes")}
        return {"action": "none", "value": None}

    if name == "fan":
        try:
            return {"action": "fan", "value": clamp(int(value), 0, 100)}
        except (TypeError, ValueError):
            return {"action": "none", "value": None}

    return {"action": "none", "value": None}


def execute_action(action):
    normalized = normalize_action(action)
    with state_lock:
        if normalized["action"] == "light":
            system_state["light"] = normalized["value"]
        elif normalized["action"] == "fan":
            system_state["fan"] = normalized["value"]
    return normalized


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.get("/api/state")
def get_state():
    return jsonify(current_payload())


@app.post("/api/light")
def set_light():
    data, error = read_json()
    if error:
        return error

    value = data.get("light", data.get("value"))
    if not isinstance(value, bool):
        return jsonify({"error": "Field 'light' or 'value' must be a boolean."}), 400

    with state_lock:
        system_state["light"] = value
    return jsonify({"success": True, "state": current_payload()})


@app.post("/api/fan")
def set_fan():
    data, error = read_json()
    if error:
        return error

    value = data.get("fan", data.get("value"))
    try:
        fan = clamp(int(value), 0, 100)
    except (TypeError, ValueError):
        return jsonify({"error": "Field 'fan' or 'value' must be a number from 0 to 100."}), 400

    with state_lock:
        system_state["fan"] = fan
    return jsonify({"success": True, "state": current_payload()})


@app.post("/api/temperature")
def set_temperature():
    data, error = read_json()
    if error:
        return error

    value = data.get("temperature")
    try:
        temperature = round(float(value), 2)
    except (TypeError, ValueError):
        return jsonify({"error": "Field 'temperature' must be numeric."}), 400

    with state_lock:
        system_state["temperature"] = temperature
    predictor.add_temperature(temperature)

    # CORRECTION : On renvoie un JSON ultra-léger sans l'historique pour l'ESP32
    with state_lock:
        return jsonify({
            "success": True, 
            "state": {
                "light": system_state["light"],
                "fan": system_state["fan"]
            }
        })

@app.post("/api/ask")
def ask_ai():
    data, error = read_json()
    if error:
        return error

    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Field 'message' is required."}), 400

    raw_action, source = ask_gemini_for_action(message)
    action = execute_action(raw_action)

    return jsonify({
        "success": True,
        "source": source,
        "message": message,
        "action": action,
        "state": current_payload(),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
