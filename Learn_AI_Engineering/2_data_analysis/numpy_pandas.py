"""
MODULE 2a: DATA ANALYSIS WITH NUMPY & PANDAS
==============================================
These two libraries are the backbone of ALL data work in Python.

NumPy  = fast math on arrays (like MATLAB matrices)
Pandas = spreadsheet in Python (tables, filtering, grouping)

EE Analogy:
  NumPy  = your oscilloscope's math channel (applies formulas to all samples at once)
  Pandas = your Excel-based data logger with filtering and pivot tables
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

os.makedirs("data", exist_ok=True)

print("=" * 60)
print("MODULE 2a: NUMPY & PANDAS")
print("=" * 60)


# ─────────────────────────────────────────────────────────────
# PART A: NUMPY
# ─────────────────────────────────────────────────────────────
print("\n--- PART A: NumPy ---")

# Create arrays
a = np.array([1, 2, 3, 4, 5])
b = np.array([10, 20, 30, 40, 50])

print(f"a = {a}")
print(f"b = {b}")

# Vectorized math — operates on ALL elements at once (no for loop needed!)
# EE: like applying a formula to every sample in your oscilloscope buffer
print(f"a + b     = {a + b}")
print(f"a * 2     = {a * 2}")
print(f"a ** 2    = {a ** 2}")          # square every element
print(f"np.sqrt(b)= {np.sqrt(b)}")
print(f"a + b     = {a + b}")
print(f"a * b     = {a * b}")           # element-wise multiply

# Common array creators
zeros  = np.zeros(5)
ones   = np.ones(5)
rng    = np.arange(0, 10, 2)            # like range() but returns array: 0,2,4,6,8
linsp  = np.linspace(0, 1, 6)          # 6 evenly-spaced points from 0 to 1
rand   = np.random.randn(5)            # 5 random values (normal distribution)

print(f"\nzeros  = {zeros}")
print(f"ones   = {ones}")
print(f"arange = {rng}")
print(f"linspace={linsp}")
print(f"random = {rand.round(3)}")

# 2D arrays (matrices)
# Shape (rows, cols)
matrix = np.array([
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
])
print(f"\nMatrix shape: {matrix.shape}")  # (3, 3)
print(f"Row 0: {matrix[0, :]}")           # first row
print(f"Col 1: {matrix[:, 1]}")           # second column
print(f"Element [1,2]: {matrix[1, 2]}")   # row 1, col 2

# Matrix operations
print(f"Transpose:\n{matrix.T}")
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
print(f"Matrix multiply A@B =\n{A @ B}")   # @ is matrix multiply

# Statistics with NumPy
data = np.array([23.4, 24.1, 22.8, 25.0, 23.7, 24.5, 22.9])
print(f"\nTemperature readings: {data}")
print(f"  mean   = {np.mean(data):.2f}")
print(f"  std    = {np.std(data):.2f}")
print(f"  min    = {np.min(data):.2f}")
print(f"  max    = {np.max(data):.2f}")
print(f"  median = {np.median(data):.2f}")

# Boolean indexing — filter data without a for loop
hot = data[data > 24.0]
print(f"  readings > 24°C: {hot}")

# Simulate a real signal — 1 second of a 10Hz sine sampled at 1kHz
fs   = 1000             # sample rate: 1000 Hz
t    = np.linspace(0, 1, fs)
freq = 10               # 10 Hz sine
signal = np.sin(2 * np.pi * freq * t) + 0.1 * np.random.randn(fs)
print(f"\nSignal: {fs} samples, mean={np.mean(signal):.3f}, std={np.std(signal):.3f}")

# FFT — see what frequencies are in the signal
fft_vals = np.abs(np.fft.rfft(signal))
freqs    = np.fft.rfftfreq(fs, 1/fs)
peak_idx = np.argmax(fft_vals)
print(f"  FFT peak at {freqs[peak_idx]:.1f} Hz  (should be ~10 Hz)")


# ─────────────────────────────────────────────────────────────
# PART B: PANDAS
# ─────────────────────────────────────────────────────────────
print("\n--- PART B: Pandas ---")

# Create a DataFrame (like a spreadsheet table)
df = pd.DataFrame({
    "timestamp_ms": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900],
    "voltage_V":    [5.02, 5.01, 4.99, 5.00, 5.03, 4.98, 5.01, 5.00, 4.99, 5.02],
    "current_mA":   [10.1, 10.0, 10.2, 9.9, 10.3, 10.1, 9.8, 10.0, 10.1, 10.2],
    "temp_C":       [23.1, 23.2, 23.4, 23.5, 23.7, 23.9, 24.1, 24.2, 24.4, 24.5],
    "channel":      ["A","A","A","A","A","B","B","B","B","B"]
})

print("\nRaw DataFrame:")
print(df.to_string())

print("\n.describe() — automatic statistics on every numeric column:")
print(df.describe().round(3))

# Accessing columns and rows
print(f"\nAll voltages: {df['voltage_V'].values}")
print(f"Row 0: {df.iloc[0].to_dict()}")
print(f"Rows 2–4:\n{df.iloc[2:5]}")

# Filtering — like WHERE clause in SQL / filtering in Excel
hot_rows = df[df["temp_C"] > 24.0]
print(f"\nRows where temp > 24°C:")
print(hot_rows[["timestamp_ms","temp_C","channel"]])

# Adding a computed column
df["power_mW"] = df["voltage_V"] * df["current_mA"]
print(f"\nPower column added (V × I):")
print(df[["timestamp_ms", "voltage_V", "current_mA", "power_mW"]])

# GroupBy — split data by a category and aggregate
# Like a pivot table in Excel
print("\nGroupBy channel:")
grouped = df.groupby("channel").agg(
    avg_voltage=("voltage_V", "mean"),
    avg_current=("current_mA", "mean"),
    avg_temp=("temp_C", "mean"),
    samples=("timestamp_ms", "count")
).round(3)
print(grouped)

# Sort
top3_power = df.sort_values("power_mW", ascending=False).head(3)
print(f"\nTop 3 highest power moments:")
print(top3_power[["timestamp_ms", "power_mW"]])

# Save and load CSV
df.to_csv("data/measurements_pandas.csv", index=False)
df_loaded = pd.read_csv("data/measurements_pandas.csv")
print(f"\nSaved and reloaded {len(df_loaded)} rows from CSV")

# ─────────────────────────────────────────────────────────────
# PART C: VISUALIZATION
# ─────────────────────────────────────────────────────────────
print("\n--- PART C: Matplotlib Plots ---")

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle("Module 2: Data Analysis — Visualizations", fontsize=14, fontweight="bold")

# Plot 1: Time-series signal
t_ms = df["timestamp_ms"]
axes[0, 0].plot(t_ms, df["voltage_V"], "b-o", markersize=4, label="Voltage")
axes[0, 0].set_title("Voltage over Time")
axes[0, 0].set_xlabel("Time (ms)")
axes[0, 0].set_ylabel("Voltage (V)")
axes[0, 0].axhline(5.0, color="red", linestyle="--", alpha=0.5, label="Nominal 5V")
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Plot 2: Scatter plot (current vs voltage)
colors = {"A": "blue", "B": "red"}
for ch in ["A", "B"]:
    mask = df["channel"] == ch
    axes[0, 1].scatter(df.loc[mask, "voltage_V"], df.loc[mask, "current_mA"],
                       label=f"Ch {ch}", color=colors[ch], s=60)
axes[0, 1].set_title("Current vs Voltage by Channel")
axes[0, 1].set_xlabel("Voltage (V)")
axes[0, 1].set_ylabel("Current (mA)")
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Plot 3: Histogram of temperature
axes[1, 0].hist(df["temp_C"], bins=6, color="green", alpha=0.7, edgecolor="black")
axes[1, 0].set_title("Temperature Distribution")
axes[1, 0].set_xlabel("Temperature (°C)")
axes[1, 0].set_ylabel("Frequency")
axes[1, 0].grid(True, alpha=0.3)

# Plot 4: FFT of simulated signal
axes[1, 1].plot(freqs[:200], fft_vals[:200], color="purple")
axes[1, 1].set_title("FFT Spectrum of 10Hz Sine")
axes[1, 1].set_xlabel("Frequency (Hz)")
axes[1, 1].set_ylabel("|FFT|")
axes[1, 1].axvline(10, color="red", linestyle="--", label="10 Hz")
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("data/module2_plots.png", dpi=120)
print("  Saved data/module2_plots.png")

print("\n" + "=" * 60)
print("MODULE 2a COMPLETE")
print("You now know: NumPy arrays, Pandas DataFrames, plotting.")
print("NEXT: python 2_data_analysis/statistics.py")
print("=" * 60)
