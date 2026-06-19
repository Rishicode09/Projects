"""
STEP 3: THE FULL NEURAL NETWORK
================================
EE Analogy: A neural network is a CASCADED FILTER BANK.

  Layer 1 (Input Layer)  → raw signal samples (50 values)
  Layer 2 (Hidden Layer) → extracts features (like bandpass filters finding harmonics)
  Layer 3 (Hidden Layer) → combines features (like a mixing stage)
  Layer 4 (Output Layer) → makes the final classification (like a comparator bank)

Architecture of our network:
  50 inputs → 64 neurons → 32 neurons → 3 outputs

The 3 outputs represent:  [P(sine), P(square), P(triangle)]
The AI picks the highest probability as its prediction.

This is called a "Multi-Layer Perceptron" (MLP) — the simplest kind of
real neural network. Built entirely from scratch using only NumPy.
"""

import numpy as np
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────
# ACTIVATION FUNCTIONS (with derivatives for training)
# ─────────────────────────────────────────────

def relu(x):
    return np.maximum(0, x)

def relu_derivative(x):
    """Gradient of ReLU. 1 where x>0, 0 where x≤0."""
    return (x > 0).astype(float)

def softmax(x):
    """
    Converts raw output scores into probabilities (must sum to 1).
    EE Analogy: like a priority encoder — outputs which signal is strongest.
    """
    e_x = np.exp(x - np.max(x, axis=1, keepdims=True))  # subtract max for stability
    return e_x / e_x.sum(axis=1, keepdims=True)


# ─────────────────────────────────────────────
# THE NEURAL NETWORK CLASS
# ─────────────────────────────────────────────

class NeuralNetwork:
    """
    A 3-layer neural network built from scratch.

    Architecture: 50 → 64 → 32 → 3

    EE Circuit Diagram:
    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
    │  50 inputs  │───►│  64 neurons  │───►│  32 neurons  │───►│ 3 output │
    │ (raw signal)│    │ (ReLU layer) │    │ (ReLU layer) │    │(softmax) │
    └─────────────┘    └──────────────┘    └──────────────┘    └──────────┘
         Layer 0            Layer 1              Layer 2           Layer 3
    """

    def __init__(self, input_size=50, hidden1=64, hidden2=32, output_size=3):
        self.input_size  = input_size
        self.hidden1     = hidden1
        self.hidden2     = hidden2
        self.output_size = output_size

        # ── WEIGHTS & BIASES ──────────────────────────────────────────────
        # W1: connects input layer (50) to hidden layer 1 (64)
        #     Shape: (50, 64) — 50×64 = 3200 adjustable weights
        # EE: like a 50×64 resistor matrix (crosspoint switch)
        self.W1 = np.random.randn(input_size, hidden1) * np.sqrt(2.0 / input_size)
        self.b1 = np.zeros((1, hidden1))

        # W2: connects hidden layer 1 (64) to hidden layer 2 (32)
        self.W2 = np.random.randn(hidden1, hidden2) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros((1, hidden2))

        # W3: connects hidden layer 2 (32) to output layer (3)
        self.W3 = np.random.randn(hidden2, output_size) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros((1, output_size))

        # Storage for intermediate values (needed during training)
        self.cache = {}

    def forward(self, X):
        """
        FORWARD PASS — signal flows INPUT → OUTPUT.
        EE: like measuring the output of each cascaded stage.

        For each layer:  output = activation( input @ weights + bias )
        '@' is matrix multiplication — like a full summing network.
        """
        # Layer 1: Input → Hidden1
        z1 = X @ self.W1 + self.b1          # weighted sum: (N,50)@(50,64) = (N,64)
        a1 = relu(z1)                         # activation: ReLU

        # Layer 2: Hidden1 → Hidden2
        z2 = a1 @ self.W2 + self.b2          # (N,64)@(64,32) = (N,32)
        a2 = relu(z2)

        # Layer 3: Hidden2 → Output (no ReLU here — softmax handles it)
        z3 = a2 @ self.W3 + self.b3          # (N,32)@(32,3) = (N,3)
        a3 = softmax(z3)                      # probabilities: [P(sine), P(sq), P(tri)]

        # Cache everything — we need these values during backpropagation
        self.cache = {'X': X, 'z1': z1, 'a1': a1, 'z2': z2, 'a2': a2, 'z3': z3, 'a3': a3}

        return a3  # final predictions

    def predict(self, X):
        """Run forward pass and return class labels (0, 1, or 2)."""
        probs = self.forward(X)
        return np.argmax(probs, axis=1)  # pick highest probability

    def count_parameters(self):
        total = (self.W1.size + self.b1.size +
                 self.W2.size + self.b2.size +
                 self.W3.size + self.b3.size)
        return total


# ─────────────────────────────────────────────
# DEMO: Show what the network looks like
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("STEP 3: NEURAL NETWORK ARCHITECTURE")
    print("=" * 55)

    X = np.load("data/X.npy")
    y = np.load("data/y.npy")

    net = NeuralNetwork()

    print(f"""
Network Layout (50 → 64 → 32 → 3):
─────────────────────────────────────────────────────
  Layer        | Size | Activation | Weights+Biases
  ─────────────┼──────┼────────────┼───────────────
  Input        |  50  |    none    |       —
  Hidden 1     |  64  |    ReLU    |  50×64 + 64 = {50*64+64:,}
  Hidden 2     |  32  |    ReLU    |  64×32 + 32 = {64*32+32:,}
  Output       |   3  |  Softmax   |  32×3  +  3 = {32*3+3:,}
  ─────────────┴──────┴────────────┴───────────────
  TOTAL PARAMETERS: {net.count_parameters():,}
  (like {net.count_parameters():,} tiny potentiometers being tuned)
─────────────────────────────────────────────────────
""")

    # Run a forward pass on 5 examples
    sample = X[:5]
    probs = net.forward(sample)
    preds = net.predict(sample)

    print("Forward pass on 5 random waveforms (BEFORE training):")
    print(f"  {'True Label':<12} {'P(sine)':<10} {'P(square)':<12} {'P(triangle)':<12} {'Predicted'}")
    print(f"  {'-'*60}")
    labels = ['sine', 'square', 'triangle']
    for i in range(5):
        true = labels[y[i]]
        pred = labels[preds[i]]
        print(f"  {true:<12} {probs[i,0]:.4f}     {probs[i,1]:.4f}       {probs[i,2]:.4f}       {pred}")

    print()
    print("  All probabilities are close to 0.33 — network is guessing randomly.")
    print("  Training will fix this.")
    print()
    print("NEXT: Run  python 4_train_model/train.py")
