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
print("\n--- PART A: Clean Code Principles ---")

# ── RULE 1: Names that explain themselves ────────────────────
print("\n  Rule 1: Use meaningful names")

# BAD — what does this do?
def calc(x, n, r):
    return x * (1 + r) ** n

# GOOD — immediately clear
def compound_interest(principal, years, annual_rate):
    """Calculate compound interest: P * (1 + r)^n"""
    return principal * (1 + annual_rate) ** years

print(f"  compound_interest(1000, 5, 0.08) = £{compound_interest(1000, 5, 0.08):.2f}")

# ── RULE 2: Functions do ONE thing ──────────────────────────
print("\n  Rule 2: Functions do one thing (Single Responsibility)")

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
            f.write(f"{k}: {v:.4f}\n")

# ── RULE 3: Don't repeat yourself (DRY) ─────────────────────
print("\n  Rule 3: DRY — Don't Repeat Yourself")

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
print("\n  Rule 4: No magic numbers — use named constants")

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
print("\n  Rule 5: Be explicit about errors")

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
print("\n--- PART B: Writing Tests ---")
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
print("\n--- PART C: Git Version Control ---")
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
  You don't guess — you measure at each node until you find the fault.

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
    Python's error messages tell you exactly which line failed
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
    404 Not Found   = resource doesn't exist
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
