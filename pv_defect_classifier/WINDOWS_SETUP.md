# Windows setup, start to finish

Written against the errors this project actually throws on a fresh Windows
machine, in the order they appear. If you downloaded the zip with the dataset
bundled, skip step 4 — it is already there.

Everything below assumes the project sits at `D:\pv_defect_classifier`. Change
the drive letter if yours differs.

---

## 1. Open the project in VS Code

Extract the zip, then **File → Open Folder** and pick `pv_defect_classifier`
(the folder containing `README.md`, not its parent). VS Code needs the project
root to find `configs/` and `src/`.

## 2. Make PowerShell willing to run the virtual environment

A fresh Windows install refuses the activation script:

```
Activate.ps1 cannot be loaded because running scripts is disabled on this system
```

That is the default execution policy, not a problem with the project. Allow
signed local scripts for your own user only:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

`CurrentUser` scope matters — it needs no administrator rights and does not
change the policy for anyone else on the machine.

## 3. Create the environment and install

```powershell
cd D:\pv_defect_classifier
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

You should see `(.venv)` at the start of your prompt. That is the environment
being active, not an error — it is what you want. To leave it later, type
`deactivate`.

Two things that bite here:

- **`pip install cv2` fails.** The import is named `cv2` but the package is
  `opencv-python`. `pip install -e ".[dev]"` already pulls the right one; you
  should not need to install it by hand.
- **`ModuleNotFoundError: No module named 'cv2'` after a successful install**
  usually means VS Code is running a different interpreter from the one you
  installed into. Press `Ctrl+Shift+P`, run **Python: Select Interpreter**, and
  choose the one inside `D:\pv_defect_classifier\.venv`.

## 4. Get the dataset

Only if your zip did not include `data\elpv-dataset\`. Check first:

```powershell
Test-Path D:\pv_defect_classifier\data\elpv-dataset\src\elpv_dataset\data\labels.csv
```

`True` means you are done — skip to step 5. If it prints `False`, and you have
git:

```powershell
git clone https://github.com/zae-bayern/elpv-dataset.git data\elpv-dataset
```

No git? Download it in a browser — <https://github.com/zae-bayern/elpv-dataset>
→ green **Code** button → **Download ZIP** — then extract it so the path above
exists. The folder must be named `elpv-dataset`; GitHub's zip unpacks to
`elpv-dataset-master`, so rename it.

Confirm it worked:

```powershell
python scripts\download_data.py
```

Expect `Found 2624 annotated cells`. Any other number means the folder layout
is wrong.

## 5. Check the install

```powershell
python -m pytest -q
```

98 tests, no dataset required, about 30 seconds.

If `pytest` alone gives `The term 'pytest' is not recognized`, the environment
is not active, or its `Scripts` folder is not on `PATH`. `python -m pytest`
works either way and is the safer habit.

## 6. Train

```powershell
python -m pvdefect.train --config configs\fast.yaml
```

Start with `fast.yaml` — about 9 minutes, and it proves the whole pipeline runs.
Its accuracy is deliberately not worth quoting; it is a smoke test.

Once that works:

```powershell
python -m pvdefect.train --config configs\default.yaml    # ~55 min on CPU
```

Training prints its own time estimate before it starts, measured on your
machine. If the figure is larger than you want to wait, read
`README.md` → "How long training takes" for what to change.

## 7. Analyse a module

```powershell
python scripts\analyse_module.py --cells path\to\cells\
```

The script needs one of `--cells` or `--module-image`; running it bare prints a
usage error listing both. It works without a trained model — it falls back to
an image-only estimator and says so.

---

## Things that are not errors

- **`(.venv)` in your prompt.** The environment is active. That is correct.
- **A warning that pretrained weights could not be downloaded.** Your network
  blocks `download.pytorch.org`. Training still runs, but from random weights,
  so the numbers are a pipeline test rather than a result.
- **`Perspective correction was skipped`.** The module outline was not found
  confidently in a whole-module photograph. Pass `--save-crops` and look at the
  crops before trusting the output.
