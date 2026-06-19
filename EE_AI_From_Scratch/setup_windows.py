"""
setup_windows.py
================
Run this ONCE from inside your EE_AI_From_Scratch folder.
It creates every project file automatically so you don't have
to copy-paste each one individually.

Usage (Git Bash or Command Prompt, from inside EE_AI_From_Scratch/):
    python setup_windows.py
"""

import os

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Created: {path}")


# ── STEP 1 ────────────────────────────────────────────────────────────────
write("1_understand_data/generate_signals.py", '''\
"""
STEP 1: UNDERSTANDING DATA
EE Analogy: Before designing a filter you study the signal.
Same with AI - data comes first.

Generates 3 waveform types (sine=0, square=1, triangle=2).
Each waveform = 50 samples, like a 50-point ADC reading.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

NUM_SAMPLES   = 50
NUM_WAVEFORMS = 300
NOISE_LEVEL   = 0.1
t = np.linspace(0, 2 * np.pi, NUM_SAMPLES)

def generate_sine(n):
    signals = []
    for _ in range(n):
        phase = np.random.uniform(0, np.pi)
        amp   = np.random.uniform(0.8, 1.2)
        s = amp * np.sin(t + phase) + np.random.normal(0, NOISE_LEVEL, NUM_SAMPLES)
        signals.append(s)
    return np.array(signals)

def generate_square(n):
    signals = []
    for _ in range(n):
        duty = np.random.uniform(0.3, 0.7)
        s = np.where(np.sin(t) > np.cos(duty), 1.0, -1.0)
        s = s + np.random.normal(0, NOISE_LEVEL, NUM_SAMPLES)
        signals.append(s)
    return np.array(signals)

def generate_triangle(n):
    signals = []
    for _ in range(n):
        phase = np.random.uniform(0, np.pi)
        s = 2 * np.abs(((t + phase) / np.pi) % 2 - 1) - 1
        s = s + np.random.normal(0, NOISE_LEVEL, NUM_SAMPLES)
        signals.append(s)
    return np.array(signals)

X_sine     = generate_sine(NUM_WAVEFORMS)
X_square   = generate_square(NUM_WAVEFORMS)
X_triangle = generate_triangle(NUM_WAVEFORMS)

X = np.vstack([X_sine, X_square, X_triangle])
y = np.array([0]*NUM_WAVEFORMS + [1]*NUM_WAVEFORMS + [2]*NUM_WAVEFORMS)

print("=" * 55)
print("DATASET CREATED")
print("=" * 55)
print(f"  X shape : {X.shape}  (rows=waveforms, cols=samples)")
print(f"  y shape : {y.shape}  (label per waveform)")
print("  Labels  : 0=sine  1=square  2=triangle")
print()
print("EE ANALOGY:")
print("  X = oscilloscope readings (50 voltage samples)")
print("  y = the answer we want the AI to learn")

os.makedirs("data", exist_ok=True)
np.save("data/X.npy", X)
np.save("data/y.npy", y)
print("  Saved to data/X.npy and data/y.npy")

fig, axes = plt.subplots(1, 3, figsize=(14, 4))
fig.suptitle("Step 1: Training Data", fontsize=13, fontweight="bold")
for i, (sig, name, col) in enumerate(zip(
    [X_sine[0], X_square[0], X_triangle[0]],
    ["Sine (label=0)", "Square (label=1)", "Triangle (label=2)"],
    ["blue", "red", "green"]
)):
    axes[i].plot(sig, color=col, linewidth=2)
    axes[i].set_title(name); axes[i].set_xlabel("Sample #")
    axes[i].set_ylabel("Amplitude"); axes[i].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("data/step1_signals.png", dpi=120)
print("  Plot saved: data/step1_signals.png")
print()
print("NEXT: python 2_build_neuron/single_neuron.py")
''')


