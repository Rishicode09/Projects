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
