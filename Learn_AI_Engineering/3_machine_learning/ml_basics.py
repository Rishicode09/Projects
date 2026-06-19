"""
MODULE 3: MACHINE LEARNING FUNDAMENTALS
=========================================
ML = teaching a computer to find patterns in data automatically.
You show it examples, it learns the rules.

EE Analogy: Instead of hand-writing a calibration formula for your
sensor, you feed it known (input, output) pairs and it finds
the formula itself. Regression = curve-fitting. Classification =
building a comparator decision tree.

We cover:
  A) Linear Regression    — predict a number (V_out from temperature)
  B) Classification       — predict a category (fault type from readings)
  C) Model Evaluation     — how do you know if it works?
  D) scikit-learn Pipeline — production-ready ML in 10 lines
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, confusion_matrix,
                              classification_report, mean_squared_error, r2_score)
from sklearn.pipeline import Pipeline
import os, warnings
warnings.filterwarnings("ignore")
os.makedirs("data", exist_ok=True)

np.random.seed(42)

print("=" * 60)
print("MODULE 3: MACHINE LEARNING")
print("=" * 60)


# ─────────────────────────────────────────────────────────────
# PART A: LINEAR REGRESSION
# ─────────────────────────────────────────────────────────────
# Scenario: predict battery voltage from temperature and age.
# This is just fancy curve-fitting (y = mX + b, but with many X).

print("\n--- PART A: Linear Regression ---")
print("  Predict battery voltage from temperature and age (months).")

n = 200
temp_C  = np.random.uniform(5, 45, n)
age_mo  = np.random.uniform(0, 36, n)
# True relationship (we're pretending we don't know this)
voltage = 4.2 - 0.003 * temp_C - 0.015 * age_mo + np.random.randn(n) * 0.05

X = np.column_stack([temp_C, age_mo])   # feature matrix: (200, 2)
y = voltage                              # target: (200,)

# Split: 80% train, 20% test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
model = LinearRegression()
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
mse    = mean_squared_error(y_test, y_pred)
r2     = r2_score(y_test, y_pred)

print(f"\n  Learned coefficients:")
print(f"    Intercept (base voltage): {model.intercept_:.4f} V")
print(f"    Temperature coefficient:  {model.coef_[0]:.5f} V/°C  (should be ~-0.003)")
print(f"    Age coefficient:          {model.coef_[1]:.5f} V/month (should be ~-0.015)")
print(f"\n  Performance on TEST set:")
print(f"    MSE  = {mse:.6f}  (mean squared error — lower is better)")
print(f"    RMSE = {np.sqrt(mse):.4f} V  (typical error per prediction)")
print(f"    R²   = {r2:.4f}  (1.0 = perfect, 0.0 = no better than mean)")

# Predict a new case
new_battery = np.array([[35, 18]])   # 35°C, 18 months old
pred_v = model.predict(new_battery)[0]
print(f"\n  Prediction: battery at 35°C, 18 months old → {pred_v:.3f} V")


# ─────────────────────────────────────────────────────────────
# PART B: CLASSIFICATION
# ─────────────────────────────────────────────────────────────
# Scenario: classify power supply faults from voltage + current readings.
# 3 classes: Normal, Overcurrent, Undervoltage

print("\n--- PART B: Classification ---")
print("  Classify power supply faults from voltage and current readings.")

# Generate synthetic fault data
# Normal:       V~5V,  I~0.5A
# Overcurrent:  V~4V,  I~2.5A  (voltage droops under heavy load)
# Undervoltage: V~3V,  I~0.3A  (V too low, current normal/low)

def make_class(n, v_mean, v_std, i_mean, i_std, label):
    V = np.random.normal(v_mean, v_std, n)
    I = np.random.normal(i_mean, i_std, n)
    L = [label] * n
    return V, I, L

n_each = 150
V1, I1, L1 = make_class(n_each, 5.0, 0.1,  0.5, 0.05, "Normal")
V2, I2, L2 = make_class(n_each, 3.9, 0.2,  2.5, 0.15, "Overcurrent")
V3, I3, L3 = make_class(n_each, 3.1, 0.15, 0.3, 0.05, "Undervoltage")

X_cls = np.column_stack([
    np.concatenate([V1, V2, V3]),
    np.concatenate([I1, I2, I3])
])
y_cls = np.array(L1 + L2 + L3)

X_tr, X_te, y_tr, y_te = train_test_split(X_cls, y_cls, test_size=0.2,
                                            random_state=42, stratify=y_cls)

# Try 3 classifiers and compare
classifiers = {
    "Logistic Regression": LogisticRegression(max_iter=200),
    "Decision Tree":       DecisionTreeClassifier(max_depth=4),
    "Random Forest":       RandomForestClassifier(n_estimators=50),
}

print(f"\n  {'Model':<25} {'Train Acc':>10} {'Test Acc':>10} {'CV Score':>10}")
print(f"  {'-'*58}")

best_model = None
best_acc   = 0

for name, clf in classifiers.items():
    clf.fit(X_tr, y_tr)
    train_acc = accuracy_score(y_tr, clf.predict(X_tr))
    test_acc  = accuracy_score(y_te, clf.predict(X_te))
    cv_score  = cross_val_score(clf, X_tr, y_tr, cv=5).mean()
    print(f"  {name:<25} {train_acc:>9.1%} {test_acc:>9.1%} {cv_score:>9.1%}")
    if test_acc > best_acc:
        best_acc = test_acc
        best_model = clf
        best_name  = name

print(f"\n  Best model: {best_name} with {best_acc:.1%} test accuracy")

# Confusion matrix
y_pred_cls = best_model.predict(X_te)
labels = ["Normal", "Overcurrent", "Undervoltage"]
cm = confusion_matrix(y_te, y_pred_cls, labels=labels)
print(f"\n  Confusion Matrix (rows=actual, cols=predicted):")
print(f"  {'':20}", end="")
for l in labels:
    print(f"  {l:>13}", end="")
print()
for i, row_label in enumerate(labels):
    print(f"  Actual {row_label:<13}", end="")
    for j, val in enumerate(cm[i]):
        print(f"  {val:>13}", end="")
    print()

print("\n  Diagonal = correct predictions. Off-diagonal = mistakes.")

# Classification report
print(f"\n  Detailed Report:")
print(classification_report(y_te, y_pred_cls, target_names=labels))

# Predict a new reading
new_reading = np.array([[4.1, 2.3]])  # low voltage, high current
prediction  = best_model.predict(new_reading)[0]
print(f"  New reading: V=4.1V, I=2.3A → Predicted fault: {prediction}")


# ─────────────────────────────────────────────────────────────
# PART C: THE ML PIPELINE (production-ready code)
# ─────────────────────────────────────────────────────────────
print("\n--- PART C: sklearn Pipeline ---")
print("  A Pipeline chains preprocessing + model into one object.")
print("  You fit once, predict cleanly — no manual scaling needed.")

pipe = Pipeline([
    ("scaler", StandardScaler()),        # step 1: normalize features
    ("clf",    RandomForestClassifier(n_estimators=100)),  # step 2: model
])

pipe.fit(X_tr, y_tr)
pipe_acc = accuracy_score(y_te, pipe.predict(X_te))
print(f"  Pipeline accuracy: {pipe_acc:.1%}")
print(f"  Predict new point (4.1V, 2.3A): {pipe.predict([[4.1, 2.3]])[0]}")
print("  The pipeline scales the new point the same way as training data.")

# Feature importance from Random Forest
rf = classifiers["Random Forest"]
importances = rf.feature_importances_
print(f"\n  Feature importances (Random Forest):")
for feature, imp in zip(["Voltage", "Current"], importances):
    bar = "█" * int(imp * 40)
    print(f"    {feature:<10}: {imp:.3f}  {bar}")


# ─────────────────────────────────────────────────────────────
# VISUALIZE
# ─────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Module 3: Machine Learning", fontsize=14, fontweight="bold")

# Regression: actual vs predicted
axes[0].scatter(y_test, y_pred, alpha=0.5, s=20)
mn, mx = min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())
axes[0].plot([mn, mx], [mn, mx], "r--", label="Perfect")
axes[0].set_title(f"Regression: Actual vs Predicted\nR²={r2:.3f}")
axes[0].set_xlabel("Actual Voltage (V)")
axes[0].set_ylabel("Predicted Voltage (V)")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Classification scatter
colors_map = {"Normal": "green", "Overcurrent": "red", "Undervoltage": "orange"}
for label in labels:
    mask = y_cls == label
    axes[1].scatter(X_cls[mask, 0], X_cls[mask, 1],
                    label=label, color=colors_map[label], alpha=0.3, s=15)
axes[1].set_title("Fault Classification Data")
axes[1].set_xlabel("Voltage (V)")
axes[1].set_ylabel("Current (A)")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# Confusion matrix heatmap
im = axes[2].imshow(cm, cmap="Blues")
axes[2].set_xticks(range(len(labels)))
axes[2].set_yticks(range(len(labels)))
axes[2].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
axes[2].set_yticklabels(labels, fontsize=8)
for i in range(len(labels)):
    for j in range(len(labels)):
        axes[2].text(j, i, str(cm[i, j]), ha="center", va="center",
                     color="white" if cm[i,j] > cm.max()/2 else "black")
plt.colorbar(im, ax=axes[2])
axes[2].set_title("Confusion Matrix")
axes[2].set_xlabel("Predicted")
axes[2].set_ylabel("Actual")

plt.tight_layout()
plt.savefig("data/module3_ml.png", dpi=120)
print("\n  Saved data/module3_ml.png")

print("\n" + "=" * 60)
print("MODULE 3 COMPLETE")
print("You now know: regression, classification, evaluation, pipelines.")
print("NEXT: python 4_neural_networks/waveform_classifier.py")
print("=" * 60)
