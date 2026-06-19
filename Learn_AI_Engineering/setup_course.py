"""
setup_course.py
===============
Run this ONE script and it creates the entire course folder structure.

    python setup_course.py

Then work through the modules in order:
  1. python 1_python_basics/fundamentals.py
  2. python 2_data_analysis/numpy_pandas.py
  3. python 2_data_analysis/statistics.py
  4. python 3_machine_learning/ml_basics.py
  5. python 4_neural_networks/fixed_waveform_classifier.py
  6. python 5_software_engineering/clean_code.py
  7. python 6_full_project/app.py   (then open http://localhost:5000)
"""

import os, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))

def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(textwrap.dedent(content).lstrip())
    print(f"  created  {path}")

# ─────────────────────────────────────────────────────────────────────────────
# requirements.txt
# ─────────────────────────────────────────────────────────────────────────────
write("requirements.txt", """
    numpy
    pandas
    matplotlib
    scikit-learn
    flask
    flask-cors
    gunicorn
""")

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 — Python Basics
# ─────────────────────────────────────────────────────────────────────────────
write("1_python_basics/fundamentals.py", '''
    """
    MODULE 1: PYTHON FUNDAMENTALS
    ==============================
    Every AI/data/software engineer starts here.
    Python is the #1 language for all three fields.

    EE Analogy: Python is your lab bench multimeter.
    Before you do anything fancy, you need to know how to use
    the basic instrument. This module is that instrument.

    Run this file and read every line alongside its output.
    """

    print("=" * 60)
    print("MODULE 1: PYTHON FUNDAMENTALS")
    print("=" * 60)


    # ─────────────────────────────────────────────────────────────
    # SECTION 1: VARIABLES AND DATA TYPES
    # ─────────────────────────────────────────────────────────────
    # A variable is just a labelled box that holds a value.
    # Python figures out the type automatically (no 'int x = 5' needed).

    print("\\n--- SECTION 1: Variables & Types ---")

    voltage    = 3.3          # float  (decimal number)
    num_pins   = 40           # int    (whole number)
    chip_name  = "STM32"      # str    (text, use quotes)
    is_powered = True         # bool   (True or False only)
    no_value   = None         # NoneType (represents "nothing" / missing)

    print(f"voltage    = {voltage}   type: {type(voltage)}")
    print(f"num_pins   = {num_pins}   type: {type(num_pins)}")
    print(f"chip_name  = {chip_name}   type: {type(chip_name)}")
    print(f"is_powered = {is_powered}  type: {type(is_powered)}")
    print(f"no_value   = {no_value}   type: {type(no_value)}")

    # String operations
    print("\\nString tricks:")
    s = "Hello Engineer"
    print(f"  upper()     : {s.upper()}")
    print(f"  lower()     : {s.lower()}")
    print(f"  split()     : {s.split()}")
    print(f"  replace()   : {s.replace('Engineer', 'World')}")
    print(f"  length      : {len(s)}")
    print(f"  slice [0:5] : {s[0:5]}")   # grab first 5 characters

    # Math operations
    print("\\nMath:")
    a, b = 10, 3
    print(f"  {a} + {b}  = {a + b}")
    print(f"  {a} - {b}  = {a - b}")
    print(f"  {a} * {b}  = {a * b}")
    print(f"  {a} / {b}  = {a / b:.4f}  (float division)")
    print(f"  {a} // {b} = {a // b}  (integer division, drops remainder)")
    print(f"  {a} % {b}  = {a % b}  (modulo = remainder)")
    print(f"  {a} ** {b} = {a ** b}  (power: 10^3)")


    # ─────────────────────────────────────────────────────────────
    # SECTION 2: LISTS AND DICTIONARIES
    # ─────────────────────────────────────────────────────────────
    # Lists = ordered collections (like an array in C)
    # Dicts = key→value pairs (like a lookup table / hash map)

    print("\\n--- SECTION 2: Lists & Dicts ---")

    # LIST
    voltages = [1.8, 3.3, 5.0, 12.0]
    print(f"voltages        = {voltages}")
    print(f"  first item    = {voltages[0]}")    # index 0 = first
    print(f"  last item     = {voltages[-1]}")   # -1 = last
    print(f"  first two     = {voltages[:2]}")   # slice
    print(f"  length        = {len(voltages)}")

    voltages.append(24.0)                        # add to end
    voltages.remove(1.8)                         # remove by value
    print(f"  after changes = {voltages}")

    # List comprehension — create a list using a one-liner formula
    # EE: like a for-loop but written as a formula
    doubled = [v * 2 for v in voltages]          # double each voltage
    high_v  = [v for v in voltages if v > 5]     # filter: keep only >5V
    print(f"  doubled       = {doubled}")
    print(f"  above 5V      = {high_v}")

    # DICTIONARY
    component = {
        "name":      "LM358 Op-Amp",
        "vcc":       5.0,
        "pins":      8,
        "in_stock":  True
    }
    print(f"\\ncomponent = {component}")
    print(f"  name    : {component['name']}")
    print(f"  vcc     : {component['vcc']}V")
    component["package"] = "DIP-8"              # add new key
    print(f"  keys    : {list(component.keys())}")
    print(f"  values  : {list(component.values())}")

    # Check if key exists before accessing
    if "package" in component:
        print(f"  package : {component['package']}")


    # ─────────────────────────────────────────────────────────────
    # SECTION 3: CONTROL FLOW (if / for / while)
    # ─────────────────────────────────────────────────────────────

    print("\\n--- SECTION 3: Control Flow ---")

    # IF / ELIF / ELSE
    supply_voltage = 4.2

    if supply_voltage > 5.0:
        print(f"  {supply_voltage}V: OVERVOLTAGE — check regulator")
    elif supply_voltage > 3.0:
        print(f"  {supply_voltage}V: Normal range (3.0V–5.0V)")
    elif supply_voltage > 1.8:
        print(f"  {supply_voltage}V: Low voltage logic")
    else:
        print(f"  {supply_voltage}V: WARNING — too low")

    # FOR LOOP — iterate over a list
    print("\\n  Scanning I2C addresses:")
    i2c_addresses = [0x48, 0x49, 0x4A, 0x4B]
    for addr in i2c_addresses:
        print(f"    Polling address 0x{addr:02X}...")

    # FOR with range() — like a classic C for-loop
    print("\\n  Counting with range:")
    for i in range(0, 5):                       # 0, 1, 2, 3, 4
        print(f"    i = {i}", end="  ")
    print()

    # WHILE LOOP
    print("\\n  Waiting for ADC ready:")
    adc_count = 0
    adc_ready = False
    while not adc_ready:
        adc_count += 1
        if adc_count >= 3:
            adc_ready = True
    print(f"    ADC ready after {adc_count} polls")

    # enumerate — gives (index, value) pairs
    print("\\n  enumerate example:")
    sensors = ["temp", "pressure", "humidity"]
    for i, name in enumerate(sensors):
        print(f"    sensor[{i}] = {name}")

    # zip — iterate two lists together
    print("\\n  zip example:")
    pins   = [14, 15, 16]
    labels = ["SDA", "SCL", "INT"]
    for pin, label in zip(pins, labels):
        print(f"    GPIO{pin} = {label}")


    # ─────────────────────────────────────────────────────────────
    # SECTION 4: FUNCTIONS
    # ─────────────────────────────────────────────────────────────
    # A function is a reusable block of code.
    # EE: like a subcircuit — wire it once, reuse it anywhere.

    print("\\n--- SECTION 4: Functions ---")

    def ohms_law(voltage, resistance):
        """Calculate current from voltage and resistance.
        Args:
            voltage    : supply voltage in Volts
            resistance : resistance in Ohms
        Returns:
            current in Amperes
        """
        if resistance == 0:
            raise ValueError("Resistance cannot be zero (would be a short circuit!)")
        return voltage / resistance

    current = ohms_law(5.0, 220)
    print(f"  5V / 220Ω = {current*1000:.2f} mA")

    # Default parameters — caller doesn't have to pass everything
    def voltage_divider(vin, r1, r2, unit="V"):
        vout = vin * r2 / (r1 + r2)
        return f"{vout:.3f}{unit}"

    print(f"  Divider (5V, 10k, 10k) = {voltage_divider(5, 10000, 10000)}")
    print(f"  Divider (3.3V, 2k, 1k) = {voltage_divider(3.3, 2000, 1000)}")

    # Functions can return multiple values (actually returns a tuple)
    def analyze_signal(samples):
        return min(samples), max(samples), sum(samples)/len(samples)

    samples = [0.1, 0.8, -0.5, 1.0, 0.3]
    lo, hi, avg = analyze_signal(samples)
    print(f"  Signal: min={lo}, max={hi}, avg={avg:.2f}")

    # Lambda — tiny one-liner function (no def needed)
    to_mv = lambda v: v * 1000          # convert Volts to milliVolts
    print(f"  3.3V = {to_mv(3.3)} mV")


    # ─────────────────────────────────────────────────────────────
    # SECTION 5: CLASSES (Object-Oriented Programming)
    # ─────────────────────────────────────────────────────────────
    # A class is a blueprint. An object is a thing made from that blueprint.
    # EE: Class = schematic. Object = the actual PCB you manufactured.

    print("\\n--- SECTION 5: Classes (OOP) ---")

    class Sensor:
        """Represents a generic sensor on our system."""

        # __init__ runs when you create a new Sensor object
        def __init__(self, name, pin, units):
            self.name   = name      # self = "this object"
            self.pin    = pin
            self.units  = units
            self.readings = []      # empty list to store data

        def add_reading(self, value):
            """Record a new measurement."""
            self.readings.append(value)

        def average(self):
            """Calculate average of all readings."""
            if not self.readings:
                return None
            return sum(self.readings) / len(self.readings)

        def __repr__(self):
            """What gets printed when you print(sensor)."""
            return f"Sensor({self.name}, pin={self.pin}, {len(self.readings)} readings)"


    # Create two Sensor objects from the same class
    temp_sensor = Sensor("LM35-Temperature", pin=A0, units="°C") if False else Sensor("LM35-Temp", pin=0, units="degC")
    volt_sensor = Sensor("Voltage-Divider",  pin=1,  units="V")

    temp_sensor.add_reading(23.4)
    temp_sensor.add_reading(24.1)
    temp_sensor.add_reading(23.8)

    print(f"  {temp_sensor}")
    print(f"  Average temperature: {temp_sensor.average():.2f} {temp_sensor.units}")

    # Inheritance — a subclass that extends a parent class
    class TemperatureSensor(Sensor):
        """Specialized sensor with alarm threshold."""

        def __init__(self, name, pin, alarm_temp):
            super().__init__(name, pin, units="degC")  # call parent's __init__
            self.alarm_temp = alarm_temp

        def is_alarming(self):
            avg = self.average()
            return avg is not None and avg > self.alarm_temp

    motor_temp = TemperatureSensor("Motor-Winding", pin=2, alarm_temp=80.0)
    for t in [72, 78, 85, 91]:
        motor_temp.add_reading(t)
    print(f"  Motor avg: {motor_temp.average():.1f}°C, Alarming: {motor_temp.is_alarming()}")


    # ─────────────────────────────────────────────────────────────
    # SECTION 6: ERROR HANDLING
    # ─────────────────────────────────────────────────────────────
    # Things go wrong. Your code should handle it gracefully.
    # EE: like a protection circuit — don't let a fault crash everything.

    print("\\n--- SECTION 6: Error Handling ---")

    def safe_divide(a, b):
        try:
            result = a / b
        except ZeroDivisionError:
            print(f"  ERROR: cannot divide {a} by zero")
            return None
        except TypeError as e:
            print(f"  ERROR: wrong type — {e}")
            return None
        else:
            # runs only if NO exception occurred
            print(f"  {a} / {b} = {result:.4f}")
            return result
        finally:
            # runs ALWAYS, exception or not (like a finally-cleanup)
            pass   # could close a file or release hardware here

    safe_divide(10, 3)
    safe_divide(10, 0)
    safe_divide(10, "two")

    # Custom exception class
    class VoltageOutOfRange(Exception):
        pass

    def check_voltage(v):
        if v < 0 or v > 5:
            raise VoltageOutOfRange(f"{v}V is outside 0–5V range")
        return v

    for v in [3.3, -1.0, 12.0]:
        try:
            check_voltage(v)
            print(f"  {v}V: OK")
        except VoltageOutOfRange as e:
            print(f"  {v}V: FAULT — {e}")


    # ─────────────────────────────────────────────────────────────
    # SECTION 7: FILE I/O
    # ─────────────────────────────────────────────────────────────

    print("\\n--- SECTION 7: File I/O ---")

    import os, csv

    # Write a CSV file (comma-separated values — opens in Excel)
    data = [
        ["time_ms", "voltage_V", "current_mA"],
        [0,    3.30, 15.2],
        [100,  3.29, 15.1],
        [200,  3.31, 15.3],
        [300,  3.28, 14.9],
    ]

    os.makedirs("data", exist_ok=True)

    with open("data/measurements.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(data)
    print("  Wrote data/measurements.csv")

    # Read it back
    with open("data/measurements.csv", "r") as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"  Columns: {header}")
        for row in reader:
            print(f"    t={row[0]}ms  V={row[1]}V  I={row[2]}mA")

    # Write a plain text log file
    with open("data/log.txt", "w") as f:
        f.write("System boot\\n")
        f.write("ADC initialized\\n")
        f.write("Sensors online\\n")

    print("  Wrote data/log.txt")

    # JSON — great for configs and API data
    import json
    config = {"sample_rate": 1000, "channels": 4, "resolution": 12}
    with open("data/config.json", "w") as f:
        json.dump(config, f, indent=2)

    with open("data/config.json", "r") as f:
        loaded = json.load(f)
    print(f"  Config loaded: {loaded}")


    print("\\n" + "=" * 60)
    print("MODULE 1 COMPLETE")
    print("You now know: variables, lists, dicts, loops, functions, classes, files.")
    print("NEXT: python 2_data_analysis/numpy_pandas.py")
    print("=" * 60)
''')

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2a — NumPy & Pandas
# ─────────────────────────────────────────────────────────────────────────────
write("2_data_analysis/numpy_pandas.py", '''
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
    print("\\n--- PART A: NumPy ---")

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

    print(f"\\nzeros  = {zeros}")
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
    print(f"\\nMatrix shape: {matrix.shape}")  # (3, 3)
    print(f"Row 0: {matrix[0, :]}")           # first row
    print(f"Col 1: {matrix[:, 1]}")           # second column
    print(f"Element [1,2]: {matrix[1, 2]}")   # row 1, col 2

    # Matrix operations
    print(f"Transpose:\\n{matrix.T}")
    A = np.array([[1, 2], [3, 4]])
    B = np.array([[5, 6], [7, 8]])
    print(f"Matrix multiply A@B =\\n{A @ B}")   # @ is matrix multiply

    # Statistics with NumPy
    data = np.array([23.4, 24.1, 22.8, 25.0, 23.7, 24.5, 22.9])
    print(f"\\nTemperature readings: {data}")
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
    print(f"\\nSignal: {fs} samples, mean={np.mean(signal):.3f}, std={np.std(signal):.3f}")

    # FFT — see what frequencies are in the signal
    fft_vals = np.abs(np.fft.rfft(signal))
    freqs    = np.fft.rfftfreq(fs, 1/fs)
    peak_idx = np.argmax(fft_vals)
    print(f"  FFT peak at {freqs[peak_idx]:.1f} Hz  (should be ~10 Hz)")


    # ─────────────────────────────────────────────────────────────
    # PART B: PANDAS
    # ─────────────────────────────────────────────────────────────
    print("\\n--- PART B: Pandas ---")

    # Create a DataFrame (like a spreadsheet table)
    df = pd.DataFrame({
        "timestamp_ms": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900],
        "voltage_V":    [5.02, 5.01, 4.99, 5.00, 5.03, 4.98, 5.01, 5.00, 4.99, 5.02],
        "current_mA":   [10.1, 10.0, 10.2, 9.9, 10.3, 10.1, 9.8, 10.0, 10.1, 10.2],
        "temp_C":       [23.1, 23.2, 23.4, 23.5, 23.7, 23.9, 24.1, 24.2, 24.4, 24.5],
        "channel":      ["A","A","A","A","A","B","B","B","B","B"]
    })

    print("\\nRaw DataFrame:")
    print(df.to_string())

    print("\\n.describe() — automatic statistics on every numeric column:")
    print(df.describe().round(3))

    # Accessing columns and rows
    print(f"\\nAll voltages: {df['voltage_V'].values}")
    print(f"Row 0: {df.iloc[0].to_dict()}")
    print(f"Rows 2–4:\\n{df.iloc[2:5]}")

    # Filtering — like WHERE clause in SQL / filtering in Excel
    hot_rows = df[df["temp_C"] > 24.0]
    print(f"\\nRows where temp > 24°C:")
    print(hot_rows[["timestamp_ms","temp_C","channel"]])

    # Adding a computed column
    df["power_mW"] = df["voltage_V"] * df["current_mA"]
    print(f"\\nPower column added (V × I):")
    print(df[["timestamp_ms", "voltage_V", "current_mA", "power_mW"]])

    # GroupBy — split data by a category and aggregate
    # Like a pivot table in Excel
    print("\\nGroupBy channel:")
    grouped = df.groupby("channel").agg(
        avg_voltage=("voltage_V", "mean"),
        avg_current=("current_mA", "mean"),
        avg_temp=("temp_C", "mean"),
        samples=("timestamp_ms", "count")
    ).round(3)
    print(grouped)

    # Sort
    top3_power = df.sort_values("power_mW", ascending=False).head(3)
    print(f"\\nTop 3 highest power moments:")
    print(top3_power[["timestamp_ms", "power_mW"]])

    # Save and load CSV
    df.to_csv("data/measurements_pandas.csv", index=False)
    df_loaded = pd.read_csv("data/measurements_pandas.csv")
    print(f"\\nSaved and reloaded {len(df_loaded)} rows from CSV")

    # ─────────────────────────────────────────────────────────────
    # PART C: VISUALIZATION
    # ─────────────────────────────────────────────────────────────
    print("\\n--- PART C: Matplotlib Plots ---")

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

    print("\\n" + "=" * 60)
    print("MODULE 2a COMPLETE")
    print("You now know: NumPy arrays, Pandas DataFrames, plotting.")
    print("NEXT: python 2_data_analysis/statistics.py")
    print("=" * 60)
''')

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2b — Statistics
# ─────────────────────────────────────────────────────────────────────────────
write("2_data_analysis/statistics.py", '''
    """
    MODULE 2b: STATISTICS FOR ENGINEERS
    =====================================
    Statistics is how you UNDERSTAND data.
    Without it, you\'re just staring at numbers.

    EE Analogy: Statistics is like your signal analyzer.
    Instead of eyeballing a waveform, you get real measurements:
    noise floor, SNR, bandwidth, confidence intervals.

    We\'ll use a real-world scenario: you\'re analyzing power supply
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

    print("\\n--- SECTION 1: Descriptive Statistics ---")
    print("  (Summarizing what your data looks like)")
    print()
    print(f"  {'Revision':<8} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8} {'Median':>8}")
    print(f"  {'-'*52}")
    for rev, noise in revisions.items():
        print(f"  {rev:<8} {np.mean(noise):>7.2f}  {np.std(noise):>7.2f}  "
              f"{np.min(noise):>7.2f}  {np.max(noise):>7.2f}  {np.median(noise):>7.2f}")

    print("\\n  Units are mV of ripple on 3.3V rail")
    print("  Lower = better. Rev E is the quietest.")

    # ─────────────────────────────────────────────────────────────
    # SECTION 2: DISTRIBUTIONS & SPREAD
    # ─────────────────────────────────────────────────────────────
    print("\\n--- SECTION 2: Distributions ---")
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
    print(f"\\n  Percentiles of Rev D noise:")
    print(f"    P5  = {p5:.2f} mV  (5% of readings are below this)")
    print(f"    P25 = {p25:.2f} mV  (25th percentile / Q1)")
    print(f"    P50 = {p50:.2f} mV  (median)")
    print(f"    P75 = {p75:.2f} mV  (75th percentile / Q3)")
    print(f"    P95 = {p95:.2f} mV  (95% of readings are below this)")
    print(f"    IQR = {p75-p25:.2f} mV  (interquartile range = P75-P25)")

    # ─────────────────────────────────────────────────────────────
    # SECTION 3: CORRELATION
    # ─────────────────────────────────────────────────────────────
    print("\\n--- SECTION 3: Correlation ---")
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
    print("\\n--- SECTION 4: Hypothesis Testing (t-test) ---")
    print("  Question: Is Rev D's noise REALLY lower than Rev C?")
    print("  Or could this be sampling luck?")

    rev_c = revisions["Rev C"]
    rev_d = revisions["Rev D"]
    t_stat, p_value = stats.ttest_ind(rev_c, rev_d)

    print(f"\\n  Rev C mean noise: {np.mean(rev_c):.2f} mV")
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
    print("\\n--- SECTION 5: Full Correlation Matrix ---")

    df = pd.DataFrame({
        "temp_C":      temperature,
        "resistance_Ω": resistance,
        "battery_V":   battery_v,
        "current_mA":  50 - 0.1*temperature + np.random.randn(n)*2
    })

    corr_matrix = df.corr().round(3)
    print(corr_matrix)
    print("\\n  Read: strong positive = close to 1.0, strong negative = close to -1.0")
    print("  Diagonal is always 1.0 (a variable perfectly correlates with itself)")

    # ─────────────────────────────────────────────────────────────
    # VISUALIZE
    # ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Module 2b: Statistics", fontsize=14, fontweight="bold")

    # Box plots of noise by revision
    axes[0, 0].boxplot([revisions[r] for r in revisions], labels=list(revisions.keys()))
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
    print("\\n  Saved data/module2b_stats.png")

    print("\\n" + "=" * 60)
    print("MODULE 2b COMPLETE")
    print("You now know: distributions, std, correlation, hypothesis testing.")
    print("NEXT: python 3_machine_learning/ml_basics.py")
    print("=" * 60)
''')

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 — Machine Learning
# ─────────────────────────────────────────────────────────────────────────────
write("3_machine_learning/ml_basics.py", '''
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

    print("\\n--- PART A: Linear Regression ---")
    print("  Predict battery voltage from temperature and age (months).")

    n = 200
    temp_C  = np.random.uniform(5, 45, n)
    age_mo  = np.random.uniform(0, 36, n)
    # True relationship (we\'re pretending we don\'t know this)
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

    print(f"\\n  Learned coefficients:")
    print(f"    Intercept (base voltage): {model.intercept_:.4f} V")
    print(f"    Temperature coefficient:  {model.coef_[0]:.5f} V/°C  (should be ~-0.003)")
    print(f"    Age coefficient:          {model.coef_[1]:.5f} V/month (should be ~-0.015)")
    print(f"\\n  Performance on TEST set:")
    print(f"    MSE  = {mse:.6f}  (mean squared error — lower is better)")
    print(f"    RMSE = {np.sqrt(mse):.4f} V  (typical error per prediction)")
    print(f"    R²   = {r2:.4f}  (1.0 = perfect, 0.0 = no better than mean)")

    # Predict a new case
    new_battery = np.array([[35, 18]])   # 35°C, 18 months old
    pred_v = model.predict(new_battery)[0]
    print(f"\\n  Prediction: battery at 35°C, 18 months old → {pred_v:.3f} V")


    # ─────────────────────────────────────────────────────────────
    # PART B: CLASSIFICATION
    # ─────────────────────────────────────────────────────────────
    # Scenario: classify power supply faults from voltage + current readings.
    # 3 classes: Normal, Overcurrent, Undervoltage

    print("\\n--- PART B: Classification ---")
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

    print(f"\\n  {'Model':<25} {'Train Acc':>10} {'Test Acc':>10} {'CV Score':>10}")
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

    print(f"\\n  Best model: {best_name} with {best_acc:.1%} test accuracy")

    # Confusion matrix
    y_pred_cls = best_model.predict(X_te)
    labels = ["Normal", "Overcurrent", "Undervoltage"]
    cm = confusion_matrix(y_te, y_pred_cls, labels=labels)
    print(f"\\n  Confusion Matrix (rows=actual, cols=predicted):")
    print(f"  {'':20}", end="")
    for l in labels:
        print(f"  {l:>13}", end="")
    print()
    for i, row_label in enumerate(labels):
        print(f"  Actual {row_label:<13}", end="")
        for j, val in enumerate(cm[i]):
            print(f"  {val:>13}", end="")
        print()

    print("\\n  Diagonal = correct predictions. Off-diagonal = mistakes.")

    # Classification report
    print(f"\\n  Detailed Report:")
    print(classification_report(y_te, y_pred_cls, target_names=labels))

    # Predict a new reading
    new_reading = np.array([[4.1, 2.3]])  # low voltage, high current
    prediction  = best_model.predict(new_reading)[0]
    print(f"  New reading: V=4.1V, I=2.3A → Predicted fault: {prediction}")


    # ─────────────────────────────────────────────────────────────
    # PART C: THE ML PIPELINE (production-ready code)
    # ─────────────────────────────────────────────────────────────
    print("\\n--- PART C: sklearn Pipeline ---")
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
    print(f"\\n  Feature importances (Random Forest):")
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
    axes[0].set_title(f"Regression: Actual vs Predicted\\nR²={r2:.3f}")
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
    print("\\n  Saved data/module3_ml.png")

    print("\\n" + "=" * 60)
    print("MODULE 3 COMPLETE")
    print("You now know: regression, classification, evaluation, pipelines.")
    print("NEXT: python 4_neural_networks/waveform_classifier.py")
    print("=" * 60)
''')

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 — FIXED Neural Network Waveform Classifier
# ─────────────────────────────────────────────────────────────────────────────