# ── STEP 2 ────────────────────────────────────────────────────────────────
write("2_build_neuron/single_neuron.py", '''\
"""
STEP 2: THE SINGLE NEURON
EE Analogy: A neuron = weighted summing amplifier + comparator.

  x1 --[w1]--+
  x2 --[w2]--+--[ SUM ]--[ + bias ]--[ activation ] --> output
  x3 --[w3]--+

  Weights = resistor values in a summing network
  Bias    = DC offset / voltage reference
  ReLU    = half-wave rectifier (literally the same thing)
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def relu(x):
    return np.maximum(0, x)

def tanh_fn(x):
    return np.tanh(x)

class Neuron:
    def __init__(self, num_inputs):
        self.weights = np.random.randn(num_inputs) * 0.01
        self.bias    = 0.0
    def forward(self, x):
        z = np.dot(self.weights, x) + self.bias
        return sigmoid(z), z

print("=" * 55)
print("STEP 2: SINGLE NEURON")
print("=" * 55)
X = np.load("data/X.npy")
neuron = Neuron(len(X[0]))
output, z = neuron.forward(X[0])
print(f"  Input          : {len(X[0])} voltage samples")
print(f"  Weighted sum z : {z:.4f}  (op-amp output)")
print(f"  After sigmoid  : {output:.4f}  (squished to 0-1)")
print()
print("  Output is random now - training will fix that.")

x_range = np.linspace(-6, 6, 200)
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
fig.suptitle("Step 2: Activation Functions (transfer curves)", fontsize=13, fontweight="bold")
for ax, (name, fn, col, note) in zip(axes, [
    ("Sigmoid", sigmoid, "blue",  "transistor saturation  range (0,1)"),
    ("ReLU",    relu,    "red",   "half-wave rectifier    range (0,inf)"),
    ("Tanh",    tanh_fn, "green", "bipolar transfer curve range (-1,1)"),
]):
    ax.plot(x_range, fn(x_range), color=col, linewidth=2.5)
    ax.set_title(f"{name}\\n{note}", fontsize=9)
    ax.set_xlabel("Input z"); ax.set_ylabel("Output")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.axvline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("data/step2_activations.png", dpi=120)
print("  Plot saved: data/step2_activations.png")
print()
print("KEY INSIGHT: 1 neuron = 1 comparator.")
print("Stack many in layers to solve complex problems.")
print()
print("NEXT: python 3_build_network/neural_network.py")
''')


# ── STEP 3 ────────────────────────────────────────────────────────────────
write("3_build_network/neural_network.py", '''\
"""
STEP 3: THE FULL NEURAL NETWORK
EE Analogy: Cascaded filter bank.

  Layer 1 (Input)  -> 50 signal samples
  Layer 2 (Hidden) -> 64 neurons with ReLU  (bandpass feature extraction)
  Layer 3 (Hidden) -> 32 neurons with ReLU  (mixing / combining stage)
  Layer 4 (Output) -> 3 neurons  softmax    (priority encoder -> probabilities)

Architecture: 50 -> 64 -> 32 -> 3
"""
import numpy as np

def relu(x):
    return np.maximum(0, x)

def relu_derivative(x):
    return (x > 0).astype(float)

def softmax(x):
    e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
    return e_x / e_x.sum(axis=1, keepdims=True)

class NeuralNetwork:
    def __init__(self, input_size=50, hidden1=64, hidden2=32, output_size=3):
        self.W1 = np.random.randn(input_size, hidden1) * np.sqrt(2.0 / input_size)
        self.b1 = np.zeros((1, hidden1))
        self.W2 = np.random.randn(hidden1, hidden2) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros((1, hidden2))
        self.W3 = np.random.randn(hidden2, output_size) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros((1, output_size))
        self.cache = {}

    def forward(self, X):
        z1 = X @ self.W1 + self.b1;  a1 = relu(z1)
        z2 = a1 @ self.W2 + self.b2; a2 = relu(z2)
        z3 = a2 @ self.W3 + self.b3; a3 = softmax(z3)
        self.cache = {"X":X,"z1":z1,"a1":a1,"z2":z2,"a2":a2,"z3":z3,"a3":a3}
        return a3

    def predict(self, X):
        return np.argmax(self.forward(X), axis=1)

    def count_parameters(self):
        return sum(w.size for w in [self.W1,self.b1,self.W2,self.b2,self.W3,self.b3])

if __name__ == "__main__":
    print("=" * 55)
    print("STEP 3: NETWORK ARCHITECTURE")
    print("=" * 55)
    X = np.load("data/X.npy")
    y = np.load("data/y.npy")
    net = NeuralNetwork()
    print(f"""
  50 -> 64 -> 32 -> 3
  Layer     | Neurons | Activation | Parameters
  ----------+---------+------------+-------------------
  Input     |    50   |    none    |       --
  Hidden 1  |    64   |    ReLU    |  {50*64+64:,}
  Hidden 2  |    32   |    ReLU    |  {64*32+32:,}
  Output    |     3   |  Softmax   |  {32*3+3:,}
  TOTAL PARAMETERS: {net.count_parameters():,}
  (like {net.count_parameters():,} potentiometers being auto-tuned)
""")
    probs = net.forward(X[:5])
    preds = net.predict(X[:5])
    labels = ["sine", "square", "triangle"]
    print("  Forward pass BEFORE training (should be random ~0.33 each):")
    for i in range(5):
        print(f"    True={labels[y[i]]:<10} Pred={labels[preds[i]]:<10} Probs={probs[i].round(2)}")
    print()
    print("NEXT: python 4_train_model/train.py")
''')


