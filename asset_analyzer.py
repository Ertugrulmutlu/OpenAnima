import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QImageReader

from .assets import (
    SUPPORTED_IMAGE_EXTENSIONS,
    is_supported_frame_file,
    natural_key,
    unique_folder_path,
)


GIF_TYPE = "gif"
STATIC_IMAGE_TYPE = "static_image"
SPRITE_STRIP_TYPE = "sprite_strip"
SPRITESHEET_TYPE = "spritesheet"
FRAME_ANIMATION_TYPE = "frame_animation"
COMPOSITE_UI_TYPE = "composite_ui"

GIF_EXTENSIONS = {".gif"}
IMAGE_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS
COMMON_FRAME_COUNTS = (2, 3, 4, 5, 6, 8, 10, 12, 16, 24, 32)
COMMON_CELL_SIZES = (16, 24, 32, 48, 64, 96, 128)
COMMON_STRIP_FRAME_SIZES = (32, 48, 64, 96, 128, 160, 192, 256)
PREVIEW_TERMS = ("preview", "example", "sample")
UI_TERMS = ("hp", "health", "mana", "stamina", "energy", "bar", "fill", "base", "frame", "hud", "ui", "preview")


@dataclass
class AssetGuess:
    guessed_type: str
    confidence: float
    reasons: list[str]
    suggested_metadata: dict


class AssetAnalyzer:
    def analyze_path(self, path: Path) -> list[AssetGuess]:
        path = Path(path)
        if path.is_dir():
            return self.analyze_folder(path)
        if path.is_file():
            return self.analyze_file(path)
        return []

    def analyze_file(self, path: Path) -> list[AssetGuess]:
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix in GIF_EXTENSIONS:
            return [
                AssetGuess(
                    guessed_type=GIF_TYPE,
                    confidence=1.0,
                    reasons=["File extension is .gif."],
                    suggested_metadata={"type": GIF_TYPE, "image": path.name},
                )
            ]

        if suffix not in IMAGE_EXTENSIONS:
            return []

        size = _read_image_size(path)
        if size is None:
            return [
                AssetGuess(
                    guessed_type=STATIC_IMAGE_TYPE,
                    confidence=0.35,
                    reasons=["File extension is a supported image type, but dimensions could not be read."],
                    suggested_metadata={"type": STATIC_IMAGE_TYPE, "image": path.name},
                )
            ]

        width, height = size
        guesses: list[AssetGuess] = []
        static_confidence = 0.55
        static_reasons = [f"Image dimensions are {width}x{height}.", "Single image files can be used as static overlay assets."]

        if _has_preview_name(path):
            static_confidence = 0.35
            static_reasons.append("Filename suggests this may be a preview/example rather than the real asset.")

        guesses.append(
            AssetGuess(
                guessed_type=STATIC_IMAGE_TYPE,
                confidence=static_confidence,
                reasons=static_reasons,
                suggested_metadata={"type": STATIC_IMAGE_TYPE, "image": path.name},
            )
        )

        guesses.extend(_strip_guesses(path, width, height, "horizontal"))
        guesses.extend(_strip_guesses(path, width, height, "vertical"))

        sheet = _best_grid_guess(path, width, height)
        if sheet is not None:
            guesses.append(sheet)

        return _sort_guesses(guesses)

    def analyze_folder(self, path: Path) -> list[AssetGuess]:
        path = Path(path)
        guesses: list[AssetGuess] = []

        metadata_guess = _metadata_guess(path)
        if metadata_guess is not None:
            guesses.append(metadata_guess)

        image_files = sorted(
            (item for item in path.iterdir() if item.is_file() and is_supported_frame_file(item)),
            key=natural_key,
        )

        if len(image_files) >= 2:
            frame_guess = _frame_folder_guess(path, image_files)
            if frame_guess is not None:
                guesses.append(frame_guess)

            ui_guess = _composite_ui_guess(path, image_files)
            if ui_guess is not None:
                guesses.append(ui_guess)

        return _sort_guesses(guesses)


