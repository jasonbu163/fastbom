# FastBOM

FastBOM is a PySide6 desktop application for manufacturing engineering-file
workflows. It reads BOM spreadsheets, finds matching SolidWorks drawing files,
converts drawings to DXF through SolidWorks COM automation, classifies results
by material and thickness, and post-processes/merges DXF files for downstream
use.

This project is currently a local desktop operator tool, not a web application.
The historical NiceGUI demos under `src/` are retained as reference code; the
current application entry point is `main.py`.

## Current Workflow

The first screen is the local processing page inside a sidebar-based desktop
shell. A settings page is also available from the sidebar.

1. Select a project directory containing a BOM spreadsheet and `.SLDDRW` files.
2. Detect BOM files and spreadsheet headers.
3. Convert matching SolidWorks drawings to DXF and classify them into
   `result/1_分类结果`.
4. Add DXF annotations into `result/2_DXF处理结果`.
5. Merge DXF files by material and thickness into `result/3_合并文件`.

## Core Capabilities

- Intelligent BOM header detection, including headers that are not on the first
  row.
- Material/thickness parsing for values such as `A3板 T=10` and `A3板T=10`.
- Fuzzy matching between BOM part names and SolidWorks drawing filenames.
- Background worker execution to keep the Qt UI responsive.
- SolidWorks COM automation for template replacement, sheet-scale view setup,
  and DXF export.
- DXF annotation and material/thickness grouping with `ezdxf`.
- PyInstaller packaging support for Windows delivery.

## Technology

- Python 3.13, managed with `uv`.
- PySide6 for the desktop UI.
- `qt-material` for the current application theme.
- `pandas`, `openpyxl`, and `xlrd` for BOM spreadsheet processing.
- `pywin32` and `pythoncom` for SolidWorks COM integration on Windows.
- `ezdxf` for DXF processing.
- PyInstaller for executable packaging.

## Project Structure

```text
fastbom/
├── main.py                 # PySide6 application entry point
├── core/                   # Local processing and SolidWorks/DXF logic
│   ├── bom_classifier.py
│   ├── dxf_processor.py
│   ├── sw_converter.py
│   ├── file_export.py
│   ├── set_template.py
│   └── set_views.py
├── config/                 # Runtime defaults and QSettings bridge
│   └── settings.py
├── gui/                    # Desktop UI and worker-thread glue
│   ├── main_window.py
│   ├── pages/
│   │   ├── local_processing_page.py
│   │   └── settings_page.py
│   ├── worker_thread.py
│   └── gui.py              # Historical/reference UI path
├── utils/                  # Logging, message, and COM helper utilities
├── template/               # SolidWorks drawing templates and drafting standard
├── static/                 # Application icons and static resources
├── tools/                  # Project helper scripts and historical runners
├── src/                    # Historical NiceGUI/demo experiments
├── build.py                # PyInstaller packaging helper
├── BUILD.md                # English packaging notes
├── BUILD.zh-CN.md          # Chinese packaging notes
├── pyproject.toml
└── uv.lock
```

## Run Locally

Install dependencies with the project runtime environment:

```bash
uv sync
```

Start the desktop application:

```bash
uv run python main.py
```

SolidWorks conversion requires Windows with SolidWorks installed. The UI and
pure Python modules may be inspected elsewhere, but the COM conversion path
cannot be fully verified without that runtime.

## Lightweight Verification

For docs-only or structural changes:

```bash
uv run python -m compileall main.py config core gui utils build.py
```

For GUI changes, also launch the app:

```bash
uv run python main.py
```

For packaging changes:

```bash
uv run python build.py
```

## Configuration

FastBOM now has a dedicated settings layer in `config/settings.py`. It keeps
the current local workflow defaults while allowing UI settings to override
selected values through Qt's standard settings mechanism.

- `QSettings` is the desktop application's settings store.
- Qt chooses the platform-native backing store: Windows registry, macOS plist,
  and INI/config-style files on Linux.
- The login dialog owns backend API URL and request timeout, because those
  values are needed before the main window opens.
- The settings page edits local workflow defaults such as BOM columns, template
  directory, output folders, DXF parameters, SolidWorks visibility, and the
  offline admin password.
- The offline admin username is fixed as `admin`. Only its local password can
  be overwritten through `QSettings`; it must not be written to tracked files
  or logs.

Recommended precedence:

```text
built-in defaults < QSettings persisted user settings < current form input
```

## Remote API Authentication Direction

The remote API integration will be implemented after the backend `openapi.json`
is available. The Qt client should follow the backend contract instead of
inventing request or response shapes locally.

Authentication rules:

- Normal login credentials come from the backend API.
- The `admin` offline account is allowed only as an emergency/default login
  source from local Qt settings.
- The offline `admin` password may be stored by the desktop client in
  `QSettings`; it must not be written to tracked files or logs.
- The backend's fallback highest-privilege account is not this `admin` account.
- If the Qt client logs in with the offline `admin` identity, the remote
  form feature must be disabled for that session.
- Only a normal backend-authenticated user session may use the remote GET/POST
  form workflow.
- When the main window closes after a backend-authenticated login, the client
  should call backend logout with the current refresh token. Offline `admin`
  sessions do not call backend logout.
- If the offline password is forgotten, do not rebuild the app. Login with a
  backend non-admin account and reset the offline password from the settings
  page, or clear the local `QSettings` auth password key to fall back to the
  built-in default.

### Offline Admin Password Reset

The offline account is intentionally simple and local-only:

- Username is always `admin`; the UI must not allow renaming it.
- Built-in default password is `#456@admin`.
- The settings page only overwrites the local password when a new password is
  entered. Leaving the password field blank keeps the current value.
- Logging in as offline `admin` opens the desktop app but disables remote
  material-library features.

Reset paths:

- If the current offline password is known, login as `admin`, open Settings,
  enter a new offline password, and save.
- If the offline password is forgotten but a backend non-admin account is
  available, login with that backend account, open Settings, enter a new
  offline password, and save.
- If both offline login and backend login are unavailable, clear the local
  `QSettings` key `auth.fallback_admin_password`. On the next launch, the app
  falls back to the built-in `#456@admin` password. Rebuilding the software is
  not required.

## Local Core Stability

The local BOM, SolidWorks, and DXF processing code has already been debugged and
is known to run in the target environment. The first-stage generalization should
avoid changing core business algorithms unless a setting injection point
requires a small compatibility edit. Prefer wrapping configuration around the
existing behavior instead of rewriting local processing logic.

## UI Structure

`gui/main_window.py` now presents a primary sidebar card and a content card with
a page stack:

- Local processing page with secondary workflow navigation:
  preparation/detection, classification conversion, DXF annotation, and DXF
  merging.
- Settings page.

The remote API form page will be added after the backend `openapi.json` is
available.

Navigation extension rules are documented in `docs/qt-navigation.md`.

Keep HTTP request construction and parsing in a small service/client boundary
rather than embedding it in the main window.

## AIIS Notes

FastBOM is a good candidate for defining AIIS local desktop software rules:
PySide6 UI, worker-thread side effects, SolidWorks COM lifecycle, filesystem
contracts, user settings, remote API submission, and PyInstaller packaging all
appear in one concrete project.

See `AGENTS.md` for project-specific agent rules.
