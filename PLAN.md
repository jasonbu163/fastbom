# FastBOM Generalization Plan

> This plan is bilingual with `PLAN.zh-CN.md`. Keep both files aligned when the
> project direction changes.

**Goal:** Turn FastBOM from a working single-workflow desktop tool into a more
general AIIS-style local desktop application with configurable Qt settings,
clear page boundaries, and PMMS backend workflow support.

**Recommendation:** Starting with Qt application settings is the right first
stage. It reduces hard-coded assumptions before UI expansion, gives the future
remote API page a stable configuration source, and keeps the initial change
small enough to verify without touching the SolidWorks conversion path.

## Current Baseline

- Entry point: `main.py`.
- Current UI: one vertical PySide6 workflow in `gui/main_window.py`.
- Current local worker boundary: `gui/worker_thread.py`.
- Current business core: `core/bom_classifier.py`, `core/sw_converter.py`,
  `core/dxf_processor.py`.
- Current hard-coded values include theme, default BOM columns, output folder
  names, template path, SolidWorks visibility, and DXF annotation parameters.
- The local BOM, SolidWorks, and DXF business code has already been debugged and
  should be treated as stable during the first-stage generalization.
- Current delivery runtime is Windows + SolidWorks for full conversion
  verification; macOS can only verify docs, syntax, and pure Python structure.

## Target Architecture

```text
main.py
  loads settings/theme
  creates MainWindow

config/
  settings.py              # defaults and QSettings bridge

gui/
  main_window.py           # sidebar/page shell
  pages/
    local_processing_page.py
    residual_material_page.py
    user_management_page.py
    settings_page.py

services/
  remote_api.py            # backend auth, users, material specs, and inventory client

core/
  bom_classifier.py
  sw_converter.py
  dxf_processor.py
```

Keep `MainWindow` thin over time. UI pages collect operator intent; config and
service modules own runtime settings and external contracts; worker/core modules
perform long-running local side effects.

## Phase 1: Configuration And Settings Foundation

**Purpose:** Make the application configurable without changing the operator
workflow or adding the remote API page yet.

**Scope:**

- Add a settings module with built-in defaults and persisted user settings
  through `QSettings`.
- Move the safest hard-coded values into settings:
  - application theme;
  - default BOM part/material/quantity column names;
  - output folder names;
  - template directory;
  - SolidWorks visibility;
  - DXF text layer/color/default height/spacing;
  - inventory XLSX export filename prefix;
  - future backend API base URL and request timeout;
  - fallback admin username and fallback admin password in local Qt settings.
- Avoid changing local core business algorithms. Only touch `core/` where a
  small settings injection point is necessary to preserve existing behavior.
- Add a minimal settings UI if it can be done without restructuring the whole
  window; otherwise expose settings through the module first and defer the full
  settings page to Phase 2.
- Update README and AGENTS files when the settings contract lands.

**Recommended files:**

- Create: `config/__init__.py`.
- Create: `config/settings.py`.
- Modify: `main.py`.
- Modify: `gui/main_window.py`.
- Modify: `gui/worker_thread.py`.
- Modify only if needed for settings injection: `core/bom_classifier.py`.
- Modify only if needed for settings injection: `core/sw_converter.py`.
- Modify only if needed for settings injection: `core/dxf_processor.py`.
- Modify: `README.md`.
- Modify: `README.zh-CN.md`.
- Modify: `AGENTS.md`.
- Modify: `AGENTS.zh-CN.md`.

**Settings precedence:**

```text
built-in defaults < QSettings persisted values < current form input
```

**Acceptance criteria:**

- `main.py` no longer hard-codes the theme directly.
- Default BOM column names are loaded from the settings layer.
- Output folder names are loaded from the settings layer.
- `SWConverter` can use a configured template directory and SolidWorks
  visibility flag.
- `DXFProcessor` can use configured annotation values without changing its
  public behavior for default settings.
- Inventory XLSX export default filenames use a configurable prefix and local
  timestamp.
- Running with empty QSettings still behaves like the current application.
- Full SolidWorks conversion remains functionally unchanged when defaults are
  used.

**Verification:**

```bash
uv run python -m compileall main.py config core gui utils build.py
```

On macOS, `uv run` may fail before compile because `pywin32` is Windows-only.
In that case, use a read-only syntax check and state the platform limitation:

```bash
python3 -c "from pathlib import Path; paths=[Path('main.py'),Path('build.py'),*Path('config').glob('*.py'),*Path('core').glob('*.py'),*Path('gui').glob('*.py'),*Path('utils').glob('*.py')]; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in paths]; print(f'compiled {len(paths)} files')"
```

On Windows with SolidWorks installed:

```bash
uv run python main.py
```

Then verify the existing local workflow with a small BOM + `.SLDDRW` sample.

## Phase 2: Desktop Navigation And Settings Page

**Status:** Implemented for the current desktop shell. `MainWindow` now owns the
primary sidebar and page stack, while the local workflow lives in
`gui/pages/local_processing_page.py` with secondary navigation.

**Purpose:** Move from a single vertical workflow to a desktop application shell
that can hold multiple workflows.

**Scope:**

