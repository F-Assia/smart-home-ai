from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

system_state = {
    "light": False,
    "fan": 0,
    "temperature": 0
}

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/state")
def get_state():
    return jsonify(system_state)

@app.route("/api/light", methods=["POST"])
def set_light():
    data = request.json
    system_state["light"] = data["light"]
    return jsonify({"success": True})

@app.route("/api/fan", methods=["POST"])
def set_fan():
    data = request.json
    system_state["fan"] = data["fan"]
    return jsonify({"success": True})

@app.route("/api/temperature", methods=["POST"])
def set_temperature():
    data = request.json
    system_state["temperature"] = data["temperature"]
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)