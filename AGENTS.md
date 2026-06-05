# AGENTS.md

FastBOM is an AIIS-flavored local desktop application. Treat it as a PySide6
operator console for BOM-driven engineering-file processing, SolidWorks COM
automation, DXF post-processing, and future remote API form submission.

## Project Shape

- Delivery shape: Qt / PySide6 desktop software, not a web app.
- Current entry point: `main.py`.
- Current production UI path: `gui/main_window.py` + `gui/worker_thread.py`.
- Current local business core: `core/bom_classifier.py`, `core/sw_converter.py`,
  and `core/dxf_processor.py`.
- The local BOM, SolidWorks, and DXF core has already been debugged and should
  be treated as stable during the first-stage configuration upgrade.
- Resource truth: SolidWorks templates live in `template/`; icons live in
  `static/`.
- Historical/demo code: `src/demo*.py`, `gui/gui.py`, and old helper scripts are
  reference material unless the user explicitly asks to revive them.

## AIIS Principles For This Repo

- Keep the human operator in control. Batch conversion, file writes, folder
  deletion, SolidWorks COM calls, and remote submissions must be explicit UI
  actions with clear status feedback.
- Let the system absorb workflow complexity. Prefer stable settings, defaults,
  validation, and logs over asking the operator to remember hidden rules.
- Separate the operator console from side effects. UI widgets collect intent;
  worker/service code performs long-running local work and remote requests.
- Treat files and API responses as contracts. Do not invent ad hoc mappings in
  the UI when a typed helper, service, or settings object is the real boundary.
- Keep AIIS grounding concrete. Changes should point back to PySide6 widgets,
  worker threads, SolidWorks COM lifecycle, DXF files, QSettings, API
  payloads, logs, or PyInstaller packaging.

## Engineering Boundaries

- `main.py` should stay thin: create `QApplication`, load settings/theme, create
  the main window, start the event loop.
- `gui/` owns widgets, page composition, signals, and presentation state.
- `gui/worker_thread.py` owns background execution glue for local long-running
  jobs. Do not block the UI thread with pandas, SolidWorks, DXF, filesystem, or
  HTTP work.
- `core/` owns deterministic local processing and SolidWorks/DXF behavior.
- Do not rewrite local core business logic during the settings upgrade. Only
  make small compatibility edits where settings must be injected into existing
  behavior.
- Future remote API code should live outside `MainWindow`, preferably in a
  small service/client module such as `services/remote_api.py`.
- Settings/config code lives in `config/settings.py`.
- Project-level tools belong in `tools/`; they should not silently depend on GUI
  state.

## UI Evolution Rules

- Do not keep adding more vertical "steps" to `MainWindow` once a new business
  page is introduced.
- For multiple workflows, prefer a sidebar plus `QStackedWidget` page model:
  local processing, remote form submission, and settings should be separate
  pages.
- The current local processing workflow lives in
  `gui/pages/local_processing_page.py` and is hosted by the page stack in
  `MainWindow`.
- New page modules should be small and named by workflow, for example
  `gui/pages/remote_form_page.py` and `gui/pages/settings_page.py`.
- When adding a primary page or a local-processing subpage, follow
  `docs/qt-navigation.md`.
- Long-running local workflow pages should keep logs visible, provide an
  explicit "save log" action, and open output folders only from an explicit
  operator action.
- Keep UI text practical and operator-facing. Avoid marketing language inside
  the application.
- Any remote API page must show request status, response summary, and error
  feedback without freezing the UI.

## Configuration Rules

- Desktop runtime settings should be saved through `QSettings`, Qt's standard
  settings mechanism. Do not add a backend-style environment configuration
  layer for the Qt client.
- Recommended precedence: built-in defaults < persisted QSettings values <
  current form input.
- Login-time settings own backend API base URL and request timeout.
- Main settings page candidates: default BOM columns, template directory,
  output folder names, SolidWorks visibility, DXF annotation parameters, and
  offline admin password.
- Do not expose theme editing in the settings page unless the user asks for a
  dedicated theme workflow.
- Do not add configurability for one-off values unless it supports real field
  deployment or repeated operator use.

## Remote API Contract Rules

- API URL, timeout, and authentication-related values must not be hard-coded in
  the page.
- Keep GET and POST payload construction in a service/client boundary. The UI
  should not manually concatenate URLs or serialize business payloads inline.
- Follow the AIIS response shape when this project controls the server contract:
  `{"code": 200, "message": "success", "data": ...}`.
- If the remote server uses a different contract, document the expected request
  and response shape in the service module and README.
- Read the backend `openapi.json` before implementing the remote form page or
  API client.
- Normal login credentials must come from the backend API.
- The offline `admin` username is fixed and must not be editable in the UI.
- Its local password may be stored in local Qt settings only for diagnostics or
  bootstrap. Do not write offline credentials to tracked files or logs.
- The backend's fallback highest-privilege account is not this `admin` account.
- If the Qt client logs in with offline `admin`, disable the remote form
  workflow for that session.
- Do not maintain long-lived mock APIs in the desktop app. Short-lived static
  samples are allowed only while the real endpoint is unavailable.

## Verification

Use the project runtime environment for project commands. This repository uses
`uv` and Python 3.13.

Minimum checks after docs-only changes:

```bash
uv run python -m compileall main.py config core gui utils build.py
```

For UI or worker changes, also start the app on a machine with the required GUI
runtime:

```bash
uv run python main.py
```

For SolidWorks conversion changes, verify on Windows with SolidWorks installed.
Do not claim the full conversion path is verified from macOS or from a machine
without SolidWorks.

For packaging changes, prefer:

```bash
uv run python build.py
```

If a command cannot be run because the host lacks Windows, SolidWorks, COM, or
GUI support, say that explicitly in the final report.

## Documentation Rules

- Keep `README.md` and `README.zh-CN.md` aligned with the real entry point,
  runtime, structure, and delivery shape.
- If the project moves from single-page workflow to sidebar/page navigation,
  update README and this file in the same change.
- If a local desktop pattern becomes reusable across AIIS projects, suggest
  extracting it as a Qt/PySide6 desktop skill, but do not create a shared skill
  unless the user asks for that step.
