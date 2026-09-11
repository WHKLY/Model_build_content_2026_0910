# LRX Termux Python Virtual Environment

Date checked: 2026-09-11

Project path:

`/data/data/com.termux/files/home/Project/Model_build_content_2026_0910`

## Purpose

This environment record documents the Python refactor environment after abandoning the MWorks/Syslab implementation. The virtual environment was used to run `python scripts/q1_main.py` successfully on 2026-09-11.

## Host Environment

- Runtime: Termux on Android
- Kernel: `Linux localhost 6.6.77-android15-8-gf9a1d4bd8353-abogki440974771-4k #1 SMP PREEMPT Fri Aug 29 01:48:34 UTC 2025 aarch64 Android`
- Shell used by Codex: `bash`
- UTC timestamp observed during setup: `Fri Sep 11 07:04:29 UTC 2026`

## Virtual Environment

- Venv path: `.venv/`
- Creation command: `python3 -m venv --system-site-packages .venv`
- Reason for `--system-site-packages`: Termux scientific packages are distributed through `pkg`; pip attempted to build NumPy/SciPy from source and did not complete promptly.
- `pyvenv.cfg` values observed after recreation:
  - `home = /data/data/com.termux/files/usr/bin`
  - `include-system-site-packages = true`
  - `version = 3.14.6`
  - `executable = /data/data/com.termux/files/usr/bin/python3.14`
  - `command = /data/data/com.termux/files/usr/bin/python3 -m venv --system-site-packages /data/data/com.termux/files/home/Project/Model_build_content_2026_0910/.venv`

## Installed Package Sources

Heavy scientific packages were installed with Termux `pkg`:

```bash
pkg install -y python-numpy python-scipy python-pandas matplotlib
```

Pure Python Excel packages were installed with pip inside `.venv`:

```bash
.venv/bin/python -m pip install openpyxl xlsxwriter
```

## Runtime Versions Used

```text
numpy==2.4.4
scipy==1.18.1
pandas==3.0.5
matplotlib==3.11.2
openpyxl==3.1.5
xlsxwriter==3.2.9
```

A full `pip freeze` capture is stored in:

`env/LRX_Termux_python_venv_pip_freeze.txt`

## Run Result

`python scripts/q1_main.py` completed successfully and generated CSV, XLSX, PNG, and SVG outputs under `output/question_1/`.
