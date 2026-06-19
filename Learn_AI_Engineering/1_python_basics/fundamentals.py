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

print("\n--- SECTION 1: Variables & Types ---")

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
print("\nString tricks:")
s = "Hello Engineer"
print(f"  upper()     : {s.upper()}")
print(f"  lower()     : {s.lower()}")
print(f"  split()     : {s.split()}")
print(f"  replace()   : {s.replace('Engineer', 'World')}")
print(f"  length      : {len(s)}")
print(f"  slice [0:5] : {s[0:5]}")   # grab first 5 characters

# Math operations
print("\nMath:")
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

print("\n--- SECTION 2: Lists & Dicts ---")

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
print(f"\ncomponent = {component}")
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

print("\n--- SECTION 3: Control Flow ---")

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
print("\n  Scanning I2C addresses:")
i2c_addresses = [0x48, 0x49, 0x4A, 0x4B]
for addr in i2c_addresses:
    print(f"    Polling address 0x{addr:02X}...")

# FOR with range() — like a classic C for-loop
print("\n  Counting with range:")
for i in range(0, 5):                       # 0, 1, 2, 3, 4
    print(f"    i = {i}", end="  ")
print()

# WHILE LOOP
print("\n  Waiting for ADC ready:")
adc_count = 0
adc_ready = False
while not adc_ready:
    adc_count += 1
    if adc_count >= 3:
        adc_ready = True
print(f"    ADC ready after {adc_count} polls")

# enumerate — gives (index, value) pairs
print("\n  enumerate example:")
sensors = ["temp", "pressure", "humidity"]
for i, name in enumerate(sensors):
    print(f"    sensor[{i}] = {name}")

# zip — iterate two lists together
print("\n  zip example:")
pins   = [14, 15, 16]
labels = ["SDA", "SCL", "INT"]
for pin, label in zip(pins, labels):
    print(f"    GPIO{pin} = {label}")


# ─────────────────────────────────────────────────────────────
# SECTION 4: FUNCTIONS
# ─────────────────────────────────────────────────────────────
# A function is a reusable block of code.
# EE: like a subcircuit — wire it once, reuse it anywhere.

print("\n--- SECTION 4: Functions ---")

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

print("\n--- SECTION 5: Classes (OOP) ---")

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

print("\n--- SECTION 6: Error Handling ---")

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

print("\n--- SECTION 7: File I/O ---")

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
    f.write("System boot\n")
    f.write("ADC initialized\n")
    f.write("Sensors online\n")

print("  Wrote data/log.txt")

# JSON — great for configs and API data
import json
config = {"sample_rate": 1000, "channels": 4, "resolution": 12}
with open("data/config.json", "w") as f:
    json.dump(config, f, indent=2)

with open("data/config.json", "r") as f:
    loaded = json.load(f)
print(f"  Config loaded: {loaded}")


print("\n" + "=" * 60)
print("MODULE 1 COMPLETE")
print("You now know: variables, lists, dicts, loops, functions, classes, files.")
print("NEXT: python 2_data_analysis/numpy_pandas.py")
print("=" * 60)