- Introduce a sidebar + `QStackedWidget`.
- Host the local processing workflow as the first page.
- Split local processing into secondary pages: preparation/detection,
  classification conversion, DXF annotation, and DXF merging.
- Add a settings page backed by the Phase 1 settings module.
- Keep the current local processing core behavior unchanged.

**Recommended files:**

- Create: `gui/pages/__init__.py`.
- Create: `gui/pages/local_processing_page.py`.
- Create: `gui/pages/settings_page.py`.
- Modify: `gui/main_window.py`.
- Modify: `main.py`.
- Create: `docs/qt-navigation.md`.

**Acceptance criteria:**

- The first screen still shows the local processing workflow.
- Local processing subpages are reachable from the secondary navigation.
- Long-running task pages expose save-log and open-output-directory actions.
- Settings can be viewed and saved from the UI.
- Saving settings writes through `QSettings`.
- The UI remains responsive during existing worker tasks.

## Phase 3: Backend Auth, Sheet Material Inventory, And User Management

**Status:** The generic remote form target has been narrowed into PMMS backend
integration pages. The current implementation includes backend login sessions,
sheet material inventory management, material specification management, user
management, paginated lists, XLSX import/export, and stock-in/consume inventory
actions.

**Purpose:** Move remote functionality from a demo form into field-usable PMMS
operator pages while keeping the UI separated from HTTP contracts.

**Scope:**

- Maintain the client contract from `pmms-integration-materials/`.
- Add backend-authenticated login and backend logout when the main window
  closes.
- Add the sheet material inventory page as the expanded concept that replaced
  the earlier residual-material-only workflow.
- Add the user management page for paginated backend accounts, creation,
  editing, disabling, and password updates.
- Keep HTTP request construction in `services/remote_api.py`.
- Use configured backend API base URL and timeout.
- Allow fallback `admin` login only from local Qt settings.
- Record that the backend's fallback highest-privilege account is not this
  `admin` account.
- Disable remote inventory and user-management workflows whenever the client
  session is force-logged in with fallback `admin`.
- Show request status, response summary, and error feedback in the UI.
- Use backend pagination for inventory lists, show all statuses by default, and
  support inventory-code, material-grade, and status filters.
- Manage material specifications separately from inventory; backend validation
  rejects changing key material/thickness fields after inventory references
  exist.
- Use the stock-in and consume actions for normal quantity movement. Quantity in
  the inventory edit dialog is only for manual ledger correction.
- XLSX import preview should expose created, updated, errors, used quantity, and
  added quantity.

**Recommended files:**

- Modify: `services/remote_api.py`.
- Create/modify: `gui/pages/residual_material_page.py`.
- Create/modify: `gui/pages/user_management_page.py`.
- Modify: `gui/main_window.py`.
- Modify: `config/settings.py`.
- Modify: `tests/test_remote_api.py`.
- Modify: `tests/test_residual_material_page_auth.py`.
- Modify: `tests/test_user_management_page.py`.

**Acceptance criteria:**

- Remote GET, POST, PATCH, and DELETE actions do not block the UI.
- URL and timeout are not hard-coded in the page.
- Normal credentials are obtained through the backend API contract.
- Fallback admin credentials are never stored in tracked files or displayed in
  logs/UI.
- Remote inventory and user-management actions are disabled for fallback admin
  sessions.
- The service module owns request construction and response parsing.
- Inventory pagination, filters, inventory-code lookup, import/export,
  stock-in, and consume workflows are usable.
- `consumed` displays as "exhausted" in the UI, can be restored through
  stock-in, and cannot be consumed again.
- User management creation, editing, disabling, and password management are only
  available to backend accounts with management permissions.
- README and BUILD document the remote inventory, material specification, and
  user-management operation and verification boundaries.

**Verification:**

```bash
uv run python -m compileall main.py config core gui utils build.py
uv run python -m unittest discover -s tests -p 'test_*.py'
```

During field integration, also log in with a backend account and verify
paginated refresh, material-spec maintenance, stock-in, consume, XLSX
import/export, and user management.

## Phase 4: AIIS Desktop Skill Candidate

**Purpose:** Decide whether this project has enough evidence to extract a
reusable AIIS Qt/PySide6 local desktop skill.

**Evidence to collect:**

- Settings layer works across local processing and remote API pages.
- Sidebar/page model supports at least two workflows.
- Worker-side local side effects remain separate from UI.
- Packaging and platform limitations are documented.

**Likely skill boundary:**

- PySide6 desktop shell structure.
- QSettings precedence.
- Worker thread rules for local side effects.
- Remote API service boundary.
- PyInstaller resource and platform checks.

Do not create the shared skill until the user explicitly asks for that step.

## Stage Gates

- **Gate 1:** Settings defaults work with empty QSettings.
- **Gate 2:** QSettings persistence is documented.
- **Gate 3:** Existing local workflow still works on Windows + SolidWorks.
- **Gate 4:** Sidebar/page split keeps the first screen useful.
- **Gate 5:** Remote PMMS pages use the settings/service boundary and pass
  inventory and user-management acceptance.
- **Gate 6:** Reusable desktop rules have enough evidence for a future skill.
