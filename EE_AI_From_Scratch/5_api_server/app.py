"""
STEP 5a: THE API SERVER (Flask)
================================
EE Analogy: This is the INTERFACE between the trained model and the outside world.
Like a measurement instrument's GPIB or USB interface — your model is the sensor,
Flask is the driver that lets software communicate with it.

The API accepts:
  POST /predict
  Body: { "signal": [50 float values] }

Returns:
  { "prediction": "sine", "confidence": 0.97, "probabilities": {...} }

How to run:
  python 5_api_server/app.py
  → Server starts at http://localhost:5000
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '3_build_network'))
from neural_network import NeuralNetwork

app = Flask(__name__)
CORS(app)  # allow frontend (different port) to talk to this server

# ─────────────────────────────────────────────
# LOAD TRAINED MODEL ON STARTUP
# ─────────────────────────────────────────────
# EE: like powering up your instrument — it loads its calibration from EEPROM.

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def load_model():
    net = NeuralNetwork(input_size=50, hidden1=64, hidden2=32, output_size=3)
    net.W1 = np.load(os.path.join(DATA_DIR, 'W1.npy'))
    net.b1 = np.load(os.path.join(DATA_DIR, 'b1.npy'))
    net.W2 = np.load(os.path.join(DATA_DIR, 'W2.npy'))
    net.b2 = np.load(os.path.join(DATA_DIR, 'b2.npy'))
    net.W3 = np.load(os.path.join(DATA_DIR, 'W3.npy'))
    net.b3 = np.load(os.path.join(DATA_DIR, 'b3.npy'))
    return net

scaler_mean  = np.load(os.path.join(DATA_DIR, 'scaler_mean.npy'))
scaler_std   = np.load(os.path.join(DATA_DIR, 'scaler_std.npy'))
model        = load_model()

LABELS = {0: 'Sine Wave', 1: 'Square Wave', 2: 'Triangle Wave'}

print("Model loaded successfully. Server ready.")


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    """Simple health check — like a ping command."""
    return jsonify({'status': 'online', 'model': 'waveform-classifier-v1'})


@app.route('/predict', methods=['POST'])
def predict():
    """
    Main prediction endpoint.
    Accepts 50 signal samples, returns the predicted waveform type.
    """
    data = request.get_json()

    if not data or 'signal' not in data:
        return jsonify({'error': 'Send JSON with key "signal" containing 50 values'}), 400

    signal = np.array(data['signal'], dtype=float)

    if len(signal) != 50:
        return jsonify({'error': f'Expected 50 samples, got {len(signal)}'}), 400

    # Normalize using saved scaler parameters (same transform as during training)
    signal_normalized = (signal - scaler_mean) / scaler_std
    signal_batch = signal_normalized.reshape(1, -1)  # shape: (1, 50)

    # Run inference
    probs = model.forward(signal_batch)[0]           # shape: (3,)
    pred_class = int(np.argmax(probs))
    confidence = float(probs[pred_class])

    return jsonify({
        'prediction':    LABELS[pred_class],
        'class_id':      pred_class,
        'confidence':    round(confidence * 100, 1),
        'probabilities': {
            'sine':     round(float(probs[0]) * 100, 1),
            'square':   round(float(probs[1]) * 100, 100),
            'triangle': round(float(probs[2]) * 100, 1),
        }
    })


@app.route('/demo', methods=['GET'])
def demo():
    """
    Returns a real example signal so the frontend has something to test with.
    """
    waveform_type = request.args.get('type', 'sine')
    t = np.linspace(0, 2 * np.pi, 50)

    if waveform_type == 'sine':
        signal = np.sin(t).tolist()
    elif waveform_type == 'square':
        signal = np.where(np.sin(t) > 0, 1.0, -1.0).tolist()
    elif waveform_type == 'triangle':
        signal = (2 * np.abs(((t) / np.pi) % 2 - 1) - 1).tolist()
    else:
        return jsonify({'error': 'type must be sine, square, or triangle'}), 400

    return jsonify({'type': waveform_type, 'signal': signal})


if __name__ == '__main__':
    print("\n" + "="*55)
    print("WAVEFORM CLASSIFIER API")
    print("="*55)
    print("  http://localhost:5000/health   → check if running")
    print("  http://localhost:5000/demo?type=sine  → get sample signal")
    print("  POST /predict {signal:[...50 values...]}  → classify")
    print("\n  Open 5_frontend/index.html in your browser")
    print("="*55 + "\n")
    app.run(debug=True, port=5000)
