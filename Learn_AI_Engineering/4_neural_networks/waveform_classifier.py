"""
MODULE 4: FIXED NEURAL NETWORK — WAVEFORM CLASSIFIER
======================================================
This is the FIXED version of the EE_AI_From_Scratch classifier.

WHAT WAS BROKEN:
  1. Square wave generation used np.sin-based threshold → sometimes
     looked like a sine wave near the threshold → model confused them.
  2. Random noise was classified as triangle because the model never
     saw noise in training — it had to pick SOMETHING.
  3. Network was too small (64,32) and undertrained (500 epochs).

WHAT WE FIXED:
  1. Square waves now use np.sign(np.sin(t)) — hard ±1 transitions,
     never ambiguous. Like a digital logic square wave, not analog.
  2. Added NOISE as a 4th class — model now knows what noise looks like.
  3. Bigger network (128, 64) trained for 1000 epochs.
  4. More training data: 500 per class instead of 300.

EE Analogy of the fix:
  Old: your comparator threshold was in the middle of the sine wave,
       so a slow-rising sine sometimes triggered like a square.
  New: we use a Schmidt trigger (hysteresis) — clean snap to ±1,
       no ambiguity around the threshold.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from network import NeuralNetwork, relu_grad, softmax

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, classification_report

os.makedirs("data", exist_ok=True)
np.random.seed(42)

NUM_SAMPLES   = 50     # ADC samples per waveform
NUM_PER_CLASS = 500    # training examples per class (was 300)
t = np.linspace(0, 2 * np.pi, NUM_SAMPLES)


# ─────────────────────────────────────────────────────────────
# DATA GENERATION (FIXED)
# ─────────────────────────────────────────────────────────────

def gen_sine(n):
    out = []
    for _ in range(n):
        phase = np.random.uniform(0, 2*np.pi)
        amp   = np.random.uniform(0.8, 1.2)
        s     = amp * np.sin(t + phase)
        s    += np.random.normal(0, 0.05, NUM_SAMPLES)   # low noise
        out.append(s)
    return np.array(out)

def gen_square(n):
    """
    FIX: use np.sign(np.sin(t)) for crisp ±1 transitions.
    Old code used np.where(np.sin(t) > np.cos(duty)) which created
    smooth transitions that overlapped with sine wave shape.
    """
    out = []
    for _ in range(n):
        phase = np.random.uniform(0, 2*np.pi)
        amp   = np.random.uniform(0.8, 1.2)
        s     = amp * np.sign(np.sin(t + phase))    # HARD ±1, never ambiguous
        s    += np.random.normal(0, 0.05, NUM_SAMPLES)
        out.append(s)
    return np.array(out)

def gen_triangle(n):
    out = []
    for _ in range(n):
        phase = np.random.uniform(0, 2*np.pi)
        amp   = np.random.uniform(0.8, 1.2)
        s     = amp * (2 * np.abs(((t + phase) / np.pi) % 2 - 1) - 1)
        s    += np.random.normal(0, 0.05, NUM_SAMPLES)
        out.append(s)
    return np.array(out)

def gen_noise(n):
    """
    FIX: add noise as an explicit 4th class so the model learns
    that random noise is NOT a waveform — it stops forcing it
    to pick sine/square/triangle when the input is garbage.
    """
    out = []
    for _ in range(n):
        # pure random noise at different amplitudes
        amp = np.random.uniform(0.3, 1.5)
        s   = amp * np.random.randn(NUM_SAMPLES)
        out.append(s)
    return np.array(out)


print("=" * 60)
print("MODULE 4: FIXED WAVEFORM CLASSIFIER")
print("=" * 60)
print("\nGenerating training data...")

X_s = gen_sine(NUM_PER_CLASS)
X_q = gen_square(NUM_PER_CLASS)
X_t = gen_triangle(NUM_PER_CLASS)
X_n = gen_noise(NUM_PER_CLASS)

X = np.vstack([X_s, X_q, X_t, X_n])
y = np.array(
    [0]*NUM_PER_CLASS + [1]*NUM_PER_CLASS +
    [2]*NUM_PER_CLASS + [3]*NUM_PER_CLASS
)
LABELS = {0: "Sine", 1: "Square", 2: "Triangle", 3: "Noise"}

print(f"  Total samples: {len(X)} ({NUM_PER_CLASS} each: sine, square, triangle, noise)")
print(f"  Shape: {X.shape}")

# Normalize
scaler = StandardScaler()
X_norm = scaler.fit_transform(X)

# Split
X_tr, X_te, y_tr, y_te = train_test_split(
    X_norm, y, test_size=0.2, random_state=42, stratify=y
)

# One-hot encode
def one_hot(y, c=4):
    oh = np.zeros((len(y), c))
    oh[np.arange(len(y)), y] = 1
    return oh

Y_tr = one_hot(y_tr)
Y_te = one_hot(y_te)

# ─────────────────────────────────────────────────────────────
# BACKPROPAGATION
# ─────────────────────────────────────────────────────────────

def backward(net, Y_true, lr):
    m = Y_true.shape[0]
    c = net.cache
    dz3 = c["a3"] - Y_true
    dW3 = c["a2"].T @ dz3 / m
    db3 = np.mean(dz3, axis=0, keepdims=True)
    da2 = dz3 @ net.W3.T
    dz2 = da2 * relu_grad(c["z2"])
    dW2 = c["a1"].T @ dz2 / m
    db2 = np.mean(dz2, axis=0, keepdims=True)
    da1 = dz2 @ net.W2.T
    dz1 = da1 * relu_grad(c["z1"])
    dW1 = c["X"].T @ dz1 / m
    db1 = np.mean(dz1, axis=0, keepdims=True)
    net.W3 -= lr*dW3; net.b3 -= lr*db3
    net.W2 -= lr*dW2; net.b2 -= lr*db2
    net.W1 -= lr*dW1; net.b1 -= lr*db1

def cross_entropy(pred, true):
    return -np.mean(np.sum(true * np.log(pred + 1e-15), axis=1))

def accuracy(net, X, y):
    return np.mean(net.predict(X) == y)

# ─────────────────────────────────────────────────────────────
# TRAINING
# ─────────────────────────────────────────────────────────────
EPOCHS = 1000
LR     = 0.003
BATCH  = 64

net = NeuralNetwork(input_size=50, hidden1=128, hidden2=64, output_size=4)
print(f"\nNetwork: 50→128→64→4  ({net.param_count():,} parameters)")
print(f"Training {EPOCHS} epochs...")
print(f"\n{'Epoch':<8} {'Loss':<12} {'TrainAcc':<12} {'TestAcc'}")
print("-" * 45)

losses, test_accs = [], []

for epoch in range(EPOCHS):
    idx = np.random.permutation(len(X_tr))
    ep_loss, nb = 0, 0
    for s in range(0, len(X_tr), BATCH):
        bi = idx[s:s+BATCH]
        p  = net.forward(X_tr[bi])
        ep_loss += cross_entropy(p, Y_tr[bi])
        nb += 1
        backward(net, Y_tr[bi], LR)
    loss = ep_loss / nb
    tacc = accuracy(net, X_tr, y_tr)
    vacc = accuracy(net, X_te, y_te)
    losses.append(loss)
    test_accs.append(vacc)
    if epoch % 100 == 0 or epoch == EPOCHS-1:
        print(f"{epoch:<8} {loss:<12.4f} {tacc:<12.1%} {vacc:.1%}")

final_acc = accuracy(net, X_te, y_te)
print(f"\nFinal test accuracy: {final_acc:.1%}")

# ─────────────────────────────────────────────────────────────
# CONFUSION MATRIX
# ─────────────────────────────────────────────────────────────
label_names = ["Sine", "Square", "Triangle", "Noise"]
y_pred = net.predict(X_te)
cm = confusion_matrix(y_te, y_pred)
print("\nConfusion Matrix (rows=actual, cols=predicted):")
print(f"{'':12}", end="")
for l in label_names:
    print(f"  {l:>9}", end="")
print()
for i, rl in enumerate(label_names):
    print(f"  {rl:<10}", end="")
    for j, v in enumerate(cm[i]):
        marker = " ✓" if i == j else "  "
        print(f"  {v:>7}{marker[0]}", end="")
    print()
print()
print(classification_report(y_te, y_pred, target_names=label_names))

# ─────────────────────────────────────────────────────────────
# SAVE WEIGHTS
# ─────────────────────────────────────────────────────────────
for name in ["W1","b1","W2","b2","W3","b3"]:
    np.save(f"data/{name}.npy", getattr(net, name))
np.save("data/scaler_mean.npy", scaler.mean_)
np.save("data/scaler_std.npy",  scaler.scale_)
print("Weights saved to data/")

# ─────────────────────────────────────────────────────────────
# VISUALIZE: sample waveforms from each class
# ─────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 4, figsize=(16, 7))
fig.suptitle("Module 4: Fixed Waveform Classifier\n"
             "Top row: sample waveforms. Bottom row: training curves.", fontsize=13)

wave_data = [X_s[0], X_q[0], X_t[0], X_n[0]]
colors     = ["#3b82f6", "#ef4444", "#22c55e", "#a855f7"]
titles     = ["Sine (class 0)", "Square (class 1)", "Triangle (class 2)", "Noise (class 3)"]

for i, (wave, color, title) in enumerate(zip(wave_data, colors, titles)):
    axes[0, i].plot(wave, color=color, linewidth=2)
    axes[0, i].set_title(title, fontsize=10)
    axes[0, i].set_xlabel("Sample #")
    axes[0, i].axhline(0, color="gray", linestyle="--", linewidth=0.5)
    axes[0, i].grid(True, alpha=0.3)
    axes[0, i].set_ylim(-2, 2)

# Training curves
axes[1, 0].plot(losses, color="crimson", linewidth=1.5)
axes[1, 0].set_title("Loss Curve")
axes[1, 0].set_xlabel("Epoch")
axes[1, 0].set_ylabel("Cross-Entropy Loss")
axes[1, 0].grid(True, alpha=0.3)

axes[1, 1].plot([a*100 for a in test_accs], color="steelblue", linewidth=1.5)
axes[1, 1].axhline(95, color="green", linestyle="--", alpha=0.7, label="95% target")
axes[1, 1].set_title("Test Accuracy")
axes[1, 1].set_xlabel("Epoch")
axes[1, 1].set_ylabel("Accuracy (%)")
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

# Confusion matrix heatmap
im = axes[1, 2].imshow(cm, cmap="Blues")
axes[1, 2].set_xticks(range(4)); axes[1, 2].set_yticks(range(4))
axes[1, 2].set_xticklabels(label_names, rotation=30, ha="right", fontsize=8)
axes[1, 2].set_yticklabels(label_names, fontsize=8)
for i in range(4):
    for j in range(4):
        axes[1, 2].text(j, i, str(cm[i,j]), ha="center", va="center",
                        color="white" if cm[i,j] > cm.max()/2 else "black", fontsize=9)
axes[1, 2].set_title("Confusion Matrix")
axes[1, 2].set_xlabel("Predicted"); axes[1, 2].set_ylabel("Actual")

axes[1, 3].axis("off")
axes[1, 3].text(0.1, 0.7,
    f"Final Test Accuracy: {final_acc:.1%}\n\n"
    f"Architecture:\n  50 → 128 → 64 → 4\n\n"
    f"What was fixed:\n"
    f"  • Square: np.sign(sin(t))\n"
    f"  • Added Noise as class 3\n"
    f"  • 500 samples/class (was 300)\n"
    f"  • 1000 epochs (was 500)\n"
    f"  • Bigger network (128,64)",
    transform=axes[1, 3].transAxes, fontsize=9,
    verticalalignment="top", family="monospace",
    bbox=dict(boxstyle="round", facecolor="#f0f4f8", alpha=0.8)
)

plt.tight_layout()
plt.savefig("data/module4_classifier.png", dpi=120)
print("  Saved data/module4_classifier.png")

print("\n" + "=" * 60)
print("MODULE 4 COMPLETE")
print(f"Model accuracy: {final_acc:.1%} (was ~85-90% with bugs)")
print("Weights saved to data/ for the API server.")
print("NEXT: python 5_software_engineering/clean_code.py")
print("=" * 60)