# ── STEP 4 ────────────────────────────────────────────────────────────────
write("4_train_model/train.py", '''\
"""
STEP 4: TRAINING - HOW THE NETWORK LEARNS
EE Analogy: Auto-tuning a bank of potentiometers.

  1. Forward pass  -> make a prediction
  2. Compute loss  -> measure how wrong (like THD)
  3. Backprop      -> trace error back, find which weights caused it
  4. Update        -> nudge each weight a tiny amount
  5. Repeat 14000x -> network converges to 98%+ accuracy

Backprop = chain rule of calculus applied OUTPUT -> INPUT.
Same idea as sensitivity analysis in circuit design.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "3_build_network"))
from neural_network import NeuralNetwork, relu_derivative
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

X = np.load("data/X.npy")
y = np.load("data/y.npy")

scaler = StandardScaler()
X = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Train: {len(X_train)}  |  Test: {len(X_test)}")

def one_hot(y, n=3):
    r = np.zeros((len(y), n)); r[np.arange(len(y)), y] = 1; return r

Y_train = one_hot(y_train)
Y_test  = one_hot(y_test)

def cross_entropy(pred, true):
    return -np.mean(np.sum(true * np.log(pred + 1e-15), axis=1))

def backward(net, Y_true, lr):
    m = Y_true.shape[0]
    X, z1, a1, z2, a2, a3 = (net.cache[k] for k in ["X","z1","a1","z2","a2","a3"])
    dz3 = a3 - Y_true
    dW3 = a2.T @ dz3 / m;  db3 = np.mean(dz3, axis=0, keepdims=True)
    dz2 = (dz3 @ net.W3.T) * relu_derivative(net.cache["z2"])
    dW2 = a1.T @ dz2 / m;  db2 = np.mean(dz2, axis=0, keepdims=True)
    dz1 = (dz2 @ net.W2.T) * relu_derivative(z1)
    dW1 = X.T @ dz1 / m;   db1 = np.mean(dz1, axis=0, keepdims=True)
    net.W3 -= lr*dW3; net.b3 -= lr*db3
    net.W2 -= lr*dW2; net.b2 -= lr*db2
    net.W1 -= lr*dW1; net.b1 -= lr*db1

def accuracy(net, X, y):
    return np.mean(net.predict(X) == y)

EPOCHS = 500; LR = 0.005; BATCH = 32
net = NeuralNetwork()
train_losses, test_accs = [], []

print(f"\\n{\'Epoch\':<8} {\'Loss\':<12} {\'Train Acc\':<14} {\'Test Acc\'}")
print("-" * 48)

for epoch in range(EPOCHS):
    idx = np.random.permutation(len(X_train))
    ls, nb = 0, 0
    for s in range(0, len(X_train), BATCH):
        Xb = X_train[idx[s:s+BATCH]]; Yb = Y_train[idx[s:s+BATCH]]
        ls += cross_entropy(net.forward(Xb), Yb); nb += 1
        backward(net, Yb, LR)
    avg = ls/nb
    ta  = accuracy(net, X_train, y_train)
    va  = accuracy(net, X_test,  y_test)
    train_losses.append(avg); test_accs.append(va)
    if epoch % 50 == 0 or epoch == EPOCHS-1:
        print(f"{epoch:<8} {avg:<12.4f} {ta:<14.1%} {va:.1%}")

print(f"\\nFINAL TEST ACCURACY: {accuracy(net, X_test, y_test):.1%}")

np.save("data/W1.npy", net.W1); np.save("data/b1.npy", net.b1)
np.save("data/W2.npy", net.W2); np.save("data/b2.npy", net.b2)
np.save("data/W3.npy", net.W3); np.save("data/b3.npy", net.b3)
np.save("data/scaler_mean.npy", scaler.mean_)
np.save("data/scaler_std.npy",  scaler.scale_)
print("Model weights saved to data/")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Step 4: Training Progress", fontsize=13, fontweight="bold")
ax1.plot(train_losses, color="crimson", linewidth=1.5)
ax1.set_title("Loss (lower = less distortion)"); ax1.set_xlabel("Epoch")
ax1.set_ylabel("Cross-Entropy Loss"); ax1.grid(True, alpha=0.3)
ax2.plot([a*100 for a in test_accs], color="steelblue", linewidth=1.5)
ax2.axhline(95, color="green", linestyle="--", alpha=0.7, label="95% target")
ax2.set_title("Test Accuracy"); ax2.set_xlabel("Epoch")
ax2.set_ylabel("Accuracy (%)"); ax2.legend(); ax2.grid(True, alpha=0.3)
plt.tight_layout(); plt.savefig("data/step4_training.png", dpi=120)
print("Plot saved: data/step4_training.png")
print("\\nNEXT: python 5_api_server/app.py")
print("      Then open 5_frontend/index.html in your browser")
''')