write("4_neural_networks/network.py", '''
    """
    The NeuralNetwork class (shared between train.py and the API).
    Built from scratch using only NumPy.
    """
    import numpy as np

    def relu(x):          return np.maximum(0, x)
    def relu_grad(x):     return (x > 0).astype(float)
    def softmax(x):
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)

    class NeuralNetwork:
        """
        3-layer MLP: input_size → hidden1 → hidden2 → output_size
        Fixed from EE_AI_From_Scratch: larger network, cleaner data.
        """
        def __init__(self, input_size=50, hidden1=128, hidden2=64, output_size=3):
            self.W1 = np.random.randn(input_size, hidden1) * np.sqrt(2.0 / input_size)
            self.b1 = np.zeros((1, hidden1))
            self.W2 = np.random.randn(hidden1, hidden2) * np.sqrt(2.0 / hidden1)
            self.b2 = np.zeros((1, hidden2))
            self.W3 = np.random.randn(hidden2, output_size) * np.sqrt(2.0 / hidden2)
            self.b3 = np.zeros((1, output_size))
            self.cache = {}

        def forward(self, X):
            z1 = X @ self.W1 + self.b1;  a1 = relu(z1)
            z2 = a1 @ self.W2 + self.b2; a2 = relu(z2)
            z3 = a2 @ self.W3 + self.b3; a3 = softmax(z3)
            self.cache = dict(X=X, z1=z1, a1=a1, z2=z2, a2=a2, z3=z3, a3=a3)
            return a3

        def predict(self, X):
            return np.argmax(self.forward(X), axis=1)

        def param_count(self):
            return sum(w.size for w in [self.W1,self.b1,self.W2,self.b2,self.W3,self.b3])
''')

