"""
File Path: /build.py
Description: PyInstaller packaging entry point for the PMMS desktop app.
Main Features:
    - Builds the PySide6 app from main.py
    - Reads product naming from config/app_metadata.py
    - Collects Windows/SolidWorks and Qt runtime dependencies
    - Copies operator-editable delivery resources into dist/
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from config.app_metadata import APP_NAME, APP_VERSION, WINDOW_TITLE


PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = "main.py"
ICON_PATH = Path("static/efficacy_researching_settings_icon_152066.ico")
RESOURCE_DIRS = ("template", "static")


class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

    @classmethod
    def print_header(cls, text: str) -> None:
        print(f"\n{cls.HEADER}{cls.BOLD}{'=' * 64}{cls.ENDC}")
        print(f"{cls.HEADER}{cls.BOLD}{text:^64}{cls.ENDC}")
        print(f"{cls.HEADER}{cls.BOLD}{'=' * 64}{cls.ENDC}\n")

    @classmethod
    def print_success(cls, text: str) -> None:
        print(f"{cls.OKGREEN}OK {text}{cls.ENDC}")

    @classmethod
    def print_info(cls, text: str) -> None:
        print(f"{cls.OKBLUE}INFO {text}{cls.ENDC}")

    @classmethod
    def print_warning(cls, text: str) -> None:
        print(f"{cls.WARNING}WARN {text}{cls.ENDC}")

    @classmethod
    def print_error(cls, text: str) -> None:
        print(f"{cls.FAIL}ERROR {text}{cls.ENDC}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME} {APP_VERSION} with PyInstaller.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--onefile", action="store_true", default=True, help=f"Build dist/{APP_NAME}.exe.")
    mode.add_argument("--onedir", action="store_true", help=f"Build dist/{APP_NAME}/{APP_NAME}.exe.")
    console = parser.add_mutually_exclusive_group()
    console.add_argument("--windowed", action="store_true", default=True, help="Hide console window.")
    console.add_argument("--console", action="store_true", help="Keep console window for debugging.")
    parser.add_argument("--optimize-size", action="store_true", help="Exclude common unused packages.")
    parser.add_argument("--skip-clean", action="store_true", help="Keep existing build/ and dist/.")
    parser.add_argument(
        "--allow-non-windows",
        action="store_true",
        help="Allow a non-Windows PyInstaller smoke build. Windows is required for release artifacts.",
    )
    args = parser.parse_args()
    if args.onedir:
        args.onefile = False
    if args.console:
        args.windowed = False
    return args


def validate_windows_target(allow_non_windows: bool) -> bool:
    if platform.system() == "Windows":
        return True
    message = (
        f"{APP_NAME} {APP_VERSION} release builds must be produced on Windows because SolidWorks "
        "COM and pywin32 are Windows-only. Use --allow-non-windows only for a "
        "local PyInstaller smoke check."
    )
    if allow_non_windows:
        Colors.print_warning(message)
        return True
    Colors.print_error(message)
    return False


def validate_project_structure() -> bool:
    Colors.print_info("Validating project structure...")
    required_paths = {
        "main.py": "application entry point",
        "config/settings.py": "settings model and QSettings bridge",
        "config/app_metadata.py": "application metadata",
        "auth/session.py": "login session model",
        "services/remote_api.py": "remote API client",
        "gui/login_dialog.py": "login dialog",
        "gui/main_window.py": "main window",
        "gui/pages/local_processing_page.py": "local processing page",
        "gui/pages/residual_material_page.py": "material inventory page",
        "gui/pages/settings_page.py": "settings page",
        "gui/worker_thread.py": "local workflow worker thread",
        "core/bom_classifier.py": "BOM classifier",
        "core/sw_converter.py": "SolidWorks converter",
        "core/dxf_processor.py": "DXF processor",
        "utils/platform_capabilities.py": "platform capability detection",
    }
    ok = True
    for relative_path, description in required_paths.items():
        if (PROJECT_ROOT / relative_path).exists():
            print(f"  OK {description}: {relative_path}")
        else:
            Colors.print_error(f"Missing {description}: {relative_path}")
            ok = False

    for resource_dir in RESOURCE_DIRS:
        path = PROJECT_ROOT / resource_dir
        if path.exists():
            count = sum(1 for item in path.rglob("*") if item.is_file())
            print(f"  OK resource directory: {resource_dir} ({count} files)")
        else:
            Colors.print_warning(f"Missing optional resource directory: {resource_dir}")
    return ok


def ensure_pyinstaller_available() -> bool:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        Colors.print_error("PyInstaller is not installed in the current project environment.")
        print("Install project dependencies first, for example:")
        print("  uv sync")
        return False
    Colors.print_success("PyInstaller is available in the current environment.")
    return True


def clean_build_outputs() -> None:
    Colors.print_info("Cleaning previous build outputs...")
    for relative_path in ("build", "dist"):
        path = PROJECT_ROOT / relative_path
        if path.exists():
            shutil.rmtree(path)
            print(f"  removed {relative_path}/")

    generated_spec = PROJECT_ROOT / f"{APP_NAME}.spec"
    if generated_spec.exists():
        generated_spec.unlink()
        print(f"  removed generated {generated_spec.name}")


def hidden_imports() -> list[str]:
    imports = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "auth",
        "auth.session",
        "config",
        "config.app_metadata",
        "config.settings",
        "core",
        "core.bom_classifier",
        "core.dxf_processor",
        "core.sw_converter",
        "gui",
        "gui.login_dialog",
        "gui.main_window",
        "gui.pages",
        "gui.pages.local_processing_page",
        "gui.pages.residual_material_page",
        "gui.pages.settings_page",
        "gui.worker_thread",
        "services",
        "services.auth_service",
        "services.remote_api",
        "utils",
        "utils.log",
        "utils.platform_capabilities",
        "utils.show",
        "utils.variant_helper",
        "openpyxl",
        "openpyxl.cell._writer",
    ]
    if platform.system() == "Windows":
        imports.extend(
            [
                "win32com.client",
                "win32com.client.gencache",
                "pythoncom",
                "pywintypes",
            ]
        )
    return imports


def data_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    qt_material_spec = importlib.util.find_spec("qt_material")
    if qt_material_spec is not None and qt_material_spec.origin:
        files.append((Path(qt_material_spec.origin).resolve().parent, "qt_material"))
    else:
        Colors.print_warning("qt-material is not installed; the packaged app will use Qt defaults.")

    for resource_dir in RESOURCE_DIRS:
        path = PROJECT_ROOT / resource_dir
        if path.exists():
            files.append((path, resource_dir))
    return files


def build_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--name",
        APP_NAME,
        "--onefile" if args.onefile else "--onedir",
        "--windowed" if args.windowed else "--console",
    ]

    if ICON_PATH.exists():
        command.extend(["--icon", str(ICON_PATH)])

    for package_name in ("numpy", "pandas", "ezdxf", "openpyxl"):
        command.extend(["--collect-all", package_name])

    for module_name in hidden_imports():
        command.extend(["--hidden-import", module_name])

    for source, destination in data_files():
        command.extend(["--add-data", f"{source}{os.pathsep}{destination}"])

    if args.optimize_size:
        for module_name in ("matplotlib", "scipy", "tkinter", "IPython", "jupyter", "notebook"):
            command.extend(["--exclude-module", module_name])

    command.append(MAIN_SCRIPT)
    return command


def run_pyinstaller(args: argparse.Namespace) -> bool:
    Colors.print_header(f"Building {APP_NAME} {APP_VERSION}")
    command = build_command(args)
    print("Command:")
    print("  " + " ".join(command))
    print()
    try:
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        Colors.print_error(f"PyInstaller failed with exit code {exc.returncode}.")
        return False
    return True


def copy_delivery_resources(onefile: bool) -> None:
    target_dir = PROJECT_ROOT / "dist" if onefile else PROJECT_ROOT / "dist" / APP_NAME
    if not target_dir.exists():
        Colors.print_warning(f"Expected output directory does not exist: {target_dir}")
        return

    Colors.print_info("Copying operator-editable delivery resources...")
    for resource_dir in RESOURCE_DIRS:
        source = PROJECT_ROOT / resource_dir
        if not source.exists():
            continue
        destination = target_dir / resource_dir
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        count = sum(1 for item in destination.rglob("*") if item.is_file())
        print(f"  OK {resource_dir}/ -> {destination.relative_to(PROJECT_ROOT)} ({count} files)")


def print_delivery_summary(onefile: bool) -> None:
    Colors.print_header("Build Output")
    if onefile:
        exe_path = PROJECT_ROOT / "dist" / f"{APP_NAME}.exe"
        print(f"Executable: {exe_path.relative_to(PROJECT_ROOT)}")
    else:
        exe_path = PROJECT_ROOT / "dist" / APP_NAME / f"{APP_NAME}.exe"
        print(f"Directory:  {Path('dist') / APP_NAME}")
        print(f"Executable: {exe_path.relative_to(PROJECT_ROOT)}")

    print()
    print("Minimum Windows smoke check:")
    print(f"  {exe_path}")
    print()
    print("Field-delivery notes:")
    print(f"  - Product: {WINDOW_TITLE} {APP_VERSION} ({APP_NAME}).")
    print("  - Build release artifacts on Windows with SolidWorks installed.")
    print("  - Keep template/ beside the exe so operators can inspect drawing templates.")
    print("  - Login-time server URL and local settings are stored through QSettings.")


def main() -> bool:
    args = parse_args()
    os.chdir(PROJECT_ROOT)

    Colors.print_header(f"{APP_NAME} {APP_VERSION} Packaging")
    if not validate_windows_target(args.allow_non_windows):
        return False
    if not validate_project_structure():
        return False
    if not ensure_pyinstaller_available():
        return False
    if not args.skip_clean:
        clean_build_outputs()
    if not run_pyinstaller(args):
        return False
    copy_delivery_resources(args.onefile)
    print_delivery_summary(args.onefile)
    Colors.print_success("Packaging completed.")
    return True


if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\nBuild cancelled.")
        sys.exit(1)