def create_asset_folder_from_guess(
    source_path: Path,
    target_assets_root: Path,
    guess: AssetGuess,
    asset_name: str,
) -> Path:
    source_path = Path(source_path).resolve()
    target_assets_root = Path(target_assets_root).resolve()
    target_assets_root.mkdir(parents=True, exist_ok=True)

    target = unique_folder_path(target_assets_root, _sanitize_asset_name(asset_name or source_path.stem or source_path.name))

    if source_path.is_dir():
        shutil.copytree(source_path, target)
    elif source_path.is_file():
        target.mkdir(parents=True, exist_ok=False)
        shutil.copy2(source_path, target / source_path.name)
    else:
        raise FileNotFoundError(source_path)

    metadata = dict(guess.suggested_metadata or {})
    if _should_write_metadata(guess):
        metadata.setdefault("type", guess.guessed_type)
        if source_path.is_file() and "image" not in metadata:
            metadata["image"] = source_path.name
        _write_metadata_safely(target / "asset.json", metadata)

    return target


def _metadata_guess(folder: Path) -> AssetGuess | None:
    metadata_path = folder / "asset.json"
    if not metadata_path.exists():
        return None

    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return AssetGuess(
            guessed_type="unknown",
            confidence=0.0,
            reasons=[f"Folder contains asset.json, but it could not be read: {exc}"],
            suggested_metadata={},
        )

    if not isinstance(data, dict):
        return AssetGuess(
            guessed_type="unknown",
            confidence=0.0,
            reasons=["Folder contains asset.json, but it is not a JSON object."],
            suggested_metadata={},
        )

    asset_type = str(data.get("type") or "unknown")
    return AssetGuess(
        guessed_type=asset_type,
        confidence=0.98 if asset_type != "unknown" else 0.4,
        reasons=["Folder contains existing asset.json metadata."],
        suggested_metadata=data,
    )


def _read_image_size(path: Path) -> tuple[int, int] | None:
    reader = QImageReader(str(path))
    size = reader.size()
    if not size.isValid():
        return None
    return size.width(), size.height()


def _strip_guesses(path: Path, width: int, height: int, direction: str) -> list[AssetGuess]:
    long_side = width if direction == "horizontal" else height
    short_side = height if direction == "horizontal" else width
    if short_side <= 0 or long_side / short_side < 3:
        return []

    candidates: list[tuple[float, int, int, list[str]]] = []
    for frames in COMMON_FRAME_COUNTS:
        if long_side % frames != 0:
            continue
        frame_size = long_side // frames
        if frame_size < 4:
            continue

        square_fit = max(0.0, 1.0 - abs(frame_size - short_side) / max(frame_size, short_side))
        common_bonus = 0.1 if frame_size in COMMON_CELL_SIZES else 0.0
        confidence = min(0.9, 0.74 + (square_fit * 0.12) + common_bonus)
        reasons = [
            f"Image aspect ratio is {long_side / short_side:.2f}:1 on the {direction} axis.",
            f"{long_side}px divides evenly into {frames} frames of {frame_size}px.",
        ]
        if square_fit >= 0.85:
            reasons.append("Candidate frame size is close to square.")
        if frame_size in COMMON_CELL_SIZES:
            reasons.append(f"Frame size {frame_size}px is a common pixel-art size.")

        candidates.append((confidence, frames, frame_size, reasons))

    for frame_size in COMMON_STRIP_FRAME_SIZES:
        if long_side % frame_size != 0:
            continue
        frames = long_side // frame_size
        if frames < 2:
            continue
        square_fit = max(0.0, 1.0 - abs(frame_size - short_side) / max(frame_size, short_side))
        exact_axis_bonus = 0.08 if frame_size == short_side else 0.0
        confidence = min(0.98, 0.78 + (square_fit * 0.12) + 0.08 + exact_axis_bonus)
        reasons = [
            f"{long_side}px divides evenly into common {frame_size}px frames.",
            f"That yields {frames} {direction} frames.",
        ]
        if square_fit >= 0.9:
            reasons.append("Frame size is close to the opposite image dimension.")
        candidates.append((confidence, frames, frame_size, reasons))

    by_frames = {}
    for candidate in sorted(candidates, key=lambda item: item[0], reverse=True):
        by_frames.setdefault(candidate[1], candidate)

    guesses = []
    for confidence, frames, frame_size, reasons in list(by_frames.values())[:3]:
        frame_width = frame_size if direction == "horizontal" else width
        frame_height = height if direction == "horizontal" else frame_size
        guesses.append(
            AssetGuess(
                guessed_type=SPRITE_STRIP_TYPE,
                confidence=confidence,
                reasons=reasons,
                suggested_metadata={
                    "type": SPRITE_STRIP_TYPE,
                    "image": path.name,
                    "direction": direction,
                    "frames": frames,
                    "frame_width": frame_width,
                    "frame_height": frame_height,
                    "fps": 8,
                    "crop_left": 0,
                    "crop_top": 0,
                    "crop_right": 0,
                    "crop_bottom": 0,
                    "trim_transparent": False,
                    "trim_padding": 0,
                    "anchor_x": 0.5,
                    "anchor_y": 0.9,
                },
            )
        )
    return guesses