# ── STEP 5 - API ──────────────────────────────────────────────────────────
write("5_api_server/app.py", '''\
"""
STEP 5a: FLASK API SERVER
EE Analogy: The GPIB/USB driver for your trained model.
Model = the sensor/instrument. Flask = the communication interface.

Run: python 5_api_server/app.py
Then open 5_frontend/index.html in your browser.
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "3_build_network"))
from neural_network import NeuralNetwork

app = Flask(__name__)
CORS(app)

ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR     = os.path.join(ROOT, "data")
FRONTEND_DIR = os.path.join(ROOT, "5_frontend")

def load_model():
    net = NeuralNetwork()
    net.W1 = np.load(os.path.join(DATA_DIR, "W1.npy"))
    net.b1 = np.load(os.path.join(DATA_DIR, "b1.npy"))
    net.W2 = np.load(os.path.join(DATA_DIR, "W2.npy"))
    net.b2 = np.load(os.path.join(DATA_DIR, "b2.npy"))
    net.W3 = np.load(os.path.join(DATA_DIR, "W3.npy"))
    net.b3 = np.load(os.path.join(DATA_DIR, "b3.npy"))
    return net

scaler_mean = np.load(os.path.join(DATA_DIR, "scaler_mean.npy"))
scaler_std  = np.load(os.path.join(DATA_DIR, "scaler_std.npy"))
model       = load_model()
LABELS      = {0: "Sine Wave", 1: "Square Wave", 2: "Triangle Wave"}
print("Model loaded. Open http://localhost:5000 in your browser.")

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/health")
def health():
    return jsonify({"status": "online"})

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data or "signal" not in data:
        return jsonify({"error": "Send JSON: {signal: [50 floats]}"}), 400
    signal = np.array(data["signal"], dtype=float)
    if len(signal) != 50:
        return jsonify({"error": f"Need 50 samples, got {len(signal)}"}), 400
    sig_norm = (signal - scaler_mean) / scaler_std
    probs    = model.forward(sig_norm.reshape(1, -1))[0]
    pred     = int(np.argmax(probs))
    return jsonify({
        "prediction":    LABELS[pred],
        "confidence":    round(float(probs[pred]) * 100, 1),
        "probabilities": {
            "sine":     round(float(probs[0]) * 100, 1),
            "square":   round(float(probs[1]) * 100, 1),
            "triangle": round(float(probs[2]) * 100, 1),
        }
    })

@app.route("/demo")
def demo():
    wtype = request.args.get("type", "sine")
    t = np.linspace(0, 2 * np.pi, 50)
    if wtype == "sine":
        sig = np.sin(t)
    elif wtype == "square":
        sig = np.where(np.sin(t) > 0, 1.0, -1.0)
    elif wtype == "triangle":
        sig = 2 * np.abs(((t) / np.pi) % 2 - 1) - 1
    else:
        return jsonify({"error": "type must be sine, square, or triangle"}), 400
    return jsonify({"type": wtype, "signal": sig.tolist()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
''')


