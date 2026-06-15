# Smart Home Assistant with AI and IoT

Academic project using Python 3.13, Flask, Gemini API, ESP32 on Wokwi, DHT22, LED, SG90 servo, scikit-learn, and Chart.js.

## Features

- Live Flask dashboard with temperature, light status, fan speed, and predicted temperature.
- REST API for ESP32 and browser controls.
- Gemini-powered text commands such as `turn on the light` and `set fan to 75 percent`.
- Local fallback command parser for demos without Gemini access.
- Temperature history stored in `data/temperature_history.csv`.
- LinearRegression prediction for the next temperature value.
- Wokwi ESP32 simulation using GPIO 4 for DHT22, GPIO 13 for LED, and GPIO 18 for servo.

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Gemini API Setup

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

The app still works with local rule-based command parsing if the key is missing or the Gemini request fails.

## Running Flask

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## API Endpoints

### GET `/api/state`

Returns the current smart home state, prediction, and recent temperature history.

### POST `/api/light`

```json
{ "light": true }
```

### POST `/api/fan`

```json
{ "fan": 75 }
```

### POST `/api/temperature`

```json
{ "temperature": 28.5 }
```

### POST `/api/ask`

```json
{ "message": "turn on the light" }
```

Example response:

```json
{
  "success": true,
  "action": {
    "action": "light",
    "value": true
  }
}
```

## Wokwi Setup

1. Open Wokwi and create an ESP32 project.
2. Copy `wokwi/sketch.ino` into the sketch editor.
3. Copy `wokwi/diagram.json` into the diagram file.
4. Install/use these Arduino libraries in Wokwi:
   - `DHTesp`
   - `ESP32Servo`
   - `ArduinoJson`
5. Run the Flask server.
6. Update `FLASK_BASE_URL` in `sketch.ino`.

Important: Wokwi running in the browser usually cannot reach `http://127.0.0.1:5000` on your computer directly. Use a tunnel such as ngrok or Cloudflare Tunnel, then replace:

```cpp
const char* FLASK_BASE_URL = "http://127.0.0.1:5000";
```

with your public tunnel URL.

## Demo Instructions

1. Start Flask with `python app.py`.
2. Open the dashboard in the browser.
3. Move the DHT22 temperature slider in Wokwi.
4. Watch the dashboard temperature and Chart.js graph update.
5. Click the light and fan controls on the dashboard.
6. Confirm the Wokwi LED and servo update after polling.
7. Try AI commands:
   - `turn on the light`
   - `turn off the light`
   - `set fan to 75 percent`
   - `set fan to 0`

## Project Structure

```text
smart-home-ai/
+-- app.py
+-- predictor.py
+-- requirements.txt
+-- README.md
+-- data/
+-- templates/
|   +-- dashboard.html
+-- static/
|   +-- style.css
|   +-- script.js
+-- wokwi/
    +-- sketch.ino
    +-- diagram.json
```
