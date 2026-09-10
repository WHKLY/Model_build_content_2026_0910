# LRX Local Environment

Date checked: 2026-09-11

Project path:

`G:\a for HIT\project\Model_build_content_2026_0910`

## Operating System

- OS: Windows 10 / Windows NT 10.0.26200.0
- Architecture: 64-bit
- Shell used by Codex: PowerShell 7.6.4

## MWorks Installation

MWorks executables are not currently available from `PATH`.

Installed products found from Windows uninstall registry:

| Product | Version | Path evidence |
|---|---:|---|
| MWORKS.Syslab 2024a(x64) | 0.11.1 | `C:\Program Files\MWORKS\Syslab 2024a\Bin\syslab.exe` |
| MWORKS.Syslab 2026a(x64) | 26.1.2.6708 | registry entry exists; icon path points to Syslab 2024a |
| MWORKS.Sysplorer 2024a(x64) | 6.0.2.2701 | registry entry exists; recorded icon path was not present on disk |

Observed local Syslab directories:

- `C:\Program Files\MWORKS\Syslab 2024a\Docs`
- `C:\Program Files\MWORKS\Syslab 2024a\Examples`
- `C:\Program Files\MWORKS\Syslab 2024a\Bin`

The local Syslab examples mainly use `.jl` script files, so this project will use `.jl` for MWorks/Syslab scripts unless later testing proves another extension is required.

## Python and Conda

Python is not the primary project runtime. It may be used only as an auxiliary checker or file inspection tool.

- Default `python`: `C:\Users\27073\miniconda3\python.exe`
- Python version: 3.11.14
- Conda version: 25.9.1
- `CONDA_PREFIX`: not set in this shell
- `CONDA_DEFAULT_ENV`: not set in this shell

`conda info --envs` failed in the current Codex sandbox because Conda tried to probe CUDA virtual packages and hit `PermissionError: [WinError 5]`. This appears to be an environment-query issue, not a project dependency issue.

## CUDA

- `CUDA_PATH`: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0`
- `CUDA_PATH_V13_0`: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0`

CUDA is not expected to be needed for the deterministic LP model in question 1.

## Virtual Environment Decision

Do not create a Python virtual environment for this project at this stage.

Reasoning:

- The planned implementation language is MWorks/Syslab, not Python.
- Python is only auxiliary, so creating a Python venv would not isolate the real runtime risk.
- The main reproducibility risk is inconsistent MWorks/Syslab versions and syntax/API differences across teammates.
- If Python scripts are later introduced for verification or plotting, prefer recording the exact interpreter and package versions first, then decide whether a dedicated environment is necessary.

Recommended reproducibility rule:

Each teammate should add their own `env/<name>_env.md` with MWorks version, executable path, shell, OS, and any auxiliary Python/Excel environment they used.
