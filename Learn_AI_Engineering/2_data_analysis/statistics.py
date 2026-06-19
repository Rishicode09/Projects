"""
MODULE 2b: STATISTICS FOR ENGINEERS
=====================================
Statistics is how you UNDERSTAND data.
Without it, you're just staring at numbers.

EE Analogy: Statistics is like your signal analyzer.
Instead of eyeballing a waveform, you get real measurements:
noise floor, SNR, bandwidth, confidence intervals.

We'll use a real-world scenario: you're analyzing power supply
noise across 5 different PCB revisions.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import os

os.makedirs("data", exist_ok=True)

print("=" * 60)
print("MODULE 2b: STATISTICS")
print("=" * 60)

np.random.seed(42)

# ─────────────────────────────────────────────────────────────
# SCENARIO: 5 PCB revisions, measuring 3.3V rail noise (mV)
# ─────────────────────────────────────────────────────────────
revisions = {
    "Rev A": np.random.normal(loc=12.5, scale=3.0, size=50),  # noisy
    "Rev B": np.random.normal(loc=10.1, scale=2.5, size=50),
    "Rev C": np.random.normal(loc=8.3,  scale=2.0, size=50),
    "Rev D": np.random.normal(loc=6.2,  scale=1.5, size=50),
    "Rev E": np.random.normal(loc=5.1,  scale=1.2, size=50),  # best
}

print("\n--- SECTION 1: Descriptive Statistics ---")
print("  (Summarizing what your data looks like)")
print()
print(f"  {'Revision':<8} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8} {'Median':>8}")
print(f"  {'-'*52}")
for rev, noise in revisions.items():
    print(f"  {rev:<8} {np.mean(noise):>7.2f}  {np.std(noise):>7.2f}  "
          f"{np.min(noise):>7.2f}  {np.max(noise):>7.2f}  {np.median(noise):>7.2f}")

print("\n  Units are mV of ripple on 3.3V rail")
print("  Lower = better. Rev E is the quietest.")

# ─────────────────────────────────────────────────────────────
# SECTION 2: DISTRIBUTIONS & SPREAD
# ─────────────────────────────────────────────────────────────
print("\n--- SECTION 2: Distributions ---")
print("  A distribution tells you WHERE your data points tend to cluster.")
print()

rev_d = revisions["Rev D"]
mean  = np.mean(rev_d)
std   = np.std(rev_d)

print(f"  Rev D noise:  mean = {mean:.2f} mV, std = {std:.2f} mV")
print()
print("  The '68-95-99.7 Rule' for normally-distributed data:")
within_1std = np.sum(np.abs(rev_d - mean) < 1*std)
within_2std = np.sum(np.abs(rev_d - mean) < 2*std)
within_3std = np.sum(np.abs(rev_d - mean) < 3*std)
print(f"    Within 1 std ({mean:.1f}±{std:.1f} mV): {within_1std}/50 = {within_1std*2}% (expect 68%)")
print(f"    Within 2 std ({mean:.1f}±{2*std:.1f} mV): {within_2std}/50 = {within_2std*2}% (expect 95%)")
print(f"    Within 3 std ({mean:.1f}±{3*std:.1f} mV): {within_3std}/50 = {within_3std*2}% (expect 99.7%)")

# Percentiles
p5, p25, p50, p75, p95 = np.percentile(rev_d, [5, 25, 50, 75, 95])
print(f"\n  Percentiles of Rev D noise:")
print(f"    P5  = {p5:.2f} mV  (5% of readings are below this)")
print(f"    P25 = {p25:.2f} mV  (25th percentile / Q1)")
print(f"    P50 = {p50:.2f} mV  (median)")
print(f"    P75 = {p75:.2f} mV  (75th percentile / Q3)")
print(f"    P95 = {p95:.2f} mV  (95% of readings are below this)")
print(f"    IQR = {p75-p25:.2f} mV  (interquartile range = P75-P25)")

# ─────────────────────────────────────────────────────────────
# SECTION 3: CORRELATION
# ─────────────────────────────────────────────────────────────
print("\n--- SECTION 3: Correlation ---")
print("  How strongly do two variables move together?")
print("  Range: -1 (perfect inverse) to +1 (perfect positive)")

n = 100
temperature = np.random.uniform(20, 80, n)
# Resistance increases with temperature (positive correlation)
resistance  = 100 + 0.3 * temperature + np.random.randn(n) * 5
# Battery voltage drops as temperature rises (negative correlation)
battery_v   = 4.2 - 0.005 * temperature + np.random.randn(n) * 0.05

corr_temp_res = np.corrcoef(temperature, resistance)[0, 1]
corr_temp_bat = np.corrcoef(temperature, battery_v)[0, 1]

print(f"  Temperature vs Resistance: r = {corr_temp_res:.3f}  (positive — resistance rises with temp)")
print(f"  Temperature vs Battery V:  r = {corr_temp_bat:.3f}  (negative — voltage drops with temp)")

# ─────────────────────────────────────────────────────────────
# SECTION 4: HYPOTHESIS TESTING
# ─────────────────────────────────────────────────────────────
# "Is Rev D actually better than Rev C, or just lucky noise?"
# We use a t-test: if p < 0.05, the difference is real (not random).
print("\n--- SECTION 4: Hypothesis Testing (t-test) ---")
print("  Question: Is Rev D's noise REALLY lower than Rev C?")
print("  Or could this be sampling luck?")

rev_c = revisions["Rev C"]
rev_d = revisions["Rev D"]
t_stat, p_value = stats.ttest_ind(rev_c, rev_d)

print(f"\n  Rev C mean noise: {np.mean(rev_c):.2f} mV")
print(f"  Rev D mean noise: {np.mean(rev_d):.2f} mV")
print(f"  t-statistic: {t_stat:.3f}")
print(f"  p-value:     {p_value:.6f}")
print()
if p_value < 0.05:
    print("  CONCLUSION: p < 0.05 → the difference IS statistically significant.")
    print("  Rev D is genuinely quieter. Go with Rev D.")
else:
    print("  CONCLUSION: p >= 0.05 → difference could be random noise.")
    print("  Need more data or the designs are equivalent.")

print()
print("  Rule of thumb: p < 0.05 means less than 5% chance the")
print("  difference is due to random variation.")

# ─────────────────────────────────────────────────────────────
# SECTION 5: CORRELATION MATRIX (multiple variables at once)
# ─────────────────────────────────────────────────────────────
print("\n--- SECTION 5: Full Correlation Matrix ---")

df = pd.DataFrame({
    "temp_C":      temperature,
    "resistance_Ω": resistance,
    "battery_V":   battery_v,
    "current_mA":  50 - 0.1*temperature + np.random.randn(n)*2
})

corr_matrix = df.corr().round(3)
print(corr_matrix)
print("\n  Read: strong positive = close to 1.0, strong negative = close to -1.0")
print("  Diagonal is always 1.0 (a variable perfectly correlates with itself)")

# ─────────────────────────────────────────────────────────────
# VISUALIZE
# ─────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(12, 9))
fig.suptitle("Module 2b: Statistics", fontsize=14, fontweight="bold")

# Box plots of noise by revision
axes[0, 0].boxplot([revisions[r] for r in revisions], tick_labels=list(revisions.keys()))
axes[0, 0].set_title("Noise by PCB Revision (Box Plot)")
axes[0, 0].set_ylabel("Ripple (mV)")
axes[0, 0].axhline(5.0, color="green", linestyle="--", alpha=0.7, label="5mV target")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Histogram with normal curve
x_range = np.linspace(mean - 4*std, mean + 4*std, 200)
axes[0, 1].hist(rev_d, bins=12, density=True, alpha=0.7, color="blue", label="Rev D data")
axes[0, 1].plot(x_range, stats.norm.pdf(x_range, mean, std), "r-", lw=2, label="Normal fit")
axes[0, 1].set_title("Rev D Noise — Histogram + Normal Fit")
axes[0, 1].set_xlabel("Ripple (mV)")
axes[0, 1].set_ylabel("Density")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Scatter: temp vs resistance
axes[1, 0].scatter(temperature, resistance, alpha=0.5, s=20, color="green")
m, b = np.polyfit(temperature, resistance, 1)
axes[1, 0].plot(temperature, m*temperature + b, "r-", lw=2, label=f"r={corr_temp_res:.2f}")
axes[1, 0].set_title("Temperature vs Resistance")
axes[1, 0].set_xlabel("Temperature (°C)")
axes[1, 0].set_ylabel("Resistance (Ω)")
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# Heatmap of correlation matrix
cm = df.corr().values
labels = list(df.columns)
im = axes[1, 1].imshow(cm, cmap="RdBu", vmin=-1, vmax=1)
axes[1, 1].set_xticks(range(len(labels)))
axes[1, 1].set_yticks(range(len(labels)))
axes[1, 1].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
axes[1, 1].set_yticklabels(labels, fontsize=8)
for i in range(len(labels)):
    for j in range(len(labels)):
        axes[1, 1].text(j, i, f"{cm[i,j]:.2f}", ha="center", va="center", fontsize=8)
plt.colorbar(im, ax=axes[1, 1])
axes[1, 1].set_title("Correlation Matrix Heatmap")

plt.tight_layout()
plt.savefig("data/module2b_stats.png", dpi=120)
print("\n  Saved data/module2b_stats.png")

print("\n" + "=" * 60)
print("MODULE 2b COMPLETE")
print("You now know: distributions, std, correlation, hypothesis testing.")
print("NEXT: python 3_machine_learning/ml_basics.py")
print("=" * 60)
