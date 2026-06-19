# Full-Stack AI From Scratch — For Electrical Engineers
## Built by You, Explained Like a Circuit

---

## What You're Building

A complete AI system that **classifies electrical waveforms** (sine, square, triangle waves).
This is 100% relevant to your field — signal analysis is core EE work.

```
[Raw Signal Data] → [Neural Network] → [Prediction API] → [Web Frontend]
     (data)            (brain/model)      (Flask server)    (HTML page)
```

---

## The Big Picture — AI is Just Math on Numbers

As an EE you already know:
- **Ohm's Law**: V = IR — input goes in, a formula transforms it, output comes out
- **Op-Amp**: amplifies and transforms a signal
- **Filter**: suppresses certain frequencies

A **neural network** does the same thing — it's a series of mathematical "filters"
that transform raw numbers into a prediction.

---

## The 5 Steps (Run in Order)

| Step | File | What You Learn |
|------|------|----------------|
| 1 | `1_understand_data/generate_signals.py` | Where AI data comes from |
| 2 | `2_build_neuron/single_neuron.py` | What one "neuron" actually does |
| 3 | `3_build_network/neural_network.py` | How neurons stack into a brain |
| 4 | `4_train_model/train.py` | How the model learns (backprop) |
| 5 | `5_api_server/app.py` + `5_frontend/index.html` | Full-stack deployment |

---

## Install Dependencies First

```bash
pip install numpy matplotlib flask scikit-learn
```

Then run each file in order:
```bash
python 1_understand_data/generate_signals.py
python 2_build_neuron/single_neuron.py
python 3_build_network/neural_network.py
python 4_train_model/train.py
python 5_api_server/app.py   # then open 5_frontend/index.html in browser
```
