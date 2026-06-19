# AI Concepts — Explained for Electrical Engineers

## 1. What IS a Neural Network?

It's a series of weighted sums followed by nonlinear functions.

```
EE Circuit:          AI Equivalent:
─────────────────────────────────────────────────────
Resistor divider  →  Weights (W)
DC bias voltage   →  Bias (b)
Summing amplifier →  Weighted sum: z = W·x + b
Transfer curve    →  Activation function: f(z)
Cascaded stages   →  Layers of neurons
```

A neuron computes:  `output = f( w1·x1 + w2·x2 + ... + wn·xn + b )`

This is IDENTICAL to an op-amp weighted summer followed by a nonlinear element.

---

## 2. Why Do We Need Nonlinearity?

If every layer is just a linear operation (weighted sum), you could collapse
all layers into ONE layer. The whole network would just be linear.

Nonlinear activations (ReLU, sigmoid, tanh) let the network represent
complex, curved decision boundaries.

EE analogy: A cascade of linear amplifiers is still a linear amplifier.
You need saturation, clipping, or a diode to get nonlinear behavior.

---

## 3. What Are Weights?

Weights are the 6,531 numbers the network learned during training.
Before training: random (like random component tolerances).
After training: carefully tuned (like a calibrated instrument).

The training process found values that minimize prediction error —
automatically, without you hand-tuning anything.

---

## 4. What Is Training?

Training = minimizing a loss function using gradient descent.

```
STEP 1: Forward pass  → make a prediction
STEP 2: Compute loss  → measure how wrong we were
STEP 3: Backprop      → compute how each weight contributed to the error
STEP 4: Update        → nudge each weight to reduce error
STEP 5: Repeat        → 500 × 28 batches = ~14,000 updates
```

EE analogy: Imagine an auto-tuner that:
1. Measures your circuit's output
2. Compares it to a reference
3. Calculates sensitivity of each trim-pot on the error
4. Adjusts each trim-pot by a tiny amount
5. Repeats until output matches reference

Backpropagation is the CHAIN RULE of calculus applied backwards
through the network — exactly like sensitivity analysis in circuit design.

---

## 5. What Is a Learning Rate?

The fraction by which we adjust weights each step.

- Too large → overshoots, oscillates (like integral windup in a PID)
- Too small → converges too slowly
- Just right → stable, converges to a good solution

We used 0.005 — found by trial and error (or can be auto-tuned).

---

## 6. What Is Loss?

Loss = a number measuring how wrong our predictions are.

We used Cross-Entropy loss:
  `Loss = -mean( true_label × log(predicted_probability) )`

EE analogy: Total Harmonic Distortion (THD).
Lower is better. Perfect prediction = 0.

---

## 7. Overfitting — The Signal Integrity Problem

EE analogy: A filter perfectly tuned to noise on a specific PCB layout
will fail when you change the PCB. It learned the board, not the signal.

Same with AI: if the model memorizes training data, it fails on new data.

Solution: Use a separate TEST set — signals the model never saw during training.
Our test accuracy tells us how well the model generalizes.

---

## 8. The Full Stack — What Each Piece Does

```
┌─────────────────────────────────────────────────────────────────┐
│  DATA LAYER         (1_understand_data/)                        │
│  Generates waveforms + labels. Your "signal library."           │
├─────────────────────────────────────────────────────────────────┤
│  MODEL LAYER        (2_build_neuron/ + 3_build_network/)        │
│  The mathematical structure. Weights unset = untrained.         │
├─────────────────────────────────────────────────────────────────┤
│  TRAINING LAYER     (4_train_model/)                            │
│  Optimizes weights. Produces trained model saved as .npy files. │
├─────────────────────────────────────────────────────────────────┤
│  API LAYER          (5_api_server/)                             │
│  Flask server. Loads trained model. Accepts HTTP requests.      │
│  EE: GPIB/USB driver for your AI "instrument"                   │
├─────────────────────────────────────────────────────────────────┤
│  FRONTEND LAYER     (5_frontend/)                               │
│  HTML page. User sends a signal, AI returns prediction.         │
│  EE: The front panel of your instrument                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. What to Learn Next

| Topic | EE Parallel | Why It Matters |
|-------|-------------|----------------|
| Convolutional Neural Networks (CNN) | FIR filter + pooling | Images, 2D signals |
| Recurrent Neural Networks (RNN/LSTM) | IIR filter with memory | Time-series, sequences |
| Transformer | Attention = dynamic filter bank | NLP, state-of-the-art |
| PyTorch/TensorFlow | HDL for neural networks | Industry standard tools |
| GPU training | Parallel computation, like DSP hardware | Real-scale training |
| Batch Normalization | Like AGC (Automatic Gain Control) | Faster, stabler training |

---

## 10. Glossary (EE → AI)

| AI Term | EE Equivalent |
|---------|---------------|
| Weight | Resistor value / gain |
| Bias | DC offset |
| Activation | Transfer curve / saturation |
| Layer | Cascaded stage |
| Forward pass | Signal flowing through circuit |
| Backward pass / Backprop | Sensitivity analysis, reversed |
| Loss | THD / error signal |
| Gradient | Sensitivity coefficient (∂output/∂parameter) |
| Learning rate | Step size of trim-pot adjustment |
| Epoch | One full sweep of calibration |
| Batch | Burst of samples processed together |
| Overfitting | Over-optimized for one specific test fixture |
| Dropout | Randomly open-circuiting neurons (regularization) |
| Softmax | Priority encoder → probabilities |
| One-hot encoding | Decoder output (one line HIGH) |
| Normalization | AC coupling + AGC |