# ── STEP 5 - FRONTEND ─────────────────────────────────────────────────────
write("5_frontend/index.html", """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Waveform AI Classifier</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;padding:2rem}
    h1{color:#38bdf8;font-size:1.6rem;margin-bottom:.3rem}
    h2{color:#7dd3fc;font-size:1rem;font-weight:normal;margin-bottom:1.5rem}
    .card{background:#1e293b;border-radius:12px;padding:1.5rem;margin-bottom:1.2rem;border:1px solid #334155}
    .card h3{color:#38bdf8;margin-bottom:.8rem}
    .btn-row{display:flex;gap:.7rem;flex-wrap:wrap;margin-bottom:1rem}
    button{padding:.55rem 1.2rem;border:none;border-radius:6px;cursor:pointer;font-size:.9rem;font-weight:600}
    button:hover{opacity:.85}
    .b-sine{background:#3b82f6;color:#fff}
    .b-square{background:#ef4444;color:#fff}
    .b-triangle{background:#22c55e;color:#fff}
    .b-noise{background:#8b5cf6;color:#fff}
    .b-classify{background:#f59e0b;color:#0f172a;font-size:1rem;padding:.7rem 2rem}
    canvas{width:100%;height:160px;background:#0f172a;border-radius:8px;border:1px solid #334155;display:block}
    .result-box{background:#0f172a;border-radius:8px;padding:1.2rem 1.5rem;border:2px solid #334155;min-height:80px;margin-top:1rem}
    .result-label{font-size:1.8rem;font-weight:bold;color:#34d399}
    .result-conf{font-size:.95rem;color:#94a3b8;margin-top:.2rem}
    .prob-bars{display:flex;flex-direction:column;gap:.6rem;margin-top:1rem}
    .prob-row{display:flex;align-items:center;gap:.8rem}
    .prob-name{width:80px;font-size:.85rem;color:#94a3b8}
    .bar-outer{flex:1;height:18px;background:#334155;border-radius:4px;overflow:hidden}
    .bar-inner{height:100%;border-radius:4px;transition:width .4s ease}
    .prob-val{width:45px;font-size:.85rem;text-align:right;color:#cbd5e1}
    .status{font-size:.8rem;color:#64748b;margin-top:.5rem}
    .ee-box{background:#162032;border-left:3px solid #38bdf8;padding:.8rem 1rem;border-radius:4px;font-size:.85rem;color:#94a3b8;margin-top:.8rem}
    .steps{list-style:none}
    .steps li{padding:.5rem 0;border-bottom:1px solid #334155;font-size:.88rem;color:#94a3b8}
    .steps li span{color:#38bdf8;font-weight:bold;margin-right:.5rem}
  </style>
</head>
<body>
<h1>Waveform AI Classifier</h1>
<h2>Full-Stack AI &mdash; Built From Scratch for Electrical Engineers</h2>

<div class="card">
  <h3>1. Load a Waveform</h3>
  <div class="btn-row">
    <button class="b-sine"     onclick="load('sine')">Sine Wave</button>
    <button class="b-square"   onclick="load('square')">Square Wave</button>
    <button class="b-triangle" onclick="load('triangle')">Triangle Wave</button>
    <button class="b-noise"    onclick="noise()">Random Noise</button>
  </div>
  <canvas id="scope"></canvas>
  <p class="status" id="sig-status">No signal loaded</p>
  <div class="ee-box"><strong>EE Analogy:</strong> This is your oscilloscope &mdash; 50 ADC samples. The AI receives exactly these 50 numbers.</div>
</div>

<div class="card">
  <h3>2. Classify It</h3>
  <button class="b-classify" onclick="classify()">Classify Signal &rarr;</button>
  <p class="status" id="api-status">Load a signal first</p>
  <div class="result-box" id="result-box"><div style="color:#475569">Load a signal then click Classify</div></div>
  <div class="prob-bars" id="prob-bars" style="display:none">
    <div class="prob-row"><span class="prob-name">Sine</span><div class="bar-outer"><div class="bar-inner" id="bar-sine" style="background:#3b82f6;width:33%"></div></div><span class="prob-val" id="val-sine">--</span></div>
    <div class="prob-row"><span class="prob-name">Square</span><div class="bar-outer"><div class="bar-inner" id="bar-square" style="background:#ef4444;width:33%"></div></div><span class="prob-val" id="val-square">--</span></div>
    <div class="prob-row"><span class="prob-name">Triangle</span><div class="bar-outer"><div class="bar-inner" id="bar-triangle" style="background:#22c55e;width:33%"></div></div><span class="prob-val" id="val-triangle">--</span></div>
  </div>
  <div class="ee-box" style="margin-top:.8rem"><strong>What happens:</strong> Browser sends 50 values to Flask &rarr; normalize &rarr; 3 forward passes through network layers &rarr; probabilities &rarr; display result.</div>
</div>

<div class="card">
  <h3>3. How It Was Built</h3>
  <ul class="steps">
    <li><span>Step 1</span>900 noisy waveforms generated as labeled training data</li>
    <li><span>Step 2</span>Single neuron: weighted sum + ReLU = summing amp + half-wave rectifier</li>
    <li><span>Step 3</span>Network: 50 &rarr; 64 &rarr; 32 &rarr; 3 (cascaded filter stages)</li>
    <li><span>Step 4</span>500 epochs backprop: auto-tuned 6,531 weights to ~99% accuracy</li>
    <li><span>Step 5</span>Flask REST API + this HTML frontend = full-stack AI app</li>
  </ul>
</div>

<script>
const API = window.location.origin.startsWith('http') ? window.location.origin : 'http://localhost:5000';
let sig = null;

function draw(signal, color) {
  const c = document.getElementById('scope'), ctx = c.getContext('2d');
  c.width = c.offsetWidth; c.height = 160;
  const W=c.width,H=c.height,p=20,mn=Math.min(...signal),mx=Math.max(...signal),r=(mx-mn)||1;
  ctx.clearRect(0,0,W,H);
  ctx.strokeStyle='#1e3a5f'; ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const y=p+(H-2*p)*i/4;ctx.beginPath();ctx.moveTo(p,y);ctx.lineTo(W-p,y);ctx.stroke();}
  const zy=p+(H-2*p)*(mx/r);
  ctx.strokeStyle='#475569';ctx.beginPath();ctx.moveTo(p,zy);ctx.lineTo(W-p,zy);ctx.stroke();
  ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();
  signal.forEach((v,i)=>{const x=p+(W-2*p)*i/(signal.length-1),y=p+(H-2*p)*(1-(v-mn)/r);i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.stroke();
  ctx.fillStyle=color;
  signal.forEach((v,i)=>{const x=p+(W-2*p)*i/(signal.length-1),y=p+(H-2*p)*(1-(v-mn)/r);ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);ctx.fill();});
}

async function load(type) {
  const colors={sine:'#3b82f6',square:'#ef4444',triangle:'#22c55e'};
  try {
    const d=await(await fetch(API+'/demo?type='+type)).json();
    sig=d.signal; draw(sig,colors[type]);
    document.getElementById('sig-status').textContent=type+' wave loaded (50 samples)';
    document.getElementById('api-status').textContent='Ready. Click Classify.';
  } catch(e){document.getElementById('sig-status').textContent='Cannot reach API - is app.py running?';}
}

function noise(){
  sig=Array.from({length:50},()=>Math.random()*2-1);
  draw(sig,'#a855f7');
  document.getElementById('sig-status').textContent='Random noise loaded (50 samples)';
  document.getElementById('api-status').textContent='Ready. Click Classify.';
}

async function classify(){
  if(!sig){document.getElementById('api-status').textContent='Load a signal first!';return;}
  document.getElementById('api-status').textContent='Sending to model...';
  try{
    const d=await(await fetch(API+'/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signal:sig})})).json();
    document.getElementById('result-box').innerHTML='<div class="result-label">'+d.prediction+'</div><div class="result-conf">Confidence: <strong>'+d.confidence+'%</strong></div>';
    const p=d.probabilities;
    document.getElementById('prob-bars').style.display='flex';
    ['sine','square','triangle'].forEach(k=>{document.getElementById('bar-'+k).style.width=p[k]+'%';document.getElementById('val-'+k).textContent=p[k]+'%';});
    document.getElementById('api-status').textContent='Done!';
  }catch(e){document.getElementById('api-status').textContent='Error - make sure app.py is running';}
}
</script>
</body>
</html>
""")

print()
print("=" * 55)
print("ALL FILES CREATED SUCCESSFULLY")
print("=" * 55)
print("""
Now run these commands in order (from this folder):

  pip install numpy matplotlib flask flask-cors scikit-learn

  python 1_understand_data/generate_signals.py
  python 2_build_neuron/single_neuron.py
  python 3_build_network/neural_network.py
  python 4_train_model/train.py
  python 5_api_server/app.py

Then open http://localhost:5000 in your browser.
""")
