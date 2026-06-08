import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def get_stats(ts_file_path):
    """Parses a single TS file and returns a dict with metrics, or None if failed."""
    path = Path(ts_file_path)
    if not path.exists():
        return None

    try:
        tree = ET.parse(path)
        root = tree.getroot()

        total = 0
        translated = 0
        unfinished = 0

        for message in root.iter("message"):
            translation = message.find("translation")

            if translation is not None:
                if translation.get("type") == "vanished":
                    continue

                total += 1

                if translation.get("type") == "unfinished":
                    unfinished += 1
                else:
                    translated += 1

        progress = (translated / total * 100) if total > 0 else 0.0
        
        # Check if the corresponding SVG icon exists in the same directory
        svg_file = path.with_suffix(".svg")
        has_icon = "Yes" if svg_file.exists() else "Missing"

        return {
            "file": path.name,
            "total": total,
            "translated": translated,
            "unfinished": unfinished,
            "progress": f"{progress:.2f}%",
            "icon": has_icon,
        }

    except (ET.ParseError, Exception):
        return None


def main():
    # Resolve project root path dynamically relative to this script location (tools/)
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    i18n_dir = project_root / "openanima_app" / "i18n"

    # Find all .ts files in the i18n directory
    ts_files = sorted(list(i18n_dir.glob("*.ts")))

    if not ts_files:
        print(f"No translation files (.ts) found in: {i18n_dir}")
        sys.exit(0)

    # Print table header
    print("-" * 85)
    print(
        f"{'File Name':<20} | {'Total':<8} | {'Translated':<12} | {'Unfinished':<10} | {'Progress':<10} | {'Icon':<7}"
    )
    print("-" * 85)

    # Process each file and print data row
    for ts_file in ts_files:
        stats = get_stats(ts_file)

        if stats:
            print(
                f"{stats['file']:<20} | "
                f"{stats['total']:<8} | "
                f"{stats['translated']:<12} | "
                f"{stats['unfinished']:<10} | "
                f"{stats['progress']:<10} | "
                f"{stats['icon']:<7}"
            )
        else:
            print(f"{ts_file.name:<20} | Error parsing file or file is empty.")

    print("-" * 85)


if __name__ == "__main__":
    main()