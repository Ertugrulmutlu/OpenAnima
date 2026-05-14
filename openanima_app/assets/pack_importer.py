import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .analyzer import AssetAnalyzer
from .paths import is_inside_assets, unique_folder_path


@dataclass
class AssetPackImportResult:
    path: Path
    name: str
    author: str
    description: str
    detected_assets: list[str]


def import_asset_pack(source, assets_root):
    source = Path(source).resolve()
    assets_root = Path(assets_root).resolve()
    assets_root.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        return _import_folder_pack(source, assets_root)
    if source.is_file() and source.suffix.lower() == ".zip":
        return _import_zip_pack(source, assets_root)
    raise ValueError("Select a folder or .zip asset pack.")


def _import_folder_pack(source, assets_root):
    metadata = _read_pack_metadata(source)
    pack_name = str(metadata.get("name") or source.name)

    if is_inside_assets(source):
        target = source
    else:
        target = unique_folder_path(assets_root, pack_name)
        shutil.copytree(source, target)

    return _result_for_pack(target, metadata)


def _import_zip_pack(source, assets_root):
    if not zipfile.is_zipfile(source):
        raise ValueError("The selected file is not a readable zip archive.")

    target = unique_folder_path(assets_root, source.stem)
    target.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                member_path = Path(member.filename)
                if member.is_dir() or member_path.is_absolute() or ".." in member_path.parts:
                    continue
                archive.extract(member, target)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise

    metadata = _read_pack_metadata(target)
    preferred_name = str(metadata.get("name") or "").strip()
    if preferred_name and target.name != preferred_name:
        renamed = unique_folder_path(assets_root, preferred_name)
        target.rename(renamed)
        target = renamed

    return _result_for_pack(target, metadata)


def _read_pack_metadata(folder):
    for name in ("pack.json", "asset.json"):
        path = Path(folder) / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def _result_for_pack(folder, metadata):
    detected_assets = _detect_assets(folder, metadata)
    return AssetPackImportResult(
        path=Path(folder),
        name=str(metadata.get("name") or Path(folder).name),
        author=str(metadata.get("author") or ""),
        description=str(metadata.get("description") or ""),
        detected_assets=detected_assets,
    )


def _detect_assets(folder, metadata):
    listed = metadata.get("assets")
    if isinstance(listed, list):
        names = []
        for item in listed:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and item.get("path"):
                names.append(str(item.get("path")))
        if names:
            return names

    analyzer = AssetAnalyzer()
    detected = []
    for path in sorted(Path(folder).iterdir(), key=lambda item: item.name.lower()):
        if path.name in {"asset.json", "pack.json"}:
            continue
        guesses = analyzer.analyze_path(path)
        if guesses:
            best = guesses[0]
            detected.append(f"{path.name} ({best.guessed_type}, {best.confidence:.0%})")
    return detected
