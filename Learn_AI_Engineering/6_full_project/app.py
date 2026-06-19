"""
MODULE 6: THE FULL PROJECT — FIXED API SERVER
===============================================
This serves the fixed waveform classifier as a web API.
It now correctly handles 4 classes: Sine, Square, Triangle, NOISE.

Run:
    cd Learn_AI_Engineering
    python 4_neural_networks/waveform_classifier.py  # train first
    python 6_full_project/app.py                     # then start server

Then open http://localhost:5000 in your browser.
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
import os, sys

# Load our network class from Module 4
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..',"4_neural_networks"))
from network import NeuralNetwork

app = Flask(__name__)
CORS(app)

DATA_DIR     = os.path.join(os.path.dirname(__file__), '..', 'data')
FRONTEND_DIR = os.path.dirname(__file__)

LABELS = {0: "Sine Wave", 1: "Square Wave", 2: "Triangle Wave", 3: "Random Noise"}

def load_model():
    net = NeuralNetwork(input_size=50, hidden1=128, hidden2=64, output_size=4)
    for name in ["W1","b1","W2","b2","W3","b3"]:
        setattr(net, name, np.load(os.path.join(DATA_DIR, f"{name}.npy")))
    return net

try:
    scaler_mean = np.load(os.path.join(DATA_DIR, "scaler_mean.npy"))
    scaler_std  = np.load(os.path.join(DATA_DIR, "scaler_std.npy"))
    model       = load_model()
    print("Model loaded. Server ready.")
except FileNotFoundError:
    print("ERROR: No trained model found.")
    print("Run first: python 4_neural_networks/waveform_classifier.py")
    exit(1)


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/health")
def health():
    return jsonify({"status": "online", "classes": list(LABELS.values())})

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data or "signal" not in data:
        return jsonify({"error": "Send JSON with key 'signal' containing 50 values"}), 400
    signal = np.array(data["signal"], dtype=float)
    if len(signal) != 50:
        return jsonify({"error": f"Expected 50 samples, got {len(signal)}"}), 400
    normalized = (signal - scaler_mean) / scaler_std
    probs      = model.forward(normalized.reshape(1, -1))[0]
    pred_class = int(np.argmax(probs))
    return jsonify({
        "prediction":   LABELS[pred_class],
        "class_id":     pred_class,
        "confidence":   round(float(probs[pred_class]) * 100, 1),
        "probabilities": {
            "sine":     round(float(probs[0]) * 100, 1),
            "square":   round(float(probs[1]) * 100, 1),
            "triangle": round(float(probs[2]) * 100, 1),
            "noise":    round(float(probs[3]) * 100, 1),
        }
    })

@app.route("/demo")
def demo():
    wt = request.args.get("type", "sine")
    t  = np.linspace(0, 2 * np.pi, 50)
    if   wt == "sine":     sig = np.sin(t).tolist()
    elif wt == "square":   sig = np.sign(np.sin(t)).tolist()
    elif wt == "triangle": sig = (2*np.abs(((t)/np.pi)%2-1)-1).tolist()
    elif wt == "noise":    sig = (np.random.randn(50)).tolist()
    else: return jsonify({"error": "type must be sine, square, triangle, or noise"}), 400
    return jsonify({"type": wt, "signal": sig})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
