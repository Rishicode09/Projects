"""
STEP 1: UNDERSTANDING DATA
EE Analogy: Before you design a filter, you need to understand
the signal you're working with. Same with AI — data comes first.

We're going to generate 3 types of waveforms:
  - Sine wave   → label 0
  - Square wave → label 1
  - Triangle    → label 2

Each waveform is sampled at 50 points (like a 50-sample ADC reading).
That gives us 50 numbers per signal = 50 "features" our AI will learn from.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # no display needed, saves to file
import matplotlib.pyplot as plt
import os

# ─────────────────────────────────────────────
# WHAT IS A "SAMPLE"?
# ─────────────────────────────────────────────
# Think of your oscilloscope. It captures voltage at discrete time points.
# Each captured value is one "sample". 50 samples = one row of data for the AI.

NUM_SAMPLES = 50       # how many time-steps we sample per waveform
NUM_WAVEFORMS = 300    # 300 examples of each type (300 sine, 300 square, 300 tri)
NOISE_LEVEL = 0.1      # add a little noise (like real-world signal noise)

t = np.linspace(0, 2 * np.pi, NUM_SAMPLES)  # time axis: 0 to 2π


def generate_sine(n):
    """Pure sine wave with random phase and small noise."""
    signals = []
    for _ in range(n):
        phase = np.random.uniform(0, np.pi)         # random phase shift
        amplitude = np.random.uniform(0.8, 1.2)     # slight amplitude variation
        signal = amplitude * np.sin(t + phase)
        signal += np.random.normal(0, NOISE_LEVEL, NUM_SAMPLES)  # add noise
        signals.append(signal)
    return np.array(signals)


def generate_square(n):
    """Square wave (like a PWM signal) with random duty cycle."""
    signals = []
    for _ in range(n):
        duty = np.random.uniform(0.3, 0.7)          # random duty cycle (30-70%)
        signal = np.where(np.sin(t) > np.cos(duty), 1.0, -1.0)
        signal += np.random.normal(0, NOISE_LEVEL, NUM_SAMPLES)
        signals.append(signal)
    return np.array(signals)


def generate_triangle(n):
    """Triangle wave (like a sawtooth used in PWM generation)."""
    signals = []
    for _ in range(n):
        phase = np.random.uniform(0, np.pi)
        signal = 2 * np.abs(((t + phase) / np.pi) % 2 - 1) - 1
        signal += np.random.normal(0, NOISE_LEVEL, NUM_SAMPLES)
        signals.append(signal)
    return np.array(signals)


# ─────────────────────────────────────────────
# BUILD THE DATASET
# ─────────────────────────────────────────────
# X = the actual signal values (inputs to our AI)
# y = the label / answer (0=sine, 1=square, 2=triangle)

X_sine     = generate_sine(NUM_WAVEFORMS)
X_square   = generate_square(NUM_WAVEFORMS)
X_triangle = generate_triangle(NUM_WAVEFORMS)

X = np.vstack([X_sine, X_square, X_triangle])   # stack all signals: shape (900, 50)
y = np.array([0]*NUM_WAVEFORMS + [1]*NUM_WAVEFORMS + [2]*NUM_WAVEFORMS)  # labels: (900,)

print("=" * 55)
print("DATASET CREATED")
print("=" * 55)
print(f"  Total waveforms  : {len(X)}")
print(f"  Samples per wave : {NUM_SAMPLES}")
print(f"  X shape          : {X.shape}  ← (rows=waveforms, cols=samples)")
print(f"  y shape          : {y.shape}  ← one label per waveform")
print(f"  Labels           : 0=sine, 1=square, 2=triangle")
print()
print("EE ANALOGY:")
print("  X = your oscilloscope readings (50 voltage samples per waveform)")
print("  y = what waveform type it is (the 'answer' we want AI to predict)")

# Save dataset for later steps
os.makedirs("data", exist_ok=True)
np.save("data/X.npy", X)
np.save("data/y.npy", y)
print()
print("  Saved to data/X.npy and data/y.npy")

# ─────────────────────────────────────────────
# VISUALIZE — like looking at your oscilloscope
# ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
fig.suptitle("Step 1: Your Training Data (AI sees thousands of these)", fontsize=13, fontweight='bold')

for i, (signal, name, color) in enumerate(zip(
    [X_sine[0], X_square[0], X_triangle[0]],
    ['Sine Wave (label=0)', 'Square Wave (label=1)', 'Triangle Wave (label=2)'],
    ['blue', 'red', 'green']
)):
    axes[i].plot(signal, color=color, linewidth=2)
    axes[i].set_title(name, fontsize=11)
    axes[i].set_xlabel("Sample # (time)")
    axes[i].set_ylabel("Amplitude (voltage)")
    axes[i].axhline(0, color='gray', linestyle='--', linewidth=0.8)
    axes[i].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("data/step1_signals.png", dpi=120)
print("  Plot saved to data/step1_signals.png")
print()
print("NEXT: Run  python 2_build_neuron/single_neuron.py")

import numpy as np, matplotlib, os
matplotlib.use("Agg")
import matplotlib.pyplot as plt
NUM_SAMPLES=50; NUM_WAVEFORMS=300; NOISE=0.1
t = np.linspace(0, 2*np.pi, NUM_SAMPLES)
def gen_sine(n):
    return np.array([np.random.uniform(0.8,1.2)*np.sin(t+np.random.uniform(0,np.pi))+np.random.normal(0,NOISE,NUM_SAMPLES) for _ in range(n)])
def gen_square(n):
    return np.array([np.where(np.sin(t)>np.cos(np.random.uniform(0.3,0.7)),1.0,-1.0)+np.random.normal(0,NOISE,NUM_SAMPLES) for _ in range(n)])
def gen_triangle(n):
    return np.array([2*np.abs(((t+np.random.uniform(0,np.pi))/np.pi)%2-1)-1+np.random.normal(0,NOISE,NUM_SAMPLES) for _ in range(n)])
Xs=gen_sine(NUM_WAVEFORMS); Xq=gen_square(NUM_WAVEFORMS); Xt=gen_triangle(NUM_WAVEFORMS)
X=np.vstack([Xs,Xq,Xt]); y=np.array([0]*NUM_WAVEFORMS+[1]*NUM_WAVEFORMS+[2]*NUM_WAVEFORMS)
os.makedirs("data",exist_ok=True); np.save("data/X.npy",X); np.save("data/y.npy",y)
print(f"Dataset: {X.shape} saved. Labels: 0=sine 1=square 2=triangle")
fig,ax=plt.subplots(1,3,figsize=(14,4))
for i,(s,n,c) in enumerate(zip([Xs[0],Xq[0],Xt[0]],["Sine","Square","Triangle"],["blue","red","green"])):
    ax[i].plot(s,color=c,linewidth=2); ax[i].set_title(n); ax[i].grid(True,alpha=0.3)
plt.tight_layout(); plt.savefig("data/step1_signals.png",dpi=120)
print("Plot: data/step1_signals.png")
print("NEXT: python 2_build_neuron/single_neuron.py")