write("4_neural_networks/waveform_classifier.py", '''
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
    print("\\nGenerating training data...")

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
    print(f"\\nNetwork: 50→128→64→4  ({net.param_count():,} parameters)")
    print(f"Training {EPOCHS} epochs...")
    print(f"\\n{'Epoch':<8} {'Loss':<12} {'TrainAcc':<12} {'TestAcc'}")
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
    print(f"\\nFinal test accuracy: {final_acc:.1%}")

    # ─────────────────────────────────────────────────────────────
    # CONFUSION MATRIX
    # ─────────────────────────────────────────────────────────────
    label_names = ["Sine", "Square", "Triangle", "Noise"]
    y_pred = net.predict(X_te)
    cm = confusion_matrix(y_te, y_pred)
    print("\\nConfusion Matrix (rows=actual, cols=predicted):")
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
    fig.suptitle("Module 4: Fixed Waveform Classifier\\n"
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
        f"Final Test Accuracy: {final_acc:.1%}\\n\\n"
        f"Architecture:\\n  50 → 128 → 64 → 4\\n\\n"
        f"What was fixed:\\n"
        f"  • Square: np.sign(sin(t))\\n"
        f"  • Added Noise as class 3\\n"
        f"  • 500 samples/class (was 300)\\n"
        f"  • 1000 epochs (was 500)\\n"
        f"  • Bigger network (128,64)",
        transform=axes[1, 3].transAxes, fontsize=9,
        verticalalignment="top", family="monospace",
        bbox=dict(boxstyle="round", facecolor="#f0f4f8", alpha=0.8)
    )

    plt.tight_layout()
    plt.savefig("data/module4_classifier.png", dpi=120)
    print("  Saved data/module4_classifier.png")

    print("\\n" + "=" * 60)
    print("MODULE 4 COMPLETE")
    print(f"Model accuracy: {final_acc:.1%} (was ~85-90% with bugs)")
    print("Weights saved to data/ for the API server.")
    print("NEXT: python 5_software_engineering/clean_code.py")
    print("=" * 60)
''')

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5 — Software Engineering Principles
# ─────────────────────────────────────────────────────────────────────────────
write("5_software_engineering/clean_code.py", '''
    """
    MODULE 5: SOFTWARE ENGINEERING PRINCIPLES
    ==========================================
    Writing code that WORKS is step 1.
    Writing code that is MAINTAINABLE is step 2 (much harder).

    This module covers the principles that separate a junior
    engineer from a senior one.

    EE Analogy: Good code is like a well-designed PCB.
      - Clean code     = good silkscreen labels, no mystery test points
      - Functions      = modular subcircuits you can swap out
      - Tests          = production test fixtures
      - Documentation  = component datasheets inline
      - Version control= schematic revision history in git

    Topics:
      A) Clean Code Rules
      B) Writing Tests
      C) Git Workflow (concepts + commands)
      D) Debugging Strategies
      E) APIs and HTTP (for data engineering / AI engineering)
    """

    print("=" * 60)
    print("MODULE 5: SOFTWARE ENGINEERING")
    print("=" * 60)


    # ─────────────────────────────────────────────────────────────
    # PART A: CLEAN CODE
    # ─────────────────────────────────────────────────────────────
    print("\\n--- PART A: Clean Code Principles ---")

    # ── RULE 1: Names that explain themselves ────────────────────
    print("\\n  Rule 1: Use meaningful names")

    # BAD — what does this do?
    def calc(x, n, r):
        return x * (1 + r) ** n

    # GOOD — immediately clear
    def compound_interest(principal, years, annual_rate):
        """Calculate compound interest: P * (1 + r)^n"""
        return principal * (1 + annual_rate) ** years

    print(f"  compound_interest(1000, 5, 0.08) = £{compound_interest(1000, 5, 0.08):.2f}")

    # ── RULE 2: Functions do ONE thing ──────────────────────────
    print("\\n  Rule 2: Functions do one thing (Single Responsibility)")

    # BAD — loads data, processes it, AND saves results
    def do_everything(filepath):
        pass  # this function is too big, too hard to test/reuse

    # GOOD — each function has one clear job
    def load_sensor_data(filepath):
        """Load CSV and return DataFrame."""
        import pandas as pd
        return pd.read_csv(filepath)

    def compute_statistics(df, column):
        """Return dict of stats for a column."""
        import numpy as np
        return {
            "mean": df[column].mean(),
            "std":  df[column].std(),
            "min":  df[column].min(),
            "max":  df[column].max(),
        }

    def save_report(stats, output_path):
        """Write stats dict to text file."""
        with open(output_path, "w") as f:
            for k, v in stats.items():
                f.write(f"{k}: {v:.4f}\\n")

    # ── RULE 3: Don\'t repeat yourself (DRY) ─────────────────────
    print("\\n  Rule 3: DRY — Don\'t Repeat Yourself")

    # BAD
    def convert_5v_to_3v3():   return 5.0 * 3300 / (5000 + 3300)
    def convert_12v_to_5v():   return 12.0 * 5000 / (12000 + 5000)
    def convert_24v_to_12v():  return 24.0 * 12000 / (24000 + 12000)

    # GOOD — one function, parameterized
    def voltage_divider(v_in, r1_ohm, r2_ohm):
        """Voltage divider: V_out = V_in * R2 / (R1 + R2)"""
        return v_in * r2_ohm / (r1_ohm + r2_ohm)

    print(f"    5V → 3.3V:  {voltage_divider(5.0, 5000, 3300):.2f}V")
    print(f"    12V → 5V:   {voltage_divider(12.0, 12000, 5000):.2f}V")
    print(f"    24V → 12V:  {voltage_divider(24.0, 24000, 12000):.2f}V")

    # ── RULE 4: Avoid magic numbers ──────────────────────────────
    print("\\n  Rule 4: No magic numbers — use named constants")

    # BAD
    if 3.3 - 0.1 < 3.28 < 3.3 + 0.1:
        pass

    # GOOD
    NOMINAL_3V3  = 3.3       # Volts
    TOLERANCE_3V3 = 0.1      # ±100mV acceptable
    reading = 3.28

    if abs(reading - NOMINAL_3V3) < TOLERANCE_3V3:
        print(f"    {reading}V is within tolerance of {NOMINAL_3V3}V ±{TOLERANCE_3V3}V")

    # ── RULE 5: Handle errors explicitly ─────────────────────────
    print("\\n  Rule 5: Be explicit about errors")

    def read_adc(channel):
        """Read ADC channel. Raises ValueError for invalid channel."""
        if not 0 <= channel <= 7:
            raise ValueError(f"ADC channel must be 0-7, got {channel}")
        return 3.3 * channel / 7   # fake reading

    for ch in [0, 4, 9]:
        try:
            v = read_adc(ch)
            print(f"    ADC[{ch}] = {v:.3f} V")
        except ValueError as e:
            print(f"    ADC[{ch}] ERROR: {e}")


    # ─────────────────────────────────────────────────────────────
    # PART B: TESTING
    # ─────────────────────────────────────────────────────────────
    print("\\n--- PART B: Writing Tests ---")
    print("  Tests prove your code works. They also catch regressions")
    print("  (when a new change breaks old behavior).")

    # Manual test function (real projects use pytest — same idea)
    def assert_close(actual, expected, tolerance=1e-6, label=""):
        diff = abs(actual - expected)
        if diff <= tolerance:
            print(f"  ✓ PASS  {label}  (got {actual:.6f})")
        else:
            print(f"  ✗ FAIL  {label}  (expected {expected}, got {actual}, diff={diff})")

    def assert_equal(actual, expected, label=""):
        if actual == expected:
            print(f"  ✓ PASS  {label}")
        else:
            print(f"  ✗ FAIL  {label}  (expected {expected!r}, got {actual!r})")

    def assert_raises(func, args, exc_type, label=""):
        try:
            func(*args)
            print(f"  ✗ FAIL  {label}  (expected {exc_type.__name__}, no exception raised)")
        except exc_type:
            print(f"  ✓ PASS  {label}  ({exc_type.__name__} raised as expected)")
        except Exception as e:
            print(f"  ✗ FAIL  {label}  (wrong exception: {e})")

    print()
    # Test voltage_divider
    assert_close(voltage_divider(5.0, 5000, 5000), 2.5, label="50% divider")
    assert_close(voltage_divider(0.0, 1000, 1000), 0.0, label="zero input")
    assert_close(voltage_divider(10.0, 0, 1000),  10.0, label="r1=0 → passthrough")

    # Test compound_interest
    assert_close(compound_interest(100, 0, 0.1), 100.0, label="0 years → principal")
    assert_close(compound_interest(100, 1, 0.1), 110.0, label="10% for 1 year")

    # Test error handling
    assert_raises(read_adc, [9], ValueError, label="invalid ADC channel raises ValueError")


    # ─────────────────────────────────────────────────────────────
    # PART C: GIT WORKFLOW
    # ─────────────────────────────────────────────────────────────
    print("\\n--- PART C: Git Version Control ---")
    print("""
      Git saves every version of your code. Like schematic revision control
      but for code — you can always go back to any point.

      DAILY WORKFLOW:
      ─────────────────────────────────────────────────────────
      git status              # see what changed
      git diff                # see exact changes (line by line)
      git add filename.py     # stage a file for commit
      git add .               # stage ALL changes
      git commit -m "message" # save a snapshot with a description
      git log                 # see history
      git push origin main    # upload to GitHub

      BRANCHING (work on a feature without breaking main):
      ─────────────────────────────────────────────────────────
      git checkout -b feature/add-noise-class   # create + switch to new branch
      # ... make changes, commit ...
      git push origin feature/add-noise-class   # push branch to GitHub
      # Create a Pull Request on GitHub to merge into main

      GOOD COMMIT MESSAGES:
      ─────────────────────────────────────────────────────────
      BAD:  "fix stuff"
      BAD:  "update"
      GOOD: "Fix square wave generation — use np.sign() for crisp transitions"
      GOOD: "Add noise as 4th waveform class to prevent misclassification"
      GOOD: "Increase training epochs 500→1000, accuracy 88%→97%"

      Rule: the message should explain WHY, not just WHAT.
      The diff already shows WHAT changed.
    """)


    # ─────────────────────────────────────────────────────────────
    # PART D: DEBUGGING STRATEGIES
    # ─────────────────────────────────────────────────────────────
    print("--- PART D: Debugging Strategies ---")
    print("""
      EE analogy: debugging code = tracing a fault with a multimeter.
      You don\'t guess — you measure at each node until you find the fault.

      STRATEGY 1: Print statements (oscilloscope probe)
        Add print() to see exactly what each variable contains.
        Remove them once fixed.

      STRATEGY 2: Rubber duck debugging
        Explain your code line-by-line to someone (or a rubber duck).
        The act of explaining it forces you to see the mistake.

      STRATEGY 3: Bisect
        Comment out half the code. Does the bug still happen?
        Yes → bug is in the remaining half. Repeat.
        Like binary search for a fault.

      STRATEGY 4: Read the error message
        Python\'s error messages tell you exactly which line failed
        and what went wrong. Read ALL of the traceback, not just
        the last line.

      STRATEGY 5: Check your assumptions
        "I assume X is a list" — add print(type(X)) to verify.
        "I assume this loop runs 10 times" — add a counter and print it.

      COMMON PYTHON BUGS:
        - Off-by-one: range(5) gives 0,1,2,3,4 not 1,2,3,4,5
        - Mutable default args: def f(x=[]) is a trap, use x=None
        - = vs ==: assignment vs comparison
        - Integer division: 5/2 = 2.5, but 5//2 = 2
        - Shape mismatch in NumPy: (100,) != (100,1) — check .shape
    """)


    # ─────────────────────────────────────────────────────────────
    # PART E: APIs AND HTTP
    # ─────────────────────────────────────────────────────────────
    print("--- PART E: APIs and HTTP ---")
    print("""
      An API (Application Programming Interface) is how software
      talks to other software over a network.

      EE analogy: HTTP is like a UART protocol.
        - You send a request frame  (GET / POST)
        - You receive a response frame (200 OK / 404 Not Found)
        - Data is JSON (like a structured data packet)

      HTTP METHODS:
        GET    = read data         (like reading a register)
        POST   = send/create data  (like writing to a register)
        PUT    = update existing   (like overwriting a register)
        DELETE = remove data       (like clearing a register)

      HTTP STATUS CODES:
        200 OK          = success
        201 Created     = new resource created
        400 Bad Request = your request has an error (wrong data)
        401 Unauthorized= not logged in
        403 Forbidden   = logged in but not allowed
        404 Not Found   = resource doesn\'t exist
        500 Server Error= bug on the server side

      JSON FORMAT (the data format for APIs):
        {
          "sensor_id": "ADC_01",
          "voltage": 3.28,
          "timestamp": "2025-01-15T10:30:00Z",
          "status": "normal"
        }

      Using the requests library to call an API:
        import requests
        response = requests.get("https://api.example.com/sensors/1")
        data = response.json()     # parse JSON into a Python dict
        print(data["voltage"])     # access a field

      Our project (Module 6) implements a Flask API that
      classifies waveforms. The frontend calls /predict via HTTP POST.
    """)

    print("=" * 60)
    print("MODULE 5 COMPLETE")
    print("You now know: clean code, testing, git, debugging, APIs.")
    print("NEXT: python 6_full_project/app.py")
    print("=" * 60)
''')

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 6 — Full Project: Fixed Flask API + Frontend
# ─────────────────────────────────────────────────────────────────────────────
write("6_full_project/app.py", '''
    """
    MODULE 6: THE FULL PROJECT — FIXED API SERVER
    ===============================================
    This serves the fixed waveform classifier as a web API.
    It now correctly handles 4 classes: Sine, Square, Triangle, NOISE.

    Run:
        cd Learn_AI_Engineering
        python 4_neural_networks/waveform_classifier.py  # train first
        python 6_full_project/app.py                     # then start server

    Then open http://localhost:5000 in your browser.
    """
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
    import numpy as np
    import os, sys

    # Load our network class from Module 4
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), \'..\',"4_neural_networks"))
    from network import NeuralNetwork

    app = Flask(__name__)
    CORS(app)

    DATA_DIR     = os.path.join(os.path.dirname(__file__), \'..\', \'data\')
    FRONTEND_DIR = os.path.dirname(__file__)

    LABELS = {0: "Sine Wave", 1: "Square Wave", 2: "Triangle Wave", 3: "Random Noise"}

    def load_model():
        net = NeuralNetwork(input_size=50, hidden1=128, hidden2=64, output_size=4)
        for name in ["W1","b1","W2","b2","W3","b3"]:
            setattr(net, name, np.load(os.path.join(DATA_DIR, f"{name}.npy")))
        return net

    try:
        scaler_mean = np.load(os.path.join(DATA_DIR, "scaler_mean.npy"))
        scaler_std  = np.load(os.path.join(DATA_DIR, "scaler_std.npy"))
        model       = load_model()
        print("Model loaded. Server ready.")
    except FileNotFoundError:
        print("ERROR: No trained model found.")
        print("Run first: python 4_neural_networks/waveform_classifier.py")
        exit(1)


    @app.route("/")
    def home():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "online", "classes": list(LABELS.values())})

    @app.route("/predict", methods=["POST"])
    def predict():
        data = request.get_json()
        if not data or "signal" not in data:
            return jsonify({"error": "Send JSON with key \'signal\' containing 50 values"}), 400
        signal = np.array(data["signal"], dtype=float)
        if len(signal) != 50:
            return jsonify({"error": f"Expected 50 samples, got {len(signal)}"}), 400
        normalized = (signal - scaler_mean) / scaler_std
        probs      = model.forward(normalized.reshape(1, -1))[0]
        pred_class = int(np.argmax(probs))
        return jsonify({
            "prediction":   LABELS[pred_class],
            "class_id":     pred_class,
            "confidence":   round(float(probs[pred_class]) * 100, 1),
            "probabilities": {
                "sine":     round(float(probs[0]) * 100, 1),
                "square":   round(float(probs[1]) * 100, 1),
                "triangle": round(float(probs[2]) * 100, 1),
                "noise":    round(float(probs[3]) * 100, 1),
            }
        })

    @app.route("/demo")
    def demo():
        wt = request.args.get("type", "sine")
        t  = np.linspace(0, 2 * np.pi, 50)
        if   wt == "sine":     sig = np.sin(t).tolist()
        elif wt == "square":   sig = np.sign(np.sin(t)).tolist()
        elif wt == "triangle": sig = (2*np.abs(((t)/np.pi)%2-1)-1).tolist()
        elif wt == "noise":    sig = (np.random.randn(50)).tolist()
        else: return jsonify({"error": "type must be sine, square, triangle, or noise"}), 400
        return jsonify({"type": wt, "signal": sig})

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        print(f"Starting on http://localhost:{port}")
        app.run(host="0.0.0.0", port=port)
''')

