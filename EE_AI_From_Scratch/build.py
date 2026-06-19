"""
build.py — Runs during deployment to prepare the model.
=========================================================
EE Analogy: This is the "factory calibration" step.
Before the instrument ships, we run it through calibration once
so it arrives at the customer pre-tuned and ready to use.

Cloud servers start EMPTY — they don't have your trained weights.
This script regenerates the data and trains the model so the
deployed API has a working brain to load.

It runs steps 1 and 4 automatically (step 4 imports 1's output).
"""

import subprocess
import sys
import os

# Always run from the project root so data/ lands in the right place
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

print("=" * 55)
print("DEPLOYMENT BUILD: Preparing the AI model")
print("=" * 55)

steps = [
    ("Generating training data",  "1_understand_data/generate_signals.py"),
    ("Training the neural network", "4_train_model/train.py"),
]

for description, script in steps:
    print(f"\n>>> {description} ({script})")
    result = subprocess.run([sys.executable, script])
    if result.returncode != 0:
        print(f"BUILD FAILED at: {script}")
        sys.exit(1)

print("\n" + "=" * 55)
print("BUILD COMPLETE — model weights are ready in data/")
print("The server can now load a trained model on startup.")
print("=" * 55)