def _best_grid_guess(path: Path, width: int, height: int) -> AssetGuess | None:
    candidates = []
    for cell_size in COMMON_CELL_SIZES:
        if width % cell_size != 0 or height % cell_size != 0:
            continue
        columns = width // cell_size
        rows = height // cell_size
        cell_count = columns * rows
        if cell_count < 2:
            continue
        confidence = 0.58
        if cell_count >= 4:
            confidence += 0.08
        if columns > 1 and rows > 1:
            confidence += 0.08
        candidates.append((min(confidence, 0.74), cell_size, columns, rows))

    if not candidates:
        return None

    confidence, cell_size, columns, rows = max(candidates, key=lambda item: (item[0], item[1]))
    return AssetGuess(
        guessed_type=SPRITESHEET_TYPE,
        confidence=confidence,
        reasons=[
            f"Image dimensions {width}x{height} divide evenly into {cell_size}px cells.",
            f"Grid would contain {columns} columns and {rows} rows.",
            "Grid sheets need manual frame or tile selection before they are safe to animate.",
        ],
        suggested_metadata={
            "type": SPRITESHEET_TYPE,
            "image": path.name,
            "frame_width": cell_size,
            "frame_height": cell_size,
            "note": "Needs animation frame selection",
        },
    )


def _frame_folder_guess(folder: Path, image_files: list[Path]) -> AssetGuess | None:
    dimensions: dict[tuple[int, int], list[Path]] = {}
    for image_file in image_files:
        size = _read_image_size(image_file)
        if size is not None:
            dimensions.setdefault(size, []).append(image_file)

    if not dimensions:
        return None

    best_size, matching_files = max(dimensions.items(), key=lambda item: len(item[1]))
    if len(matching_files) < 2:
        return None

    ordered_score = _ordered_filename_score(matching_files)
    confidence = 0.78 + (0.16 * ordered_score)
    reasons = [
        f"{len(matching_files)} images share dimensions {best_size[0]}x{best_size[1]}.",
        "Multiple same-size images can form a frame animation.",
    ]
    if ordered_score >= 0.7:
        reasons.append("Filenames look naturally ordered as animation frames.")

    return AssetGuess(
        guessed_type=FRAME_ANIMATION_TYPE,
        confidence=min(confidence, 0.94),
        reasons=reasons,
        suggested_metadata={"type": FRAME_ANIMATION_TYPE, "fps": 12},
    )


def _composite_ui_guess(folder: Path, image_files: list[Path]) -> AssetGuess | None:
    matched = [
        item.name
        for item in image_files
        if any(term in item.stem.lower() for term in UI_TERMS)
    ]
    if not matched:
        return None

    confidence = min(0.72, 0.48 + (len(matched) / max(1, len(image_files))) * 0.24)
    return AssetGuess(
        guessed_type=COMPOSITE_UI_TYPE,
        confidence=confidence,
        reasons=[
            f"{len(matched)} image filename(s) include UI/HUD terms.",
            "Composite UI assets need manual layer positioning.",
        ],
        suggested_metadata={
            "type": COMPOSITE_UI_TYPE,
            "name": folder.name,
            "layers": [],
            "note": "Layer positions need manual setup",
        },
    )


def _ordered_filename_score(paths: list[Path]) -> float:
    numbered = 0
    for path in paths:
        if re.search(r"(?:^|[_\-\s])(?:frame[_\-\s]?)?\d{1,4}(?:\D*$|$)", path.stem.lower()):
            numbered += 1
    return numbered / max(1, len(paths))


def _has_preview_name(path: Path) -> bool:
    stem = path.stem.lower()
    return any(term in stem for term in PREVIEW_TERMS)


def _sort_guesses(guesses: list[AssetGuess]) -> list[AssetGuess]:
    return sorted(guesses, key=lambda guess: guess.confidence, reverse=True)


def _sanitize_asset_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" ._")
    return sanitized or "asset"


def _should_write_metadata(guess: AssetGuess) -> bool:
    return bool(guess.suggested_metadata) and guess.guessed_type not in {GIF_TYPE, STATIC_IMAGE_TYPE}


def _write_metadata_safely(path: Path, metadata: dict) -> None:
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
