from pathlib import Path

from ..runtime import state
from .detection import detect_asset
from .importer import ensure_assets_dir
from .paths import is_supported_asset_file


def scan_assets(root_dir):
    root = Path(root_dir)
    if not root.exists():
        return []

    assets = []
    seen = set()

    def visit(folder):
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if path.name == "asset.json":
                continue
            if path.is_file() and is_supported_asset_file(path):
                asset = detect_asset(path)
                if asset is not None and asset.id not in seen:
                    assets.append(asset)
                    seen.add(asset.id)
            elif path.is_dir():
                asset = detect_asset(path)
                if asset is not None:
                    if asset.id not in seen:
                        assets.append(asset)
                        seen.add(asset.id)
                    continue
                visit(path)

    visit(root)

    return assets


def assets_for_pack(pack_dir):
    if not ensure_assets_dir():
        return []
    pack_dir = Path(pack_dir).resolve()
    assets = []
    seen = set()

    for path in sorted(pack_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and is_supported_asset_file(path):
            asset = detect_asset(path)
            if asset is not None and asset.id not in seen:
                assets.append(asset)
                seen.add(asset.id)
        elif path.is_dir():
            asset = detect_asset(path)
            if asset is not None and asset.id not in seen:
                assets.append(asset)
                seen.add(asset.id)
                continue

            for nested in scan_assets(path):
                if nested.id not in seen:
                    assets.append(nested)
                    seen.add(nested.id)

    return assets


def asset_packs():
    if not ensure_assets_dir():
        return [("Root assets", state.ASSETS_DIR)]
    packs = [("Root assets", state.ASSETS_DIR)]
    packs.extend((path.name, path) for path in sorted(state.ASSETS_DIR.iterdir()) if path.is_dir())
    return packs


def gifs_for_pack(pack_dir):
    pack_dir = Path(pack_dir)
    if pack_dir == state.ASSETS_DIR:
        return sorted(path for path in state.ASSETS_DIR.glob("*.gif") if path.is_file())
    return sorted(path for path in pack_dir.glob("*.gif") if path.is_file())
