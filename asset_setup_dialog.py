import json
import copy
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImageReader, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .asset_analyzer import AssetGuess
from .asset_validation import validate_asset_metadata
from .assets import AssetType, SUPPORTED_IMAGE_EXTENSIONS, is_supported_frame_file, natural_key
from .metadata_renderers import CompositeUIRenderer
from .metadata_renderers import sprite_strip_crop_values, sprite_strip_frame_size, sprite_strip_frames_from_pixmap


ASSET_TYPES = [
    AssetType.STATIC_IMAGE,
    AssetType.GIF,
    AssetType.FRAME_ANIMATION,
    AssetType.SPRITE_STRIP,
    AssetType.SPRITESHEET,
    AssetType.COMPOSITE_UI,
]

PREVIEW_TERMS = ("preview", "sample", "example")
BASE_TERMS = ("hp bar", "base", "frame", "background", "bg")
HEALTH_TERMS = ("red", "health", "hp")
ENERGY_TERMS = ("blue", "mana", "mp", "energy")
STAMINA_TERMS = ("yellow", "stamina", "xp")
TEXT_EDIT_WIDGETS = (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox)


class CompositePreviewCanvas(QWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.pixmap = QPixmap()
        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self.dragging = False
        self.drag_offset = QPointF(0, 0)
        self.drag_started = False
        self.setMinimumSize(420, 360)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def set_pixmap(self, pixmap):
        self.pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw_checkerboard(painter)
        if self.pixmap.isNull():
            painter.setPen(QColor("#b8b8b8"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No readable layers")
            return

        self.update_transform()
        target = QRectF(
            self.offset.x(),
            self.offset.y(),
            self.pixmap.width() * self.scale,
            self.pixmap.height() * self.scale,
        )
        painter.drawPixmap(target, self.pixmap, QRectF(self.pixmap.rect()))
        self.draw_grid(painter, target)
        self.draw_all_bounds(painter)
        self.draw_selected_bounds(painter)

    def draw_checkerboard(self, painter):
        painter.fillRect(self.rect(), QColor("#202020"))
        cell = 12
        color_a = QColor("#2a2a2a")
        color_b = QColor("#343434")
        for y in range(0, self.height(), cell):
            for x in range(0, self.width(), cell):
                painter.fillRect(x, y, cell, cell, color_a if ((x // cell + y // cell) % 2 == 0) else color_b)

    def draw_grid(self, painter, target):
        if not self.dialog.show_grid_check.isChecked():
            return
        grid = max(1, round(16 * self.scale))
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        x = target.left()
        while x <= target.right():
            painter.drawLine(x, target.top(), x, target.bottom())
            x += grid
        y = target.top()
        while y <= target.bottom():
            painter.drawLine(target.left(), y, target.right(), y)
            y += grid

    def update_transform(self):
        if self.pixmap.isNull():
            return
        zoom = self.dialog.preview_zoom
        if zoom == "fit":
            self.scale = min(
                self.width() / max(1, self.pixmap.width()),
                self.height() / max(1, self.pixmap.height()),
                1.0,
            )
        else:
            self.scale = float(zoom)
        draw_width = self.pixmap.width() * self.scale
        draw_height = self.pixmap.height() * self.scale
        self.offset = QPointF((self.width() - draw_width) / 2, (self.height() - draw_height) / 2)

    def draw_selected_bounds(self, painter):
        index = self.dialog.selected_layer_index
        if index < 0 or index >= len(self.dialog.layers):
            return
        layer = self.dialog.layers[index]
        rect = self.layer_rect(layer)
        if rect is None:
            return
        scaled = QRectF(
            self.offset.x() + rect.x() * self.scale,
            self.offset.y() + rect.y() * self.scale,
            rect.width() * self.scale,
            rect.height() * self.scale,
        )
        painter.setPen(QPen(QColor("#ffdd55"), 2, Qt.SolidLine))
        painter.drawRect(scaled)
        painter.setPen(QPen(QColor("#111111"), 1, Qt.DotLine))
        painter.drawLine(scaled.left(), scaled.top(), scaled.right(), scaled.bottom())
        painter.drawLine(scaled.right(), scaled.top(), scaled.left(), scaled.bottom())
        painter.setPen(QPen(QColor("#ffdd55"), 1))
        painter.drawText(scaled.adjusted(4, -18, 240, 0), str(layer.get("name") or "layer"))

    def draw_all_bounds(self, painter):
        if not self.dialog.show_bounds_check.isChecked():
            return
        painter.setPen(QPen(QColor("#66c2ff"), 1, Qt.DashLine))
        for index, layer in enumerate(self.dialog.layers):
            if index == self.dialog.selected_layer_index or not layer.get("visible", True):
                continue
            rect = self.layer_rect(layer)
            if rect is None:
                continue
            painter.drawRect(
                QRectF(
                    self.offset.x() + rect.x() * self.scale,
                    self.offset.y() + rect.y() * self.scale,
                    rect.width() * self.scale,
                    rect.height() * self.scale,
                )
            )

    def layer_rect(self, layer):
        image = layer.get("image")
        if not image:
            return None
        image_path = self.dialog.source_path / image if self.dialog.source_path.is_dir() else self.dialog.source_path
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return None
        return QRectF(float(layer.get("x", 0)), float(layer.get("y", 0)), pixmap.width(), pixmap.height())

    def event_to_asset_point(self, event):
        if self.pixmap.isNull() or self.scale <= 0:
            return None
        point = event.position()
        return QPointF((point.x() - self.offset.x()) / self.scale, (point.y() - self.offset.y()) / self.scale)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        self.setFocus()
        point = self.event_to_asset_point(event)
        if point is None:
            return
        cycle = bool(event.modifiers() & (Qt.AltModifier | Qt.ControlModifier))
        index = self.dialog.layer_at_point(point, cycle=cycle)
        if index >= 0:
            self.dialog.select_layer(index)
            layer = self.dialog.layers[index]
            self.dragging = True
            self.drag_started = False
            self.drag_offset = QPointF(point.x() - float(layer.get("x", 0)), point.y() - float(layer.get("y", 0)))
        event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.dialog.selected_layer_index >= 0:
            point = self.event_to_asset_point(event)
            if point is None:
                return
            if not self.drag_started:
                self.dialog.push_undo_state("Move layer")
                self.drag_started = True
            x = round(point.x() - self.drag_offset.x())
            y = round(point.y() - self.drag_offset.y())
            self.dialog.set_selected_layer_position(x, y)
            event.accept()
            return

        point = self.event_to_asset_point(event)
        index = self.dialog.layer_at_point(point) if point is not None else -1
        if index >= 0:
            layer = self.dialog.layers[index]
            self.setToolTip(f"{layer.get('name', 'layer')}\n{layer.get('image', '')}\nx={layer.get('x', 0)}, y={layer.get('y', 0)}")
        else:
            self.setToolTip("")
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.drag_started = False
        return super().mouseReleaseEvent(event)

class AssetSetupDialog(QDialog):
    def __init__(self, source_path, guesses, existing_metadata=None, parent=None):
        super().__init__(parent)
        self.source_path = Path(source_path)
        self.guesses = guesses
        self.existing_metadata = existing_metadata or {}
        self.image_files = _image_files(self.source_path)
        self.layers = []
        self.selected_layer_index = -1
        self.selected_layer_id = None
        self.next_layer_id = 1
        self.layer_clipboard = None
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50
        self.dirty = False
        self._applying_history = False
        self._coalesce_key = None
        self.preview_zoom = "fit"
        self._loading = False

        self.setWindowTitle("Asset Setup")
        self.setMinimumSize(900, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.name_edit = QLineEdit(str(self.existing_metadata.get("name") or _default_name(self.source_path)))
        self.type_combo = QComboBox()
        self.type_combo.addItems(ASSET_TYPES)
        self.type_combo.currentTextChanged.connect(self.sync_type)
        self.configure_editor_field(self.name_edit)
        self.configure_editor_field(self.type_combo)
        top.addWidget(QLabel("Asset name"))
        top.addWidget(self.name_edit, 1)
        top.addWidget(QLabel("Type"))
        top.addWidget(self.type_combo)
        layout.addLayout(top)

        body = QSplitter(Qt.Horizontal)
        self.guess_list = QListWidget()
        self.guess_list.setMinimumWidth(220)
        self.guess_list.setMaximumWidth(320)
        self.guess_list.currentRowChanged.connect(self.select_guess)
        for guess in self.guesses:
            item = QListWidgetItem(f"{guess.guessed_type} ({guess.confidence:.0%})")
            item.setData(Qt.UserRole, guess)
            item.setToolTip(f"{guess.guessed_type} ({guess.confidence:.0%})")
            self.guess_list.addItem(item)
        body.addWidget(self.guess_list)

        self.stack = QStackedWidget()
        self.details_page = self.build_details_page()
        self.sprite_strip_page = self.build_sprite_strip_page()
        self.composite_page = self.build_composite_page()
        self.stack.addWidget(self.details_page)
        self.stack.addWidget(self.sprite_strip_page)
        self.stack.addWidget(self.composite_page)
        body.addWidget(self.stack)
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setSizes([240, 860])
        layout.addWidget(body, 1)

        self.status_label = QLabel("Shortcuts: arrows nudge, Shift+arrows x10, Ctrl+arrows x5, Delete remove, Ctrl+D duplicate, F fit, Ctrl +/- zoom.")
        self.status_label.setObjectName("SubtleLabel")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load_initial_state()

    def build_details_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.details_label = QLabel()
        self.details_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.details_label.setWordWrap(True)
        self.metadata_preview = QLabel()
        self.metadata_preview.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.metadata_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.details_label)
        layout.addWidget(self.metadata_preview, 1)
        return page

    def configure_editor_field(self, widget):
        widget.setMinimumHeight(30)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return widget

    def sprite_group(self, title):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(8)
        return group, layout

    def field_row(self, label_text, widget):
        row = QWidget()
        row.setMinimumHeight(34)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = QLabel(label_text)
        label.setMinimumWidth(120)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.configure_editor_field(widget)
        layout.addWidget(label)
        layout.addWidget(widget, 1)
        return row

    def label_row(self, label_text, value_label):
        row = QWidget()
        row.setMinimumHeight(30)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = QLabel(label_text)
        label.setMinimumWidth(120)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        value_label.setMinimumHeight(28)
        layout.addWidget(label)
        layout.addWidget(value_label, 1)
        return row

    def build_sprite_strip_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumWidth(300)
        splitter.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        self.strip_image_combo = QComboBox()
        self.strip_image_combo.addItems([path.name for path in self.image_files])
        self.strip_image_combo.currentTextChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_dimensions_label = QLabel()
        self.strip_frames_spin = QSpinBox()
        self.strip_frames_spin.setRange(1, 512)
        self.strip_frames_spin.setValue(1)
        self.strip_frames_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_direction_combo = QComboBox()
        self.strip_direction_combo.addItems(["horizontal", "vertical"])
        self.strip_direction_combo.currentTextChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_frame_width_spin = QSpinBox()
        self.strip_frame_width_spin.setRange(0, 4096)
        self.strip_frame_width_spin.setSpecialValueText("Auto")
        self.strip_frame_width_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_frame_height_spin = QSpinBox()
        self.strip_frame_height_spin.setRange(0, 4096)
        self.strip_frame_height_spin.setSpecialValueText("Auto")
        self.strip_frame_height_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_fps_spin = QSpinBox()
        self.strip_fps_spin.setRange(1, 60)
        self.strip_fps_spin.setValue(8)
        self.strip_loop_check = QCheckBox("Loop")
        self.strip_loop_check.setChecked(True)
        self.strip_crop_left_spin = QSpinBox()
        self.strip_crop_left_spin.setRange(0, 4096)
        self.strip_crop_left_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_crop_top_spin = QSpinBox()
        self.strip_crop_top_spin.setRange(0, 4096)
        self.strip_crop_top_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_crop_right_spin = QSpinBox()
        self.strip_crop_right_spin.setRange(0, 4096)
        self.strip_crop_right_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_crop_bottom_spin = QSpinBox()
        self.strip_crop_bottom_spin.setRange(0, 4096)
        self.strip_crop_bottom_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_trim_check = QCheckBox("Trim transparent pixels")
        self.strip_trim_check.toggled.connect(self.refresh_sprite_strip_preview)
        self.strip_trim_padding_spin = QSpinBox()
        self.strip_trim_padding_spin.setRange(0, 64)
        self.strip_trim_padding_spin.valueChanged.connect(self.refresh_sprite_strip_preview)
        self.strip_anchor_x_spin = QDoubleSpinBox()
        self.strip_anchor_x_spin.setRange(0.0, 1.0)
        self.strip_anchor_x_spin.setSingleStep(0.05)
        self.strip_anchor_x_spin.setValue(0.5)
        self.strip_anchor_y_spin = QDoubleSpinBox()
        self.strip_anchor_y_spin.setRange(0.0, 1.0)
        self.strip_anchor_y_spin.setSingleStep(0.05)
        self.strip_anchor_y_spin.setValue(0.9)

        source_group, source_layout = self.sprite_group("Source")
        source_layout.addWidget(self.field_row("Image", self.strip_image_combo))
        source_layout.addWidget(self.label_row("Dimensions", self.strip_dimensions_label))
        content_layout.addWidget(source_group)

        frames_group, frames_layout = self.sprite_group("Frames")
        frames_layout.addWidget(self.field_row("Frames", self.strip_frames_spin))
        frames_layout.addWidget(self.field_row("Direction", self.strip_direction_combo))
        frames_layout.addWidget(self.field_row("Frame width", self.strip_frame_width_spin))
        frames_layout.addWidget(self.field_row("Frame height", self.strip_frame_height_spin))
        frames_layout.addWidget(self.field_row("FPS", self.strip_fps_spin))
        self.strip_loop_check.setMinimumHeight(30)
        frames_layout.addWidget(self.strip_loop_check)
        content_layout.addWidget(frames_group)

        crop_group, crop_layout = self.sprite_group("Crop")
        crop_layout.addWidget(self.field_row("Crop left", self.strip_crop_left_spin))
        crop_layout.addWidget(self.field_row("Crop top", self.strip_crop_top_spin))
        crop_layout.addWidget(self.field_row("Crop right", self.strip_crop_right_spin))
        crop_layout.addWidget(self.field_row("Crop bottom", self.strip_crop_bottom_spin))
        self.strip_trim_check.setMinimumHeight(30)
        crop_layout.addWidget(self.strip_trim_check)
        crop_layout.addWidget(self.field_row("Trim padding", self.strip_trim_padding_spin))
        content_layout.addWidget(crop_group)

        anchor_group, anchor_layout = self.sprite_group("Anchor")
        anchor_layout.addWidget(self.field_row("Anchor X", self.strip_anchor_x_spin))
        anchor_layout.addWidget(self.field_row("Anchor Y", self.strip_anchor_y_spin))
        content_layout.addWidget(anchor_group)
        content_layout.addStretch()

        self.strip_frame_size_label = QLabel()
        self.strip_frame_size_label.setMinimumHeight(28)
        self.strip_warning_label = QLabel()
        self.strip_warning_label.setObjectName("SubtleLabel")
        self.strip_warning_label.setWordWrap(True)
        self.strip_preview = QLabel()
        self.strip_preview.setFrameShape(QFrame.StyledPanel)
        self.strip_preview.setAlignment(Qt.AlignCenter)
        self.strip_preview.setMinimumSize(320, 240)
        self.strip_preview_scroll = QScrollArea()
        self.strip_preview_scroll.setWidgetResizable(False)
        self.strip_preview_scroll.setMinimumHeight(300)
        self.strip_preview_scroll.setMinimumWidth(320)
        self.strip_preview_scroll.setFrameShape(QFrame.StyledPanel)
        self.strip_preview_scroll.setWidget(self.strip_preview)
        export_button = QPushButton("Export Frames")
        export_button.setMinimumHeight(32)
        export_button.clicked.connect(self.export_sprite_strip_frames)

        preview_group, preview_layout = self.sprite_group("Preview")
        preview_group.setMinimumWidth(340)
        preview_layout.addWidget(self.strip_frame_size_label)
        preview_layout.addWidget(self.strip_warning_label)
        preview_layout.addWidget(self.strip_preview_scroll, 1)
        preview_layout.addWidget(export_button, 0, Qt.AlignLeft)
        splitter.addWidget(preview_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([540, 420])
        return page

    def build_composite_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(12)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        self.preview_combo = QComboBox()
        self.preview_combo.addItem("")
        self.preview_combo.addItems([path.name for path in self.image_files])
        self.preview_combo.currentTextChanged.connect(self.refresh_composite_preview)
        left_layout.addWidget(QLabel("Preview image"))
        left_layout.addWidget(self.preview_combo)

        self.layer_list = QListWidget()
        self.layer_list.currentRowChanged.connect(self.select_layer)
        self.layer_list.setFocusPolicy(Qt.StrongFocus)
        self.layer_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.layer_list.setDefaultDropAction(Qt.MoveAction)
        self.layer_list.model().rowsMoved.connect(self.layer_rows_moved)
        self.layer_list.installEventFilter(self)
        left_layout.addWidget(QLabel("Layers (bottom to top)"))
        left_layout.addWidget(self.layer_list, 1)

        actions = QGridLayout()
        for index, (label, handler) in enumerate(
            (
                ("Add Layer", self.add_empty_layer),
                ("Remove Layer", self.remove_selected_layer),
                ("Copy", self.copy_selected_layer),
                ("Paste", self.paste_layer),
                ("Duplicate", self.duplicate_selected_layer),
                ("Up", lambda: self.move_selected_layer(-1)),
                ("Down", lambda: self.move_selected_layer(1)),
                ("To Front", self.bring_selected_to_front),
                ("To Back", self.send_selected_to_back),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            actions.addWidget(button, index // 2, index % 2)
        left_layout.addLayout(actions)
        layout.addWidget(left, 0)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        preview_controls = QHBoxLayout()
        for label, zoom in (("Fit", "fit"), ("100%", 1.0), ("200%", 2.0)):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, value=zoom: self.set_preview_zoom(value))
            preview_controls.addWidget(button)
        zoom_out = QPushButton("Zoom Out")
        zoom_in = QPushButton("Zoom In")
        refresh = QPushButton("Refresh Preview")
        zoom_out.clicked.connect(lambda: self.zoom_preview(0.8))
        zoom_in.clicked.connect(lambda: self.zoom_preview(1.25))
        refresh.clicked.connect(self.refresh_composite_preview)
        preview_controls.addWidget(zoom_out)
        preview_controls.addWidget(zoom_in)
        preview_controls.addWidget(refresh)
        self.show_bounds_check = QCheckBox("Show bounds")
        self.show_bounds_check.setChecked(True)
        self.show_bounds_check.toggled.connect(self.refresh_composite_preview)
        self.show_grid_check = QCheckBox("Grid")
        self.show_grid_check.toggled.connect(self.refresh_composite_preview)
        self.snap_grid_check = QCheckBox("Snap")
        preview_controls.addWidget(self.show_bounds_check)
        preview_controls.addWidget(self.show_grid_check)
        preview_controls.addWidget(self.snap_grid_check)
        preview_controls.addStretch()
        center_layout.addLayout(preview_controls)
        self.composite_preview = CompositePreviewCanvas(self)
        self.composite_preview.installEventFilter(self)
        center_layout.addWidget(self.composite_preview, 1)
        layout.addWidget(center, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.properties_title = QLabel("Layer Properties")
        self.properties_title.setObjectName("SectionTitle")
        right_layout.addWidget(self.properties_title)
        form = QFormLayout()
        self.layer_name_edit = QLineEdit()
        self.layer_name_edit.textEdited.connect(self.properties_changed)
        self.layer_image_combo = QComboBox()
        self.layer_image_combo.addItems([path.name for path in self.image_files])
        self.layer_image_combo.currentTextChanged.connect(self.properties_changed)
        self.layer_role_combo = QComboBox()
        self.layer_role_combo.addItems(["normal", "base", "health", "mana", "stamina"])
        self.layer_role_combo.currentTextChanged.connect(self.role_changed)
        self.layer_x_spin = QSpinBox()
        self.layer_x_spin.setRange(-10000, 10000)
        self.layer_x_spin.valueChanged.connect(self.properties_changed)
        self.layer_y_spin = QSpinBox()
        self.layer_y_spin.setRange(-10000, 10000)
        self.layer_y_spin.valueChanged.connect(self.properties_changed)
        self.layer_visible_check = QCheckBox("Visible")
        self.layer_visible_check.toggled.connect(self.properties_changed)
        self.layer_opacity_spin = QDoubleSpinBox()
        self.layer_opacity_spin.setRange(0.0, 1.0)
        self.layer_opacity_spin.setDecimals(2)
        self.layer_opacity_spin.setSingleStep(0.1)
        self.layer_opacity_spin.valueChanged.connect(self.properties_changed)
        self.layer_clip_combo = QComboBox()
        self.layer_clip_combo.addItems(["none", "horizontal", "vertical"])
        self.layer_clip_combo.currentTextChanged.connect(self.properties_changed)
        self.layer_value_spin = QDoubleSpinBox()
        self.layer_value_spin.setRange(0.0, 1.0)
        self.layer_value_spin.setDecimals(2)
        self.layer_value_spin.setSingleStep(0.05)
        self.layer_value_spin.valueChanged.connect(self.properties_changed)
        self.layer_value_slider = QSlider(Qt.Horizontal)
        self.layer_value_slider.setRange(0, 100)
        self.layer_value_slider.valueChanged.connect(self.value_slider_changed)

        form.addRow("Name", self.layer_name_edit)
        form.addRow("Image", self.layer_image_combo)
        form.addRow("Role", self.layer_role_combo)
        form.addRow("X", self.layer_x_spin)
        form.addRow("Y", self.layer_y_spin)
        form.addRow("", self.layer_visible_check)
        form.addRow("Opacity", self.layer_opacity_spin)
        form.addRow("Clip", self.layer_clip_combo)
        form.addRow("Value", self.layer_value_spin)
        form.addRow("", self.layer_value_slider)
        right_layout.addLayout(form)

        nudge = QGridLayout()
        for index, (label, dx, dy) in enumerate((("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1), ("Left 10", -10, 0), ("Right 10", 10, 0), ("Up 10", 0, -10), ("Down 10", 0, 10))):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, x=dx, y=dy: self.nudge_selected_layer(x, y))
            nudge.addWidget(button, index // 2, index % 2)
        right_layout.addLayout(nudge)
        right_layout.addStretch()
        layout.addWidget(right, 0)
        return page

    def load_initial_state(self):
        selected_type = self.existing_metadata.get("type")
        if not selected_type and self.guesses:
            selected_type = self.guesses[0].guessed_type
        if selected_type not in ASSET_TYPES:
            selected_type = AssetType.STATIC_IMAGE if self.source_path.is_file() else AssetType.FRAME_ANIMATION
        self.type_combo.setCurrentText(selected_type)
        self.select_guess(0 if self.guesses else -1)
        if self.guess_list.count():
            self.guess_list.setCurrentRow(0)
        if self.existing_metadata.get("type") == AssetType.COMPOSITE_UI:
            self.load_composite_metadata(self.existing_metadata)
        else:
            self.load_composite_defaults()
        sprite_metadata = self.existing_metadata
        if self.existing_metadata.get("type") != AssetType.SPRITE_STRIP and self.guesses:
            first_guess = self.guesses[0]
            if first_guess.guessed_type == AssetType.SPRITE_STRIP:
                sprite_metadata = first_guess.suggested_metadata
        self.load_sprite_strip_metadata(sprite_metadata)
        self.sync_type(selected_type)

    def select_guess(self, row):
        guess = self.selected_guess()
        if guess is not None:
            self.type_combo.setCurrentText(guess.guessed_type if guess.guessed_type in ASSET_TYPES else self.type_combo.currentText())
            if guess.guessed_type == AssetType.SPRITE_STRIP and self.existing_metadata.get("type") != AssetType.SPRITE_STRIP:
                self.load_sprite_strip_metadata(guess.suggested_metadata)
        self.update_details()

    def sync_type(self, asset_type):
        self.guess_list.setVisible(len(self.guesses) > 1 and asset_type != AssetType.COMPOSITE_UI)
        if asset_type == AssetType.COMPOSITE_UI:
            self.stack.setCurrentWidget(self.composite_page)
        elif asset_type == AssetType.SPRITE_STRIP:
            self.stack.setCurrentWidget(self.sprite_strip_page)
        else:
            self.stack.setCurrentWidget(self.details_page)
        self.update_details()
        if asset_type == AssetType.COMPOSITE_UI:
            self.refresh_composite_preview()
        if asset_type == AssetType.SPRITE_STRIP:
            self.refresh_sprite_strip_preview()

    def selected_guess(self):
        item = self.guess_list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def update_details(self):
        if not hasattr(self, "details_label"):
            return
        guess = self.selected_guess()
        if guess is None:
            self.details_label.setText("No analyzer guess is selected.")
            self.metadata_preview.setText("")
            return
        reasons = "\n".join(f"- {reason}" for reason in guess.reasons)
        self.details_label.setText(f"Selected analyzer guess: {guess.guessed_type} ({guess.confidence:.0%})\n\n{reasons}")
        self.metadata_preview.setText(json.dumps(self.metadata(), indent=2))

    def make_layer(self, layer):
        layer = dict(layer)
        layer.setdefault("_id", self.next_layer_id)
        self.next_layer_id = max(self.next_layer_id, int(layer["_id"]) + 1)
        return layer

    def selected_layer(self):
        if self.selected_layer_index < 0 or self.selected_layer_index >= len(self.layers):
            return None
        return self.layers[self.selected_layer_index]

    def snapshot(self):
        return {
            "layers": copy.deepcopy(self.layers),
            "selected_layer_id": self.selected_layer_id,
            "next_layer_id": self.next_layer_id,
        }

    def restore_snapshot(self, snapshot):
        self._applying_history = True
        self.layers = copy.deepcopy(snapshot["layers"])
        self.selected_layer_id = snapshot.get("selected_layer_id")
        self.next_layer_id = snapshot.get("next_layer_id", self.next_layer_id)
        self.selected_layer_index = self.index_for_layer_id(self.selected_layer_id)
        self.sync_layer_list()
        self.select_layer(self.selected_layer_index)
        self._applying_history = False
        self.mark_dirty()

    def push_undo_state(self, description="", coalesce_key=None):
        if self._loading or self._applying_history:
            return
        if coalesce_key and self._coalesce_key == coalesce_key:
            return
        self.undo_stack.append(self.snapshot())
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self._coalesce_key = coalesce_key

    def end_coalesce(self):
        self._coalesce_key = None

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.snapshot())
        self.restore_snapshot(self.undo_stack.pop())

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.snapshot())
        self.restore_snapshot(self.redo_stack.pop())

    def mark_dirty(self):
        if self._applying_history:
            return
        self.dirty = True
        title = self.windowTitle()
        if not title.endswith("*"):
            self.setWindowTitle(f"{title}*")

    def index_for_layer_id(self, layer_id):
        for index, layer in enumerate(self.layers):
            if layer.get("_id") == layer_id:
                return index
        return -1

    def load_composite_defaults(self):
        preview = next((path.name for path in self.image_files if _matches(path, PREVIEW_TERMS)), "")
        self.preview_combo.setCurrentText(preview)
        for path in self.image_files:
            if path.name == preview or _matches(path, PREVIEW_TERMS):
                continue
            self.layers.append(self.make_layer(_default_layer_for_image(path)))
        self.sync_layer_list()
        if self.layers:
            self.select_layer(0)

    def load_composite_metadata(self, metadata):
        self.preview_combo.setCurrentText(str(metadata.get("preview") or ""))
        for layer in metadata.get("layers", []):
            if isinstance(layer, dict):
                self.layers.append(self.make_layer(_normalized_layer(layer)))
        self.sync_layer_list()
        if self.layers:
            self.select_layer(0)

    def sync_layer_list(self):
        selected_id = self.selected_layer_id
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for layer in self.layers:
            name = str(layer.get("name") or layer.get("image") or "layer")
            badges = []
            if not layer.get("visible", True):
                badges.append("hidden")
            if layer.get("clip", "none") != "none":
                badges.append(str(layer.get("clip")))
            role = layer.get("role")
            if role and role != "normal":
                badges.append(str(role))
            suffix = f"  [{' | '.join(badges)}]" if badges else ""
            item = QListWidgetItem(f"{name}{suffix}")
            item.setData(Qt.UserRole, layer.get("_id"))
            self.layer_list.addItem(item)
        self.layer_list.blockSignals(False)
        if self.layers:
            self.selected_layer_index = self.index_for_layer_id(selected_id)
            if self.selected_layer_index < 0:
                self.selected_layer_index = max(0, min(self.selected_layer_index, len(self.layers) - 1))
                self.selected_layer_id = self.layers[self.selected_layer_index].get("_id")
            self.layer_list.setCurrentRow(self.selected_layer_index)
        else:
            self.selected_layer_index = -1
            self.selected_layer_id = None
        self.refresh_composite_preview()

    def select_layer(self, row):
        if self._loading:
            return
        self.end_coalesce()
        if row < 0 or row >= len(self.layers):
            self.selected_layer_index = -1
            self.set_properties_enabled(False)
            self.refresh_composite_preview()
            return
        self.selected_layer_index = row
        self.selected_layer_id = self.layers[row].get("_id")
        self.layer_list.blockSignals(True)
        self.layer_list.setCurrentRow(row)
        self.layer_list.blockSignals(False)
        self.load_layer_properties()
        self.refresh_composite_preview()

    def layer_rows_moved(self, parent, start, end, destination, row):
        if self._loading or self._applying_history:
            return
        current_item = self.layer_list.currentItem()
        moved_id = current_item.data(Qt.UserRole) if current_item is not None else self.selected_layer_id
        ordered_ids = [self.layer_list.item(i).data(Qt.UserRole) for i in range(self.layer_list.count())]
        by_id = {layer.get("_id"): layer for layer in self.layers}
        if set(ordered_ids) != set(by_id):
            return
        self.push_undo_state("Reorder layers")
        self.layers = [by_id[layer_id] for layer_id in ordered_ids]
        self.selected_layer_id = moved_id
        self.selected_layer_index = self.index_for_layer_id(moved_id)
        self.mark_dirty()
        self.refresh_composite_preview()

    def set_properties_enabled(self, enabled):
        for widget in (
            self.layer_name_edit,
            self.layer_image_combo,
            self.layer_role_combo,
            self.layer_x_spin,
            self.layer_y_spin,
            self.layer_visible_check,
            self.layer_opacity_spin,
            self.layer_clip_combo,
            self.layer_value_spin,
            self.layer_value_slider,
        ):
            widget.setEnabled(enabled)

    def load_layer_properties(self):
        self._loading = True
        self.set_properties_enabled(self.selected_layer_index >= 0)
        if self.selected_layer_index >= 0:
            layer = self.layers[self.selected_layer_index]
            self.layer_name_edit.setText(str(layer.get("name") or "layer"))
            self.layer_image_combo.setCurrentText(str(layer.get("image") or ""))
            self.layer_role_combo.setCurrentText(str(layer.get("role") or "normal"))
            self.layer_x_spin.setValue(_int(layer.get("x"), 0))
            self.layer_y_spin.setValue(_int(layer.get("y"), 0))
            self.layer_visible_check.setChecked(bool(layer.get("visible", True)))
            self.layer_opacity_spin.setValue(_float(layer.get("opacity"), 1.0))
            self.layer_clip_combo.setCurrentText(str(layer.get("clip") or "none"))
            value = _float(layer.get("value"), 1.0)
            self.layer_value_spin.setValue(value)
            self.layer_value_slider.setValue(round(value * 100))
        self._loading = False

    def properties_changed(self):
        if self._loading or self.selected_layer_index < 0:
            return
        self.push_undo_state("Edit layer", coalesce_key="properties")
        layer = self.layers[self.selected_layer_index]
        layer["name"] = self.layer_name_edit.text().strip() or "layer"
        layer["image"] = self.layer_image_combo.currentText()
        layer["role"] = self.layer_role_combo.currentText()
        layer["x"] = self.layer_x_spin.value()
        layer["y"] = self.layer_y_spin.value()
        layer["visible"] = self.layer_visible_check.isChecked()
        layer["opacity"] = self.layer_opacity_spin.value()
        layer["clip"] = self.layer_clip_combo.currentText()
        layer["value"] = self.layer_value_spin.value()
        self.layer_value_slider.blockSignals(True)
        self.layer_value_slider.setValue(round(layer["value"] * 100))
        self.layer_value_slider.blockSignals(False)
        self.sync_layer_list()
        self.mark_dirty()

    def value_slider_changed(self, value):
        if self._loading:
            return
        self.layer_value_spin.blockSignals(True)
        self.layer_value_spin.setValue(value / 100)
        self.layer_value_spin.blockSignals(False)
        self.properties_changed()

    def role_changed(self, role):
        if self._loading or self.selected_layer_index < 0:
            return
        if role in {"health", "mana", "stamina"}:
            self.layer_clip_combo.setCurrentText("horizontal")
            if not self.layer_name_edit.text().strip() or self.layer_name_edit.text().strip() == "layer":
                self.layer_name_edit.setText(role)
        if role == "base":
            self.layer_clip_combo.setCurrentText("none")
            self.layer_name_edit.setText("base")
        self.properties_changed()

    def add_empty_layer(self):
        self.push_undo_state("Add layer")
        self.end_coalesce()
        image = self.image_files[0].name if self.image_files else ""
        self.layers.append(self.make_layer({"name": self.unique_layer_name(Path(image).stem or "layer"), "image": image, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "none", "value": 1.0, "role": "normal"}))
        self.sync_layer_list()
        self.select_layer(len(self.layers) - 1)
        self.mark_dirty()

    def remove_selected_layer(self):
        if self.selected_layer_index >= 0:
            self.push_undo_state("Remove layer")
            self.end_coalesce()
            del self.layers[self.selected_layer_index]
            self.sync_layer_list()
            self.select_layer(min(self.selected_layer_index, len(self.layers) - 1))
            self.mark_dirty()

    def duplicate_selected_layer(self):
        if self.selected_layer_index < 0:
            return
        self.push_undo_state("Duplicate layer")
        self.end_coalesce()
        layer = copy.deepcopy(self.layers[self.selected_layer_index])
        layer["_id"] = self.next_layer_id
        self.next_layer_id += 1
        layer["name"] = self.unique_layer_name(f"{layer.get('name', 'layer')} copy")
        layer["x"] = _int(layer.get("x"), 0) + 8
        layer["y"] = _int(layer.get("y"), 0) + 8
        self.layers.insert(self.selected_layer_index + 1, layer)
        self.sync_layer_list()
        self.select_layer(self.selected_layer_index + 1)
        self.mark_dirty()

    def move_selected_layer(self, delta):
        index = self.selected_layer_index
        new_index = index + delta
        if index < 0 or new_index < 0 or new_index >= len(self.layers):
            return
        self.push_undo_state("Reorder layers")
        self.end_coalesce()
        selected_id = self.selected_layer_id
        self.layers[index], self.layers[new_index] = self.layers[new_index], self.layers[index]
        self.selected_layer_id = selected_id
        self.selected_layer_index = new_index
        self.sync_layer_list()
        self.select_layer(new_index)
        self.mark_dirty()

    def bring_selected_to_front(self):
        if self.selected_layer_index < 0 or self.selected_layer_index == len(self.layers) - 1:
            return
        self.push_undo_state("Bring layer to front")
        self.end_coalesce()
        layer = self.layers.pop(self.selected_layer_index)
        self.layers.append(layer)
        self.selected_layer_id = layer.get("_id")
        self.sync_layer_list()
        self.select_layer(len(self.layers) - 1)
        self.mark_dirty()

    def send_selected_to_back(self):
        if self.selected_layer_index <= 0:
            return
        self.push_undo_state("Send layer to back")
        self.end_coalesce()
        layer = self.layers.pop(self.selected_layer_index)
        self.layers.insert(0, layer)
        self.selected_layer_id = layer.get("_id")
        self.sync_layer_list()
        self.select_layer(0)
        self.mark_dirty()

    def copy_selected_layer(self):
        layer = self.selected_layer()
        if layer is None:
            return
        self.layer_clipboard = copy.deepcopy(layer)
        self.layer_clipboard.pop("_id", None)
        QApplication.clipboard().setText(json.dumps(self.layer_clipboard, indent=2))
        self.status_label.setText(f"Copied layer: {layer.get('name', 'layer')}")

    def paste_layer(self):
        if self.layer_clipboard is None:
            text = QApplication.clipboard().text()
            try:
                data = json.loads(text)
                if isinstance(data, dict) and data.get("image"):
                    self.layer_clipboard = data
            except json.JSONDecodeError:
                pass
        if self.layer_clipboard is None:
            return
        self.push_undo_state("Paste layer")
        self.end_coalesce()
        layer = copy.deepcopy(self.layer_clipboard)
        layer["_id"] = self.next_layer_id
        self.next_layer_id += 1
        layer["name"] = self.unique_layer_name(f"{str(layer.get('name') or 'layer')} copy")
        layer["x"] = _int(layer.get("x"), 0) + 10
        layer["y"] = _int(layer.get("y"), 0) + 10
        insert_at = self.selected_layer_index + 1 if self.selected_layer_index >= 0 else len(self.layers)
        self.layers.insert(insert_at, layer)
        self.selected_layer_id = layer["_id"]
        self.sync_layer_list()
        self.select_layer(insert_at)
        self.mark_dirty()

    def unique_layer_name(self, base):
        existing = {str(layer.get("name")) for layer in self.layers}
        if base not in existing:
            return base
        index = 2
        candidate = f"{base} 2"
        if base.endswith(" copy"):
            candidate = f"{base} 2"
        while candidate in existing:
            index += 1
            candidate = f"{base} {index}"
        return candidate

    def nudge_selected_layer(self, dx, dy):
        if self.selected_layer_index < 0:
            return
        self.push_undo_state("Move layer", coalesce_key="nudge")
        layer = self.layers[self.selected_layer_index]
        self.set_selected_layer_position(_int(layer.get("x"), 0) + dx, _int(layer.get("y"), 0) + dy)

    def set_selected_layer_position(self, x, y):
        if self.selected_layer_index < 0:
            return
        if self.snap_grid_check.isChecked():
            x = round(int(x) / 16) * 16
            y = round(int(y) / 16) * 16
        self.layers[self.selected_layer_index]["x"] = int(x)
        self.layers[self.selected_layer_index]["y"] = int(y)
        self._loading = True
        self.layer_x_spin.setValue(int(x))
        self.layer_y_spin.setValue(int(y))
        self._loading = False
        self.status_label.setText(f"Layer position: x={int(x)}, y={int(y)}")
        self.refresh_composite_preview()
        self.mark_dirty()

    def layer_at_point(self, point, cycle=False):
        matches = []
        for index in range(len(self.layers) - 1, -1, -1):
            layer = self.layers[index]
            if not layer.get("visible", True):
                continue
            image = layer.get("image")
            image_path = self.source_path / image if self.source_path.is_dir() and image else self.source_path
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                continue
            rect = QRectF(float(layer.get("x", 0)), float(layer.get("y", 0)), pixmap.width(), pixmap.height())
            if rect.contains(point):
                matches.append(index)
        if not matches:
            return -1
        if not cycle or self.selected_layer_index not in matches:
            return matches[0]
        current_position = matches.index(self.selected_layer_index)
        return matches[(current_position + 1) % len(matches)]

    def set_preview_zoom(self, zoom):
        self.preview_zoom = zoom
        self.composite_preview.update()

    def zoom_preview(self, multiplier):
        current = 1.0 if self.preview_zoom == "fit" else float(self.preview_zoom)
        self.preview_zoom = min(8.0, max(0.1, current * multiplier))
        self.composite_preview.update()

    def composite_layers(self):
        layers = []
        for layer in self.layers:
            image_name = layer.get("image")
            if not image_name or not _readable_image(self.source_path, image_name):
                continue
            out = {
                "name": str(layer.get("name") or Path(image_name).stem),
                "image": str(image_name),
                "x": _int(layer.get("x"), 0),
                "y": _int(layer.get("y"), 0),
            }
            if layer.get("visible", True) is False:
                out["visible"] = False
            if _float(layer.get("opacity"), 1.0) < 1.0:
                out["opacity"] = _float(layer.get("opacity"), 1.0)
            clip = str(layer.get("clip") or "none")
            if clip != "none":
                out["clip"] = clip
                out["value"] = _float(layer.get("value"), 1.0)
            role = layer.get("role")
            if role and role != "normal":
                out["role"] = role
            layers.append(out)
        return layers

    def refresh_composite_preview(self):
        if self._loading or self.type_combo.currentText() != AssetType.COMPOSITE_UI:
            return
        metadata = self.composite_metadata(validate=False)
        renderer = CompositeUIRenderer(self.source_path, metadata)
        pixmap = renderer.render() if renderer.layers else QPixmap()
        self.composite_preview.set_pixmap(pixmap)

    def metadata(self):
        asset_type = self.type_combo.currentText()
        if asset_type == AssetType.COMPOSITE_UI:
            return self.composite_metadata(validate=False)
        if asset_type == AssetType.SPRITE_STRIP:
            return self.sprite_strip_metadata()
        guess = self.selected_guess()
        metadata = dict(guess.suggested_metadata if isinstance(guess, AssetGuess) else self.existing_metadata)
        metadata["type"] = asset_type
        metadata["name"] = self.asset_name()
        if self.source_path.is_file() and asset_type not in {AssetType.GIF, AssetType.STATIC_IMAGE}:
            metadata.setdefault("image", self.source_path.name)
        return metadata

    def load_sprite_strip_metadata(self, metadata):
        image = metadata.get("image") or (self.image_files[0].name if self.image_files else "")
        self.strip_image_combo.setCurrentText(str(image))
        self.strip_frames_spin.setValue(_int(metadata.get("frames"), 1))
        direction = str(metadata.get("direction") or "horizontal")
        self.strip_direction_combo.setCurrentText(direction if direction in {"horizontal", "vertical"} else "horizontal")
        self.strip_frame_width_spin.setValue(_int(metadata.get("frame_width"), 0))
        self.strip_frame_height_spin.setValue(_int(metadata.get("frame_height"), 0))
        self.strip_fps_spin.setValue(_int(metadata.get("fps"), 8))
        self.strip_loop_check.setChecked(bool(metadata.get("loop", True)))
        self.strip_crop_left_spin.setValue(_int(metadata.get("crop_left"), 0))
        self.strip_crop_top_spin.setValue(_int(metadata.get("crop_top"), 0))
        self.strip_crop_right_spin.setValue(_int(metadata.get("crop_right"), 0))
        self.strip_crop_bottom_spin.setValue(_int(metadata.get("crop_bottom"), 0))
        self.strip_trim_check.setChecked(bool(metadata.get("trim_transparent", False)))
        self.strip_trim_padding_spin.setValue(_int(metadata.get("trim_padding"), 0))
        self.strip_anchor_x_spin.setValue(_float(metadata.get("anchor_x"), 0.5))
        self.strip_anchor_y_spin.setValue(_float(metadata.get("anchor_y"), 0.9))
        self.refresh_sprite_strip_preview()

    def sprite_strip_metadata(self):
        metadata = {
            "name": self.asset_name(),
            "type": AssetType.SPRITE_STRIP,
            "image": self.strip_image_combo.currentText(),
            "frames": self.strip_frames_spin.value(),
            "direction": self.strip_direction_combo.currentText(),
            "fps": self.strip_fps_spin.value(),
            "loop": self.strip_loop_check.isChecked(),
            "crop_left": self.strip_crop_left_spin.value(),
            "crop_top": self.strip_crop_top_spin.value(),
            "crop_right": self.strip_crop_right_spin.value(),
            "crop_bottom": self.strip_crop_bottom_spin.value(),
            "trim_transparent": self.strip_trim_check.isChecked(),
            "trim_padding": self.strip_trim_padding_spin.value(),
            "anchor_x": self.strip_anchor_x_spin.value(),
            "anchor_y": self.strip_anchor_y_spin.value(),
        }
        if self.strip_frame_width_spin.value() > 0:
            metadata["frame_width"] = self.strip_frame_width_spin.value()
        if self.strip_frame_height_spin.value() > 0:
            metadata["frame_height"] = self.strip_frame_height_spin.value()
        return metadata

    def refresh_sprite_strip_preview(self):
        if self._loading:
            return
        image_name = self.strip_image_combo.currentText()
        image_path = self.source_path / image_name if self.source_path.is_dir() else self.source_path
        pixmap = QPixmap(str(image_path))
        size = QImageReader(str(image_path)).size()
        if pixmap.isNull() or not size.isValid():
            self.strip_dimensions_label.setText("Unreadable image")
            self.strip_frame_size_label.setText("")
            self.strip_warning_label.setText("Select a readable image.")
            self.strip_preview.setPixmap(QPixmap())
            self.strip_preview.resize(self.strip_preview.minimumSize())
            return
        width, height = pixmap.width(), pixmap.height()
        metadata = self.sprite_strip_metadata()
        self.strip_dimensions_label.setText(f"{width} x {height}")
        frame_width, frame_height, error = sprite_strip_frame_size(width, height, metadata)
        crop_left, crop_top, crop_right, crop_bottom = sprite_strip_crop_values(metadata)
        crop_width = frame_width - crop_left - crop_right if frame_width else 0
        crop_height = frame_height - crop_top - crop_bottom if frame_height else 0
        self.strip_frame_size_label.setText(
            f"Cell: {frame_width or '?'} x {frame_height or '?'}   Cropped frame: {crop_width or '?'} x {crop_height or '?'}"
        )
        if error:
            self.strip_warning_label.setText(error)
            self.strip_preview.setPixmap(QPixmap())
            self.strip_preview.resize(self.strip_preview.minimumSize())
            return
        if crop_width < 1 or crop_height < 1:
            self.strip_warning_label.setText("Crop margins leave an empty frame. Reduce crop values.")
            self.strip_preview.setPixmap(QPixmap())
            self.strip_preview.resize(self.strip_preview.minimumSize())
            return

        frames = sprite_strip_frames_from_pixmap(pixmap, metadata)
        if not frames:
            self.strip_warning_label.setText("No readable frames could be cropped.")
            self.strip_preview.setPixmap(QPixmap())
            self.strip_preview.resize(self.strip_preview.minimumSize())
            return
        self.strip_warning_label.setText(f"Previewing {len(frames)} cropped frame(s).")
        grid = self.sprite_grid_pixmap(frames)
        self.strip_preview.setPixmap(grid)
        self.strip_preview.adjustSize()

    def sprite_grid_pixmap(self, frames):
        cell_w = max(frame.width() for frame in frames)
        cell_h = max(frame.height() for frame in frames)
        label_h = 18
        padding = 6
        columns = min(6, max(1, len(frames)))
        rows = (len(frames) + columns - 1) // columns
        canvas = QPixmap(columns * (cell_w + padding), rows * (cell_h + label_h + padding))
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        for index, frame in enumerate(frames):
            x = (index % columns) * (cell_w + padding)
            y = (index // columns) * (cell_h + label_h + padding)
            painter.drawPixmap(x + (cell_w - frame.width()) // 2, y + (cell_h - frame.height()) // 2, frame)
            painter.setPen(QPen(QColor("#ffdd55"), 1))
            painter.drawRect(x, y, cell_w - 1, cell_h - 1)
            painter.setPen(QPen(QColor("#d8d8d8"), 1))
            painter.drawText(x + 3, y + cell_h + 14, f"{index + 1}")
        painter.end()
        return canvas

    def export_sprite_strip_frames(self):
        image_name = self.strip_image_combo.currentText()
        image_path = self.source_path / image_name if self.source_path.is_dir() else self.source_path
        pixmap = QPixmap(str(image_path))
        frames = sprite_strip_frames_from_pixmap(pixmap, self.sprite_strip_metadata()) if not pixmap.isNull() else []
        if not frames:
            QMessageBox.warning(self, "Export Frames", "No valid frames could be exported.")
            return
        target_root = self.source_path if self.source_path.is_dir() else self.source_path.parent
        target = target_root / f"{self.asset_name()} frames"
        index = 1
        while target.exists():
            target = target_root / f"{self.asset_name()} frames {index}"
            index += 1
        target.mkdir(parents=True)
        for frame_index, frame in enumerate(frames, start=1):
            frame.save(str(target / f"{frame_index:04d}.png"))
        (target / "asset.json").write_text(json.dumps({"type": "frame_animation", "name": self.asset_name(), "fps": self.strip_fps_spin.value()}, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Export Frames", f"Exported {len(frames)} frame(s) to:\n{target}")

    def composite_metadata(self, validate=True):
        metadata = {"name": self.asset_name(), "type": AssetType.COMPOSITE_UI, "layers": self.composite_layers()}
        preview = self.preview_combo.currentText()
        if preview:
            metadata["preview"] = preview
        if validate and not metadata["layers"]:
            return None
        return metadata

    def asset_name(self):
        return self.name_edit.text().strip() or _default_name(self.source_path)

    def keyPressEvent(self, event):
        focus = self.focusWidget()
        if isinstance(focus, TEXT_EDIT_WIDGETS):
            return super().keyPressEvent(event)
        if self.handle_editor_shortcut(event):
            return
        return super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress and watched in {self.layer_list, self.composite_preview}:
            return self.handle_editor_shortcut(event)
        return super().eventFilter(watched, event)

    def handle_editor_shortcut(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key_Z and modifiers & Qt.ControlModifier:
            if modifiers & Qt.ShiftModifier:
                self.redo()
            else:
                self.undo()
        elif key == Qt.Key_Y and modifiers & Qt.ControlModifier:
            self.redo()
        elif key == Qt.Key_C and modifiers & Qt.ControlModifier:
            self.copy_selected_layer()
        elif key == Qt.Key_V and modifiers & Qt.ControlModifier:
            self.paste_layer()
        elif key == Qt.Key_D and modifiers & Qt.ControlModifier:
            self.duplicate_selected_layer()
        elif key == Qt.Key_BracketRight and modifiers & Qt.ControlModifier:
            if modifiers & Qt.ShiftModifier:
                self.bring_selected_to_front()
            else:
                self.move_selected_layer(1)
        elif key == Qt.Key_BracketLeft and modifiers & Qt.ControlModifier:
            if modifiers & Qt.ShiftModifier:
                self.send_selected_to_back()
            else:
                self.move_selected_layer(-1)
        elif key == Qt.Key_Delete:
            self.remove_selected_layer()
        elif key == Qt.Key_R and modifiers & Qt.ControlModifier:
            self.refresh_composite_preview()
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_preview(1.25)
        elif key == Qt.Key_Minus:
            self.zoom_preview(0.8)
        elif key == Qt.Key_F:
            self.set_preview_zoom("fit")
        elif key == Qt.Key_Space and self.selected_layer_index >= 0:
            self.push_undo_state("Toggle layer visibility")
            self.layers[self.selected_layer_index]["visible"] = not self.layers[self.selected_layer_index].get("visible", True)
            self.load_layer_properties()
            self.sync_layer_list()
            self.mark_dirty()
        else:
            return self.handle_movement_shortcut(event)
        event.accept()
        return True

    def handle_movement_shortcut(self, event):
        key = event.key()
        modifiers = event.modifiers()
        step = 10 if modifiers & Qt.ShiftModifier else 5 if modifiers & Qt.ControlModifier else 1
        if key == Qt.Key_Left:
            self.nudge_selected_layer(-step, 0)
        elif key == Qt.Key_Right:
            self.nudge_selected_layer(step, 0)
        elif key == Qt.Key_Up:
            self.nudge_selected_layer(0, -step)
        elif key == Qt.Key_Down:
            self.nudge_selected_layer(0, step)
        else:
            return False
        event.accept()
        return True

    def validate_and_accept(self):
        if self.type_combo.currentText() == AssetType.COMPOSITE_UI:
            metadata = self.composite_metadata(validate=True)
            if metadata is None:
                QMessageBox.warning(self, "Asset Setup", "Composite UI assets need at least one readable layer.")
                return
        metadata = self.metadata()
        fake_asset = type("Asset", (), {"type": metadata.get("type"), "path": self.source_path, "metadata": metadata})()
        errors = validate_asset_metadata(fake_asset)
        if errors:
            QMessageBox.warning(self, "Asset Setup", "\n".join(errors))
            return
        self.dirty = False
        self.accept()

    def reject(self):
        if self.dirty:
            result = QMessageBox.question(
                self,
                "Discard Changes",
                "Discard unsaved asset setup changes?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if result != QMessageBox.Yes:
                return
        super().reject()


def _image_files(path: Path):
    path = Path(path)
    if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
        return [path]
    if not path.is_dir():
        return []
    return sorted((item for item in path.iterdir() if item.is_file() and is_supported_frame_file(item)), key=natural_key)


def _default_name(path: Path):
    return path.stem if path.is_file() else path.name


def _default_layer_for_image(path: Path):
    stem = path.stem.lower()
    if _matches(path, BASE_TERMS):
        return {"name": "base", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "none", "value": 1.0, "role": "base"}
    if any(term in stem for term in HEALTH_TERMS):
        return {"name": "health", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "horizontal", "value": 1.0, "role": "health"}
    if any(term in stem for term in ENERGY_TERMS):
        return {"name": "energy", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "horizontal", "value": 1.0, "role": "mana"}
    if any(term in stem for term in STAMINA_TERMS):
        return {"name": "stamina", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "horizontal", "value": 1.0, "role": "stamina"}
    return {"name": path.stem, "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "none", "value": 1.0, "role": "normal"}


def _normalized_layer(layer):
    normalized = _default_layer_for_image(Path(str(layer.get("image") or "layer.png")))
    normalized.update(layer)
    normalized.setdefault("visible", True)
    normalized.setdefault("opacity", 1.0)
    normalized.setdefault("clip", "none")
    normalized.setdefault("value", 1.0)
    normalized.setdefault("role", "normal")
    return normalized


def _matches(path: Path, terms):
    stem = path.stem.lower()
    return any(term in stem for term in terms)


def _readable_image(folder: Path, image_name: str):
    folder = Path(folder)
    image_path = folder / image_name if folder.is_dir() else folder
    pixmap = QPixmap(str(image_path))
    return not pixmap.isNull()


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default):
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return default
