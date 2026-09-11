# LRX Windows Python Environment

Date checked: 2026-09-11

Project path:

`G:\a for HIT\project\Model_build_content_2026_0910`

## Formal Runtime

- Operating system kernel: Microsoft Windows NT 10.0.26200.0, AMD64.
- Shell: PowerShell 7.6.5, started without loading a user profile for reproducible commands.
- Python: CPython 3.11.9, 64-bit.
- Virtual environment: `G:\a for HIT\project\Model_build_content_2026_0910\.venv`.
- Interpreter used for verification: `.venv\Scripts\python.exe`.
- pip: 24.0 inside `.venv`.

The default `python` command resolves to `C:\Users\27073\miniconda3\python.exe`, which did not contain SciPy during this review. The `py -3.11` installation had scientific packages but lacked the required Excel packages. Formal project commands therefore invoke `.venv\Scripts\python.exe` explicitly and do not depend on either global environment.

## Locked Direct Dependencies

Installed successfully from the repository `requirements.txt`:

| Package | Version |
|---|---:|
| numpy | 2.3.5 |
| scipy | 1.16.3 |
| pandas | 3.0.1 |
| matplotlib | 3.10.8 |
| openpyxl | 3.1.5 |
| xlsxwriter | 3.2.9 |

## Complete Pip Freeze

```text
contourpy==1.3.3
cycler==0.12.1
et_xmlfile==2.0.0
fonttools==4.65.0
kiwisolver==1.5.1
matplotlib==3.10.8
numpy==2.3.5
openpyxl==3.1.5
packaging==26.3
pandas==3.0.1
pillow==12.3.0
pyparsing==3.3.2
python-dateutil==2.9.0.post0
scipy==1.16.3
six==1.17.0
tzdata==2026.3
xlsxwriter==3.2.9
```

## Verified Commands

Run from the repository root in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\q1_main.py
.\.venv\Scripts\python.exe scripts\q1_certificate_verify.py --certificate output\question_1\certificate_q1.json --input original_source\附件\附件1.xlsx
```

The first clean install required a retry because the package download timed out. Re-running pip with a longer read timeout completed successfully without changing package versions.

## Scope

This is the formal Windows environment record for Question 1. MWorks/Syslab, Linux, and Termux are not used by the current Python build. The `.venv/` directory is local and ignored by Git; only this environment record and `requirements.txt` should be shared.
