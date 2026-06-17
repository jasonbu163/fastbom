# PMMS 3.0 Windows Packaging Guide

This document describes how to package the PMMS 3.0 desktop client from this
FastBOM repository. The delivered application is a PySide6 Windows operator
console for BOM processing, SolidWorks COM conversion, DXF post-processing, and
remote material inventory workflows.

The release artifact must be built on Windows. macOS or Linux can run syntax
and UI smoke checks, but they cannot validate the SolidWorks COM path.

## Environment

- Windows 10 or Windows 11.
- Python 3.13.
- `uv` project environment.
- SolidWorks installed and licensed on the build and verification machine.
- Project dependencies installed with:

```bash
uv sync
```

The project declares Windows-only COM dependencies through `pywin32`; do not
install agent-only helper packages into the project `.venv`.

## Pre-Build Checks

Run the lightweight compile check first:

```bash
uv run python -m compileall main.py config core gui utils build.py
```

On a Windows machine with GUI support, also launch the desktop app:

```bash
uv run python main.py
```

Before a release build, verify the local processing workflow with a small BOM
and SolidWorks drawing set.

## Build Commands

The executable name, packaging name, window title, and version come from
`config/app_metadata.py`:

```python
APP_NAME = "PMMS"
APP_VERSION = "3.0"
WINDOW_TITLE = "生产物料管理系统"
```

Change those metadata constants first when the product name or displayed version
changes; `build.py` reads them instead of keeping a separate hard-coded product
name.

Default release build:

```bash
uv run python build.py
```

Debug build with a console window:

```bash
uv run python build.py --console
```

Folder-mode build, useful when diagnosing missing DLLs or data files:

```bash
uv run python build.py --onedir --console
```

Non-Windows smoke build, only for checking PyInstaller wiring:

```bash
uv run python build.py --allow-non-windows
```

Do not treat a non-Windows build as a release artifact.

## Output

With the current metadata, default one-file mode is:

```text
dist/
├── PMMS.exe
├── static/
└── template/
```

With the current metadata, folder mode is:

```text
dist/
└── PMMS/
    ├── PMMS.exe
    ├── static/
    └── template/
```

`template/` is copied beside the executable so the delivery package does not
depend on the source tree. Operators and support engineers should be able to
inspect or replace SolidWorks templates explicitly.

## Runtime Configuration

PMMS 3.0 uses Qt `QSettings` for desktop configuration:

- Login-time server URL and timeout are saved by the login dialog.
- Local workflow defaults and the inventory export filename prefix are edited
  from the settings page.
- Windows stores these values through the platform-native QSettings backend.

Do not write real passwords, tokens, customer IP addresses, or customer data
into tracked files or build documentation.

## Delivery Checklist

- Build on Windows with the same Python major/minor version used in development.
- Confirm `dist/PMMS.exe` or `dist/PMMS/PMMS.exe` exists.
- Confirm `template/` and `static/` are present in the delivery output.
- Start the executable on a clean Windows machine without source checkout.
- Login with a backend account when remote material inventory is required.
- Verify offline `admin` login still disables remote inventory actions.
- Verify sheet material inventory pagination, filtering, and inventory-code
  lookup.
- Verify material specification creation/editing and backend protection for
  specifications referenced by inventory.
- Verify stock-in and consume actions instead of replacing quantity movement
  with normal edits.
- Verify XLSX import preview, confirmed import, selected inventory export, and
  default filenames in the `<name>-YYYYMMDD-HHMMSS.xlsx` format.
- Verify an administrator account can open user management and create, edit, and
  disable users.
- Run a small BOM and SolidWorks drawing conversion.
- Verify generated DXF classification, annotation, and merge output folders.

## Common Failures

### PyInstaller Is Missing

Run:

```bash
uv sync
```

Then rerun:

```bash
uv run python build.py
```

### SolidWorks COM Fails

Check:

- SolidWorks is installed and licensed.
- Windows user permissions allow COM automation.
- The same Windows account can open SolidWorks normally.
- The build was not produced on macOS or Linux.

### Missing Module At Runtime

Use a debug build:

```bash
uv run python build.py --onedir --console
```

Read the console error and add only the specific missing module to
`hidden_imports()` in `build.py`.

### Resource Path Problems

Check that `template/` and `static/` exist beside the executable in `dist/`.
The packaged application must not rely on the source checkout current working
directory.

## Notes For Future Packaging Work

- Keep `BUILD.md` and `BUILD.zh-CN.md` synchronized.
- Keep `main.py` as the production packaging entry point.
- Do not package historical demos under `src/` as the delivery application.
- Do not make the build script mutate `requirements.txt`, `pyproject.toml`, or
  generated documentation.
