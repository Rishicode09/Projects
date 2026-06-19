"""
STEP 4: TRAINING — HOW THE NETWORK LEARNS
EE Analogy: Training is like AUTO-TUNING a bank of potentiometers.

The process:
  1. Feed signal in → network makes a guess
  2. Compare guess to correct answer → compute ERROR
  3. Work backwards through network → figure out which weights caused the error
  4. Adjust weights to reduce error
  5. Repeat thousands of times

This "work backwards" step is called BACKPROPAGATION.
EE analogy: it's like tracing a signal distortion back through a circuit
and adjusting each stage's gain until the output matches the reference.

Key terms:
  Loss      = how wrong we are (like distortion / THD measurement)
  Gradient  = which direction to adjust each weight
  LR        = learning rate = step size (like a trim-pot adjustment amount)
  Epoch     = one full pass through all training data
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Import our network from Step 3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '3_build_network'))
from neural_network import NeuralNetwork, relu_derivative, softmax


# ─────────────────────────────────────────────
# LOAD & PREPARE DATA
# ─────────────────────────────────────────────

X = np.load("data/X.npy")   # shape (900, 50)
y = np.load("data/y.npy")   # shape (900,)

# NORMALIZE — scale each feature to mean=0, std=1
# EE analogy: like AC coupling — removes DC offset, normalizes amplitude
scaler = StandardScaler()
X = scaler.fit_transform(X)

# SPLIT into training set (80%) and test set (20%)
# Test set = signals the network has NEVER seen (like a calibration check)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training samples : {len(X_train)}")
print(f"Test samples     : {len(X_test)}")

# CONVERT labels to one-hot encoding
# [0] → [1, 0, 0]    [1] → [0, 1, 0]    [2] → [0, 0, 1]
# EE: like a priority encoder output — one line goes HIGH, rest stay LOW
def one_hot(y, num_classes=3):
    result = np.zeros((len(y), num_classes))
    result[np.arange(len(y)), y] = 1
    return result

Y_train = one_hot(y_train)
Y_test  = one_hot(y_test)


# ─────────────────────────────────────────────
# LOSS FUNCTION: Cross-Entropy
# ─────────────────────────────────────────────
# Measures how wrong the network's predictions are.
# EE analogy: like measuring THD (Total Harmonic Distortion) — lower is better.
#
# Formula: Loss = -mean( true_label * log(predicted_probability) )
# When prediction is perfect (prob=1.0), loss = 0
# When prediction is wrong  (prob→0), loss → infinity

def cross_entropy_loss(y_pred, y_true):
    epsilon = 1e-15  # prevent log(0)
    return -np.mean(np.sum(y_true * np.log(y_pred + epsilon), axis=1))


# ─────────────────────────────────────────────
# BACKPROPAGATION — The Learning Algorithm
# ─────────────────────────────────────────────
# This computes the GRADIENT of the loss with respect to every weight.
# Gradient = "how much does loss change if I nudge this weight?"
#
# EE analogy: Sensitivity analysis.
# If increasing a resistor value by 1% changes output by 5%, that's a high gradient.
# We adjust high-gradient components more aggressively.

def backward(net, Y_true, learning_rate=0.001):
    """
    Compute gradients and update weights using gradient descent.

    Chain rule of calculus (same as circuit signal flow analysis):
      d(Loss)/d(W3) = d(Loss)/d(a3) * d(a3)/d(z3) * d(z3)/d(W3)
    We compute this layer by layer, from OUTPUT → INPUT (backwards).
    """
    m = Y_true.shape[0]  # batch size

    # Retrieve cached values from forward pass
    X, z1, a1, z2, a2, z3, a3 = (net.cache[k] for k in ['X','z1','a1','z2','a2','z3','a3'])

    # ── OUTPUT LAYER GRADIENT ─────────────────────────────────
    # For softmax + cross-entropy, gradient simplifies beautifully to:
    dz3 = a3 - Y_true                              # prediction error: (N, 3)
    dW3 = a2.T @ dz3 / m                           # weight gradient
    db3 = np.mean(dz3, axis=0, keepdims=True)      # bias gradient

    # ── HIDDEN LAYER 2 GRADIENT ───────────────────────────────
    da2 = dz3 @ net.W3.T                           # backprop error signal
    dz2 = da2 * relu_derivative(z2)                # apply ReLU derivative
    dW2 = a1.T @ dz2 / m
    db2 = np.mean(dz2, axis=0, keepdims=True)

    # ── HIDDEN LAYER 1 GRADIENT ───────────────────────────────
    da1 = dz2 @ net.W2.T
    dz1 = da1 * relu_derivative(z1)
    dW1 = X.T @ dz1 / m
    db1 = np.mean(dz1, axis=0, keepdims=True)

    # ── UPDATE WEIGHTS (Gradient Descent) ─────────────────────
    # weight = weight - learning_rate * gradient
    # EE: trim the pot by (learning_rate × sensitivity)
    net.W3 -= learning_rate * dW3
    net.b3 -= learning_rate * db3
    net.W2 -= learning_rate * dW2
    net.b2 -= learning_rate * db2
    net.W1 -= learning_rate * dW1
    net.b1 -= learning_rate * db1


# ─────────────────────────────────────────────
# TRAINING LOOP
# ─────────────────────────────────────────────

def accuracy(net, X, y):
    preds = net.predict(X)
    return np.mean(preds == y)


EPOCHS        = 500      # how many times we loop through all data
LEARNING_RATE = 0.005    # step size per weight update (tuned by trial and error)
BATCH_SIZE    = 32       # process 32 waveforms at once (like burst sampling)

net = NeuralNetwork(input_size=50, hidden1=64, hidden2=32, output_size=3)

train_losses = []
test_accs    = []

print("\nTraining started...")
print(f"{'Epoch':<8} {'Loss':<12} {'Train Acc':<14} {'Test Acc':<12}")
print("-" * 48)

for epoch in range(EPOCHS):
    # Mini-batch gradient descent (more stable than using all data at once)
    indices = np.random.permutation(len(X_train))  # shuffle each epoch

    epoch_loss = 0
    num_batches = 0

    for start in range(0, len(X_train), BATCH_SIZE):
        batch_idx = indices[start:start + BATCH_SIZE]
        X_batch = X_train[batch_idx]
        Y_batch = Y_train[batch_idx]

        # Forward pass
        preds = net.forward(X_batch)

        # Compute loss
        loss = cross_entropy_loss(preds, Y_batch)
        epoch_loss += loss
        num_batches += 1

        # Backward pass (update weights)
        backward(net, Y_batch, LEARNING_RATE)

    avg_loss  = epoch_loss / num_batches
    test_acc  = accuracy(net, X_test, y_test)
    train_acc = accuracy(net, X_train, y_train)

    train_losses.append(avg_loss)
    test_accs.append(test_acc)

    if epoch % 50 == 0 or epoch == EPOCHS - 1:
        print(f"{epoch:<8} {avg_loss:<12.4f} {train_acc:<14.1%} {test_acc:<12.1%}")

print("\n" + "="*55)
print(f"TRAINING COMPLETE")
print(f"  Final Test Accuracy : {accuracy(net, X_test, y_test):.1%}")
print("="*55)

# ─────────────────────────────────────────────
# SAVE MODEL WEIGHTS
# ─────────────────────────────────────────────
np.save("data/W1.npy", net.W1)
np.save("data/b1.npy", net.b1)
np.save("data/W2.npy", net.W2)
np.save("data/b2.npy", net.b2)
np.save("data/W3.npy", net.W3)
np.save("data/b3.npy", net.b3)

# Save scaler parameters (needed for inference)
np.save("data/scaler_mean.npy", scaler.mean_)
np.save("data/scaler_std.npy",  scaler.scale_)
print("\nModel weights saved to data/*.npy")

# ─────────────────────────────────────────────
# PLOT TRAINING PROGRESS
# ─────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Step 4: Training Progress", fontsize=13, fontweight='bold')

ax1.plot(train_losses, color='crimson', linewidth=1.5)
ax1.set_title("Loss Over Epochs\n(like watching THD drop during tuning)")
ax1.set_xlabel("Epoch")
ax1.set_ylabel("Cross-Entropy Loss")
ax1.grid(True, alpha=0.3)

ax2.plot([a*100 for a in test_accs], color='steelblue', linewidth=1.5)
ax2.axhline(95, color='green', linestyle='--', alpha=0.7, label='95% target')
ax2.set_title("Test Accuracy Over Epochs\n(% of unseen signals classified correctly)")
ax2.set_xlabel("Epoch")
ax2.set_ylabel("Accuracy (%)")
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("data/step4_training.png", dpi=120)
print("  Plot saved to data/step4_training.png")
print()
print("NEXT: Run  python 5_api_server/app.py")
print("      Then open  5_frontend/index.html  in your browser")

import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, sys, os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","3_build_network"))
from neural_network import NeuralNetwork, relu_derivative
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
X=np.load("data/X.npy"); y=np.load("data/y.npy")
sc=StandardScaler(); X=sc.fit_transform(X)
Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)
def one_hot(y,n=3):
    r=np.zeros((len(y),n)); r[np.arange(len(y)),y]=1; return r
Ytr=one_hot(ytr); Yte=one_hot(yte)
def loss(p,t): return -np.mean(np.sum(t*np.log(p+1e-15),axis=1))
def backward(net,Yt,lr):
    m=Yt.shape[0]; X,z1,a1,z2,a2,a3=(net.cache[k] for k in["X","z1","a1","z2","a2","a3"])
    dz3=a3-Yt; dW3=a2.T@dz3/m; db3=np.mean(dz3,axis=0,keepdims=True)
    dz2=(dz3@net.W3.T)*relu_derivative(net.cache["z2"]); dW2=a1.T@dz2/m; db2=np.mean(dz2,axis=0,keepdims=True)
    dz1=(dz2@net.W2.T)*relu_derivative(z1); dW1=X.T@dz1/m; db1=np.mean(dz1,axis=0,keepdims=True)
    for p,g in [(net.W3,dW3),(net.b3,db3),(net.W2,dW2),(net.b2,db2),(net.W1,dW1),(net.b1,db1)]: p-=lr*g
def acc(net,X,y): return np.mean(net.predict(X)==y)
net=NeuralNetwork(); losses=[]; accs=[]
print(f"{'Epoch':<8}{'Loss':<12}{'TrainAcc':<14}{'TestAcc'}")
for ep in range(500):
    idx=np.random.permutation(len(Xtr)); ls=0; nb=0
    for s in range(0,len(Xtr),32):
        Xb=Xtr[idx[s:s+32]]; Yb=Ytr[idx[s:s+32]]
        ls+=loss(net.forward(Xb),Yb); nb+=1; backward(net,Yb,0.005)
    avg=ls/nb; va=acc(net,Xte,yte); losses.append(avg); accs.append(va)
    if ep%50==0 or ep==499: print(f"{ep:<8}{avg:<12.4f}{acc(net,Xtr,ytr):<14.1%}{va:.1%}")
print(f"FINAL TEST ACCURACY: {acc(net,Xte,yte):.1%}")
for nm,w in[("W1",net.W1),("b1",net.b1),("W2",net.W2),("b2",net.b2),("W3",net.W3),("b3",net.b3)]:
    np.save(f"data/{nm}.npy",w)
np.save("data/scaler_mean.npy",sc.mean_); np.save("data/scaler_std.npy",sc.scale_)
print("Weights saved. NEXT: python 5_api_server/app.py")