# ─────────────────────────────────────────────────────────────────────────────
# Frontend HTML — updated for 4 classes
# ─────────────────────────────────────────────────────────────────────────────
write("6_full_project/index.html", """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Waveform AI — Fixed Classifier</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 2rem; }
    h1  { color: #38bdf8; font-size: 1.5rem; margin-bottom: 0.25rem; }
    h2  { color: #7dd3fc; font-size: 1rem; font-weight: normal; margin-bottom: 1.5rem; }
    .card { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.2rem; border: 1px solid #334155; }
    .card h3 { color: #38bdf8; margin-bottom: 0.8rem; }
    .btn-row { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1rem; }
    button { padding: 0.5rem 1.1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
    button:hover { opacity: 0.85; }
    .btn-sine     { background: #3b82f6; color: white; }
    .btn-square   { background: #ef4444; color: white; }
    .btn-triangle { background: #22c55e; color: white; }
    .btn-noise    { background: #a855f7; color: white; }
    .btn-predict  { background: #f59e0b; color: #0f172a; font-size: 1rem; padding: 0.65rem 1.8rem; }
    canvas { width: 100%; height: 150px; background: #0f172a; border-radius: 8px; border: 1px solid #334155; display: block; }
    .result-box { background: #0f172a; border-radius: 8px; padding: 1.2rem 1.5rem; border: 2px solid #334155; min-height: 70px; margin-top: 1rem; }
    .result-label { font-size: 1.6rem; font-weight: bold; color: #34d399; }
    .result-conf  { font-size: 0.9rem; color: #94a3b8; margin-top: 0.2rem; }
    .prob-bars { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.8rem; }
    .prob-row  { display: flex; align-items: center; gap: 0.6rem; }
    .prob-name { width: 75px; font-size: 0.8rem; color: #94a3b8; }
    .prob-bar-outer { flex: 1; height: 16px; background: #334155; border-radius: 4px; overflow: hidden; }
    .prob-bar-inner { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
    .prob-val { width: 45px; font-size: 0.8rem; text-align: right; color: #cbd5e1; }
    .fix-box  { background: #0c2336; border-left: 3px solid #22c55e; padding: 0.8rem 1rem; border-radius: 4px; font-size: 0.82rem; color: #86efac; margin-top: 0.8rem; }
    .status { font-size: 0.78rem; color: #64748b; margin-top: 0.4rem; }
    .step-list { list-style: none; }
    .step-list li { padding: 0.45rem 0; border-bottom: 1px solid #334155; font-size: 0.875rem; color: #94a3b8; }
    .step-list li span { color: #38bdf8; font-weight: bold; margin-right: 0.5rem; }
  </style>
</head>
<body>

<h1>Waveform AI Classifier — Fixed Version</h1>
<h2>Now correctly classifies 4 types: Sine · Square · Triangle · Noise</h2>

<div class="card">
  <h3>1. Load a Waveform</h3>
  <div class="btn-row">
    <button class="btn-sine"     onclick="load('sine')">Sine Wave</button>
    <button class="btn-square"   onclick="load('square')">Square Wave</button>
    <button class="btn-triangle" onclick="load('triangle')">Triangle Wave</button>
    <button class="btn-noise"    onclick="load('noise')">Random Noise</button>
  </div>
  <canvas id="scope"></canvas>
  <p class="status" id="sig-status">No signal loaded</p>
  <div class="fix-box">
    <strong>What was fixed:</strong> Square waves now use np.sign(sin(t)) — hard ±1 transitions.
    Random noise is now its own class (class 3), so the model no longer
    misclassifies noise as a waveform.
  </div>
</div>

<div class="card">
  <h3>2. Classify It</h3>
  <button class="btn-predict" onclick="predict()">Classify Signal →</button>
  <p class="status" id="api-status">Load a signal first</p>

  <div class="result-box" id="result-box">
    <div style="color:#475569; font-size:0.875rem;">Load a signal, then click Classify</div>
  </div>

  <div class="prob-bars" id="prob-bars" style="display:none;">
    <div class="prob-row"><span class="prob-name">Sine</span>
      <div class="prob-bar-outer"><div class="prob-bar-inner" id="bar-sine"     style="background:#3b82f6;width:25%"></div></div>
      <span class="prob-val" id="val-sine">-</span></div>
    <div class="prob-row"><span class="prob-name">Square</span>
      <div class="prob-bar-outer"><div class="prob-bar-inner" id="bar-square"   style="background:#ef4444;width:25%"></div></div>
      <span class="prob-val" id="val-square">-</span></div>
    <div class="prob-row"><span class="prob-name">Triangle</span>
      <div class="prob-bar-outer"><div class="prob-bar-inner" id="bar-triangle" style="background:#22c55e;width:25%"></div></div>
      <span class="prob-val" id="val-triangle">-</span></div>
    <div class="prob-row"><span class="prob-name">Noise</span>
      <div class="prob-bar-outer"><div class="prob-bar-inner" id="bar-noise"    style="background:#a855f7;width:25%"></div></div>
      <span class="prob-val" id="val-noise">-</span></div>
  </div>
</div>

<div class="card">
  <h3>3. Full Learning Path</h3>
  <ul class="step-list">
    <li><span>Module 1</span> Python basics — variables, functions, classes, file I/O</li>
    <li><span>Module 2a</span> NumPy &amp; Pandas — arrays, DataFrames, visualization</li>
    <li><span>Module 2b</span> Statistics — distributions, correlation, hypothesis testing</li>
    <li><span>Module 3</span> Machine Learning — regression, classification, evaluation</li>
    <li><span>Module 4</span> Neural Networks from scratch — fixed waveform classifier (97%+ accuracy)</li>
    <li><span>Module 5</span> Software Engineering — clean code, testing, git, APIs</li>
    <li><span>Module 6</span> Full project — this page!</li>
  </ul>
</div>

<script>
  const API = window.location.origin.startsWith('http') ? window.location.origin : 'http://localhost:5000';
  let signal = null;

  function draw(sig, color) {
    const canvas = document.getElementById('scope');
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth; canvas.height = 150;
    const W = canvas.width, H = canvas.height, pad = 20;
    const mn = Math.min(...sig), mx = Math.max(...sig), rng = mx - mn || 1;
    ctx.clearRect(0,0,W,H);
    ctx.strokeStyle='#1e3a5f'; ctx.lineWidth=1;
    for(let i=0;i<=4;i++){const y=pad+(H-2*pad)*i/4;ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(W-pad,y);ctx.stroke();}
    const zy=pad+(H-2*pad)*(mx/rng);
    ctx.strokeStyle='#475569';ctx.beginPath();ctx.moveTo(pad,zy);ctx.lineTo(W-pad,zy);ctx.stroke();
    ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();
    sig.forEach((v,i)=>{const x=pad+(W-2*pad)*i/(sig.length-1),y=pad+(H-2*pad)*(1-(v-mn)/rng);i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
    ctx.stroke();
    ctx.fillStyle=color;
    sig.forEach((v,i)=>{const x=pad+(W-2*pad)*i/(sig.length-1),y=pad+(H-2*pad)*(1-(v-mn)/rng);ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill();});
  }

  async function load(type) {
    const colors={sine:'#3b82f6',square:'#ef4444',triangle:'#22c55e',noise:'#a855f7'};
    try {
      const res=await fetch(`${API}/demo?type=${type}`);
      const data=await res.json();
      signal=data.signal; draw(signal,colors[type]);
      document.getElementById('sig-status').textContent=`${type} loaded — 50 samples`;
      document.getElementById('api-status').textContent='Signal ready. Click Classify →';
    } catch(e){ document.getElementById('sig-status').textContent='Cannot reach API. Is app.py running?'; }
  }

  async function predict() {
    if(!signal){document.getElementById('api-status').textContent='Load a signal first!';return;}
    document.getElementById('api-status').textContent='Running inference...';
    try {
      const res=await fetch(`${API}/predict`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signal})});
      const d=await res.json();
      document.getElementById('result-box').innerHTML=`<div class="result-label">${d.prediction}</div><div class="result-conf">Confidence: <strong>${d.confidence}%</strong></div>`;
      document.getElementById('prob-bars').style.display='flex';
      const p=d.probabilities;
      ['sine','square','triangle','noise'].forEach(k=>{
        document.getElementById(`bar-${k}`).style.width=p[k]+'%';
        document.getElementById(`val-${k}`).textContent=p[k]+'%';
      });
      document.getElementById('api-status').textContent='Done — model ran forward pass in <5ms';
    } catch(e){ document.getElementById('api-status').textContent='Error: is app.py running?'; }
  }
</script>
</body>
</html>
""")

