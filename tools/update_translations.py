import subprocess
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    app_dir = project_root / "openanima_app"
    i18n_dir = app_dir / "i18n"

    print("Starting source code scan...")

    py_files = [str(p) for p in app_dir.rglob("*.py")]

    if not py_files:
        print("Error: No Python files found.")
        sys.exit(1)

    print(f"Found {len(py_files)} Python files to process.")

    i18n_dir.mkdir(parents=True, exist_ok=True)

    # Automatically detect languages based on existing .ts files
    ts_files = list(i18n_dir.glob("*.ts"))

    # If no .ts files exist, stop execution with a helpful message
    if not ts_files:
        print(f"\nNo translation files (.ts) found in: {i18n_dir}")
        print(
            "To add a new language, please create a '<lang_code>.ts' file inside that directory."
        )
        print("Example: Create 'ru.ts' for Russian translation.")
        sys.exit(0)

    # Find the directory where the current Python executable is located (.venv/Scripts/)
    venv_bin_dir = Path(sys.executable).parent

    # Resolve absolute paths to the utilities based on the platform
    exe_suffix = ".exe" if sys.platform == "win32" else ""
    lupdate_path = str(venv_bin_dir / f"pyside6-lupdate{exe_suffix}")
    lrelease_path = str(venv_bin_dir / f"pyside6-lrelease{exe_suffix}")

    MINIMAL_TS_XML = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE TS>\n'
        '<TS version="2.1">\n'
        '</TS>\n'
    )

    # Process update and compilation workflows for each discovered language file
    for ts_file in sorted(ts_files):
        lang = ts_file.stem  # Gets the filename without extension (e.g., 'ru')
        qm_file = ts_file.with_suffix(".qm")

        # FIX: If the .ts file is completely empty (0 bytes), initialize it with valid XML structure
        if ts_file.exists() and ts_file.stat().st_size == 0:
            ts_file.write_text(MINIMAL_TS_XML, encoding="utf-8")
            print(f"[{lang.upper()}] Initialized empty file with base XML structure.")

        print(f"\n[{lang.upper()}] Processing translation files...")

        # 1. Execute pyside6-lupdate
        lupdate_cmd = [lupdate_path] + py_files + ["-ts", str(ts_file)]
        try:
            result = subprocess.run(lupdate_cmd, check=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout.strip())
            print(f"[{lang.upper()}] Updated: {ts_file.relative_to(project_root)}")
        except subprocess.CalledProcessError as e:
            print(f"Error during pyside6-lupdate execution for language '{lang}':")
            print(e.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"Error: '{lupdate_path}' not found. Is PySide6 installed in this venv?")
            sys.exit(1)

        # 2. Execute pyside6-lrelease
        lrelease_cmd = [lrelease_path, str(ts_file), "-qm", str(qm_file)]
        try:
            result = subprocess.run(lrelease_cmd, check=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout.strip())
            print(f"[{lang.upper()}] Compiled: {qm_file.relative_to(project_root)}")
        except subprocess.CalledProcessError as e:
            print(f"Error during pyside6-lrelease execution for language '{lang}':")
            print(e.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"Warning: '{lrelease_path}' not found. Compilation skipped.")

    print("\nAll translation tasks completed successfully.")


if __name__ == "__main__":
    main()