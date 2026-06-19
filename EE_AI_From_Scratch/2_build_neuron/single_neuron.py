EE Analogy: A neuron is like a WEIGHTED SUMMER + COMPARATOR circuit.

    x1 ──[w1]──┐
    x2 ──[w2]──┤──[ Σ ]──[ + bias ]──[ activation ]──→ output
    x3 ──[w3]──┘

  - Inputs (x)      = voltage samples from your signal
  - Weights (w)     = the resistor values in your summing amplifier
  - Bias (b)        = a DC offset (like a voltage reference)
  - Activation      = like a comparator — squishes the output into a useful range
  - Output          = a single number (the neuron's "opinion")

The neuron computes:   output = activation( w·x + b )

That dot product  w·x  is EXACTLY what a resistor summing network does.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────
# ACTIVATION FUNCTIONS
# ─────────────────────────────────────────────
# These squish the output of the weighted sum into a useful range.
# EE Analogy: like a diode clamp or a sigmoid transfer curve on a transistor.

def sigmoid(x):
    """Squishes any number into range (0, 1). Like a transistor saturation curve."""
    return 1 / (1 + np.exp(-x))

def relu(x):
    """ReLU = Rectified Linear Unit. Passes positive values, blocks negative ones.
    EE Analogy: this IS a half-wave rectifier. Literally the same thing."""
    return np.maximum(0, x)

def tanh_activation(x):
    """Squishes into (-1, 1). Balanced, like a bipolar signal."""
    return np.tanh(x)


# ─────────────────────────────────────────────
# BUILD ONE NEURON
# ─────────────────────────────────────────────

class Neuron:
    """
    A single artificial neuron.
    Think of it as: one op-amp stage with weighted inputs.
    """

    def __init__(self, num_inputs):
        # Weights are randomly initialized — like random component tolerances.
        # The TRAINING process will tune these (like trimming a potentiometer).
        self.weights = np.random.randn(num_inputs) * 0.01  # small random values
        self.bias    = 0.0                                   # start at zero DC offset

    def forward(self, x):
        """
        Forward pass: compute output from inputs.
        This is the 'signal flowing through the circuit'.

        Step 1: Weighted sum  →  z = w·x + b
                                   (like a summing amplifier output)
        Step 2: Activation   →  output = sigmoid(z)
                                   (like passing through a comparator)
        """
        z = np.dot(self.weights, x) + self.bias   # weighted sum
        output = sigmoid(z)                         # activation
        return output, z


# ─────────────────────────────────────────────
# DEMO: Feed one signal sample through a neuron
# ─────────────────────────────────────────────

print("=" * 55)
print("STEP 2: SINGLE NEURON DEMO")
print("=" * 55)

# Load our signal data from Step 1
X = np.load("data/X.npy")
one_signal = X[0]  # take the first sine wave

NUM_INPUTS = len(one_signal)  # 50 inputs (one per sample)
neuron = Neuron(NUM_INPUTS)

output, z = neuron.forward(one_signal)

print(f"\nInput signal   : {NUM_INPUTS} voltage samples")
print(f"Weighted sum z : {z:.4f}   ← like an op-amp output before clipping")
print(f"After sigmoid  : {output:.4f}  ← squished into 0-1 range")
print()
print("Right now the output is RANDOM because weights are random.")
print("Training (Step 4) tunes the weights so the output becomes meaningful.")

# ─────────────────────────────────────────────
# VISUALIZE ACTIVATION FUNCTIONS
# ─────────────────────────────────────────────
x_range = np.linspace(-6, 6, 200)

fig, axes = plt.subplots(1, 3, figsize=(14, 4))
fig.suptitle("Step 2: Activation Functions (your neuron's transfer curves)", fontsize=13, fontweight='bold')

for ax, (name, fn, color, analogy) in zip(axes, [
    ("Sigmoid", sigmoid, "blue", "EE: transistor saturation curve\nRange: (0, 1)"),
    ("ReLU",    relu,    "red",  "EE: half-wave rectifier\nRange: (0, ∞)"),
    ("Tanh",    tanh_activation, "green", "EE: bipolar transfer curve\nRange: (-1, 1)"),
]):
    ax.plot(x_range, fn(x_range), color=color, linewidth=2.5)
    ax.set_title(f"{name}\n{analogy}", fontsize=10)
    ax.set_xlabel("Input (weighted sum z)")
    ax.set_ylabel("Output")
    ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.axvline(0, color='gray', linestyle='--', linewidth=0.8)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("data/step2_activations.png", dpi=120)
print("\n  Plot saved to data/step2_activations.png")
print()
print("KEY INSIGHT:")
print("  One neuron can only make ONE simple decision (like one comparator).")
print("  We need MANY neurons stacked in layers to solve complex problems.")
print()
print("NEXT: Run  python 3_build_network/neural_network.py")

import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
def sigmoid(x): return 1/(1+np.exp(-x))
def relu(x): return np.maximum(0,x)
def tanh_fn(x): return np.tanh(x)
class Neuron:
    def __init__(self,n): self.w=np.random.randn(n)*0.01; self.b=0.0
    def forward(self,x): z=np.dot(self.w,x)+self.b; return sigmoid(z),z
X=np.load("data/X.npy"); n=Neuron(len(X[0])); out,z=n.forward(X[0])
print(f"Weighted sum: {z:.4f}  After sigmoid: {out:.4f}")
print("Random now - training will make this meaningful.")
xr=np.linspace(-6,6,200); fig,axes=plt.subplots(1,3,figsize=(14,4))
for ax,(nm,fn,c) in zip(axes,[("Sigmoid",sigmoid,"blue"),("ReLU",relu,"red"),("Tanh",tanh_fn,"green")]):
    ax.plot(xr,fn(xr),color=c,linewidth=2.5); ax.set_title(nm); ax.grid(True,alpha=0.3)
plt.tight_layout(); plt.savefig("data/step2_activations.png",dpi=120)
print("Plot: data/step2_activations.png")
print("NEXT: python 3_build_network/neural_network.py")