# ─────────────────────────────────────────────────────────────────────────────
# README
# ─────────────────────────────────────────────────────────────────────────────
write("README.md", """
# Learn AI Engineering — Complete Beginner Course

## What This Teaches
| Area | Topics |
|------|--------|
| Python | Variables, functions, classes, error handling, file I/O |
| Data Analysis | NumPy arrays, Pandas DataFrames, Matplotlib, statistics |
| Machine Learning | Regression, classification, model evaluation, scikit-learn |
| Deep Learning | Neural networks from scratch, backpropagation, fixed waveform classifier |
| Software Engineering | Clean code, testing, git, debugging, APIs |

## Setup (run once)
```bash
pip install numpy pandas matplotlib scikit-learn flask flask-cors scipy
```

## Run the Modules In Order
```bash
python 1_python_basics/fundamentals.py
python 2_data_analysis/numpy_pandas.py
python 2_data_analysis/statistics.py
python 3_machine_learning/ml_basics.py
python 4_neural_networks/waveform_classifier.py   # trains the model
python 5_software_engineering/clean_code.py
python 6_full_project/app.py                      # open http://localhost:5000
```

## What Was Fixed (Waveform Classifier)
| Bug | Cause | Fix |
|-----|-------|-----|
| Square → Sine | Old: `np.where(sin>cos(duty))` → ambiguous near threshold | New: `np.sign(sin(t))` → hard ±1 |
| Noise → Triangle | Model never saw noise, forced to pick a class | Added Noise as class 3 |
| Low accuracy | Small network (64,32), only 300 samples, 500 epochs | 128,64 net, 500 samples, 1000 epochs |
""")

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("ALL FILES CREATED")
print("=" * 60)
print()
print("Install dependencies:")
print("  pip install numpy pandas matplotlib scikit-learn flask flask-cors scipy")
print()
print("Then run modules in order:")
print("  python 1_python_basics/fundamentals.py")
print("  python 2_data_analysis/numpy_pandas.py")
print("  python 2_data_analysis/statistics.py")
print("  python 3_machine_learning/ml_basics.py")
print("  python 4_neural_networks/waveform_classifier.py")
print("  python 5_software_engineering/clean_code.py")
print("  python 6_full_project/app.py   → open http://localhost:5000")
print()
print("=" * 60)
