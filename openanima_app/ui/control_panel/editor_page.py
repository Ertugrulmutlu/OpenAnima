from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...runtime import state
from ...runtime.action_runner import (
    ACTION_LAUNCH_APP,
    ACTION_OPEN_FILE,
    ACTION_OPEN_FOLDER,
    ACTION_OPEN_URL,
    normalized_action_config,
)
from ...assets.detection import detect_asset
from ...assets.models import AssetType
from ...overlay.movement import normalized_movement_config
from ...runtime.logging import log_warning
from ...runtime.paths import BASE_DIR
from ...runtime.session import persist_runtime_state


def build_editor_tab(panel):
    panel.editor_tab = QWidget()
    layout = QVBoxLayout(panel.editor_tab)
    layout.setContentsMargins(0, 0, 0, 0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    layout.addWidget(scroll)

    content = QWidget()
    scroll.setWidget(content)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(16, 16, 16, 16)
    content_layout.setSpacing(14)

    header_row = QHBoxLayout()
    inspector_title = QLabel("Inspector")
    inspector_title.setObjectName("SectionTitle")

    panel.saved_label = QLabel("")
    panel.saved_label.setObjectName("SavedLabel")

    header_row.addWidget(inspector_title)
    header_row.addStretch()
    header_row.addWidget(panel.saved_label)

    panel.saved_timer = QTimer(panel)
    panel.saved_timer.setSingleShot(True)
    panel.saved_timer.timeout.connect(lambda: panel.saved_label.setText(""))

    panel.editor_placeholder = panel.empty_state(
        "Select an overlay to edit it.",
        " ",
        [],
    )

    panel.selected_group = QGroupBox("Selected Overlay")
    selected_layout = QVBoxLayout(panel.selected_group)
    selected_layout.setContentsMargins(14, 18, 14, 14)
    selected_layout.setSpacing(6)

    panel.editor_name = QLabel("Select an overlay to edit it.")
    panel.editor_name.setObjectName("SubtleLabel")

    panel.editor_type = QLabel("")
    panel.editor_type.setObjectName("SubtleLabel")

    selected_layout.addWidget(panel.editor_name)
    selected_layout.addWidget(panel.editor_type)

    panel.overlay_controls_group = QGroupBox("Overlay Controls")
    overlay_controls_layout = QVBoxLayout(panel.overlay_controls_group)
    overlay_controls_layout.setContentsMargins(14, 18, 14, 14)
    overlay_controls_layout.setSpacing(10)

    panel.visibility_check = QCheckBox("Visible")
    panel.inspector_lock_button = QPushButton("Lock")
    panel.inspector_edit_button = QPushButton("Edit Overlay")
    panel.inspector_metadata_button = QPushButton("Asset Metadata")
    panel.inspector_remove_button = QPushButton("Remove")

    panel.prepare_button(panel.inspector_lock_button, 120, "Lock or unlock this overlay")
    panel.prepare_button(panel.inspector_edit_button, 120, "Edit Overlay")
    panel.prepare_button(panel.inspector_metadata_button, 120, "Edit Asset Metadata")
    panel.prepare_button(panel.inspector_remove_button, 120, "Remove Overlay")

    panel.inspector_remove_button.setObjectName("DangerButton")

    panel.visibility_check.toggled.connect(panel.editor_visibility_changed)
    panel.inspector_lock_button.clicked.connect(panel.toggle_selected_lock)
    panel.inspector_edit_button.clicked.connect(panel.focus_selected_overlay)
    panel.inspector_metadata_button.clicked.connect(panel.configure_selected_overlay_asset)
    panel.inspector_remove_button.clicked.connect(panel.remove_selected_overlay)

    overlay_controls_layout.addWidget(panel.visibility_check)
    overlay_controls_layout.addWidget(panel.inspector_lock_button)
    overlay_controls_layout.addWidget(panel.inspector_edit_button)
    overlay_controls_layout.addWidget(panel.inspector_metadata_button)

    danger_label = QLabel("Danger zone")
    danger_label.setObjectName("SubtleLabel")

    overlay_controls_layout.addSpacing(8)
    overlay_controls_layout.addWidget(danger_label)
    overlay_controls_layout.addWidget(panel.inspector_remove_button)

    panel.scale_label = QLabel("Scale: 100%")
    panel.scale_slider = QSlider(Qt.Horizontal)
    panel.scale_slider.setRange(50, 150)
    panel.scale_slider.setTickInterval(10)
    panel.scale_slider.valueChanged.connect(panel.editor_scale_changed)

    panel.opacity_label = QLabel("Opacity: 100%")
    panel.opacity_slider = QSlider(Qt.Horizontal)
    panel.opacity_slider.setRange(50, 100)
    panel.opacity_slider.setTickInterval(10)
    panel.opacity_slider.valueChanged.connect(panel.editor_opacity_changed)

    panel.speed_label = QLabel("Speed: 100%")
    panel.speed_slider = QSlider(Qt.Horizontal)
    panel.speed_slider.setRange(25, 200)
    panel.speed_slider.setTickInterval(25)
    panel.speed_slider.valueChanged.connect(panel.editor_speed_changed)

    panel.transform_group = QGroupBox("Appearance")
    transform_layout = QVBoxLayout(panel.transform_group)
    transform_layout.setContentsMargins(14, 18, 14, 14)
    transform_layout.setSpacing(12)

    transform_layout.addWidget(panel.slider_row(panel.scale_label, panel.scale_slider))
    transform_layout.addWidget(panel.slider_row(panel.opacity_label, panel.opacity_slider))

    panel.speed_row = panel.slider_row(panel.speed_label, panel.speed_slider)
    transform_layout.addWidget(panel.speed_row)

    panel.top_check = QCheckBox("Always on top")
    panel.click_check = QCheckBox("Click-through")
    panel.lock_check = QCheckBox("Locked")

    panel.top_check.toggled.connect(panel.editor_top_changed)
    panel.click_check.toggled.connect(panel.editor_click_changed)
    panel.lock_check.toggled.connect(panel.editor_lock_changed)

    panel.reload_button = QPushButton("Reload Asset")
    panel.reload_button.clicked.connect(panel.reload_selected_asset)

    panel.behavior_group = QGroupBox("Interaction")
    behavior_layout = QVBoxLayout(panel.behavior_group)
    behavior_layout.setContentsMargins(14, 18, 14, 14)
    behavior_layout.setSpacing(10)

    behavior_layout.addWidget(panel.top_check)
    behavior_layout.addWidget(panel.click_check)
    behavior_layout.addWidget(panel.reload_button)

    panel.action_group = QGroupBox("Actions")
    action_layout = QVBoxLayout(panel.action_group)
    action_layout.setContentsMargins(14, 18, 14, 14)
    action_layout.setSpacing(10)

    panel.action_enabled_check = QCheckBox("Enable action")

    panel.action_type_combo = QComboBox()
    panel.action_type_combo.addItem("Open file", ACTION_OPEN_FILE)
    panel.action_type_combo.addItem("Open folder", ACTION_OPEN_FOLDER)
    panel.action_type_combo.addItem("Open URL", ACTION_OPEN_URL)
    panel.action_type_combo.addItem("Launch application", ACTION_LAUNCH_APP)

    panel.action_target_edit = QLineEdit()
    panel.action_target_edit.setPlaceholderText("Path or https:// URL")

    action_target_row = QHBoxLayout()
    panel.action_browse_button = QPushButton("Browse")
    panel.action_test_button = QPushButton("Run action")

    action_target_row.addWidget(panel.action_target_edit, 1)
    action_target_row.addWidget(panel.action_browse_button)

    action_buttons = QHBoxLayout()
    action_buttons.addStretch()
    action_buttons.addWidget(panel.action_test_button)

    action_form = QFormLayout()
    action_form.addRow("", panel.action_enabled_check)
    action_form.addRow("Type", panel.action_type_combo)
    action_form.addRow("Target", action_target_row)

    action_layout.addLayout(action_form)
    action_layout.addLayout(action_buttons)

    panel.action_enabled_check.toggled.connect(panel.editor_action_changed)
    panel.action_type_combo.currentIndexChanged.connect(panel.editor_action_changed)
    panel.action_target_edit.editingFinished.connect(panel.editor_action_changed)
    panel.action_browse_button.clicked.connect(panel.browse_action_target)
    panel.action_test_button.clicked.connect(panel.test_selected_action)

    panel.movement_group = QGroupBox("Movement / Physics")
    movement_layout = QVBoxLayout(panel.movement_group)
    movement_layout.setContentsMargins(14, 18, 14, 14)
    movement_layout.setSpacing(10)

    panel.movement_enabled_check = QCheckBox("Enable movement")
    panel.movement_bounce_check = QCheckBox("Bounce on screen edges")
    panel.movement_vx_spin = panel.movement_spin(-500.0, 500.0, 1.0)
    panel.movement_vy_spin = panel.movement_spin(-500.0, 500.0, 1.0)
    panel.movement_gravity_spin = panel.movement_spin(-500.0, 500.0, 1.0)
    panel.movement_friction_spin = panel.movement_spin(0.0, 50.0, 0.1)

    movement_form = QFormLayout()
    movement_form.addRow("", panel.movement_enabled_check)
    movement_form.addRow("Velocity X", panel.movement_vx_spin)
    movement_form.addRow("Velocity Y", panel.movement_vy_spin)
    movement_form.addRow("", panel.movement_bounce_check)
    movement_form.addRow("Gravity", panel.movement_gravity_spin)
    movement_form.addRow("Friction", panel.movement_friction_spin)

    movement_layout.addLayout(movement_form)

    for widget in (
        panel.movement_enabled_check,
        panel.movement_bounce_check,
        panel.movement_vx_spin,
        panel.movement_vy_spin,
        panel.movement_gravity_spin,
        panel.movement_friction_spin,
    ):
        if isinstance(widget, QCheckBox):
            widget.toggled.connect(panel.editor_movement_changed)
        else:
            widget.valueChanged.connect(panel.editor_movement_changed)

    panel.spritesheet_group = QGroupBox("Advanced")
    panel.spritesheet_layout = QVBoxLayout(panel.spritesheet_group)
    panel.spritesheet_layout.setContentsMargins(14, 18, 14, 14)
    panel.spritesheet_layout.setSpacing(10)

    panel.composite_group = QGroupBox("Advanced")
    panel.composite_layout = QVBoxLayout(panel.composite_group)
    panel.composite_layout.setContentsMargins(14, 18, 14, 14)
    panel.composite_layout.setSpacing(12)

    content_layout.addLayout(header_row)
    content_layout.addWidget(panel.editor_placeholder)
    content_layout.addWidget(panel.selected_group)
    content_layout.addWidget(panel.overlay_controls_group)
    content_layout.addWidget(panel.transform_group)
    content_layout.addWidget(panel.behavior_group)
    content_layout.addWidget(panel.action_group)
    content_layout.addWidget(panel.movement_group)
    content_layout.addWidget(panel.spritesheet_group)
    content_layout.addWidget(panel.composite_group)
    content_layout.addStretch()


def slider_row(panel, value_label, slider):
    row = QWidget()
    row.setObjectName("EditorRow")

    layout = QVBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    value_label.setMinimumWidth(120)

    layout.addWidget(value_label)
    layout.addWidget(slider)

    return row


def movement_spin(panel, minimum, maximum, step):
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setDecimals(1)
    spin.setSuffix(" px/s" if maximum > 50 else "")
    return spin


def set_editor_signals_blocked(panel, blocked):
    for widget in (
        panel.scale_slider,
        panel.opacity_slider,
        panel.speed_slider,
        panel.top_check,
        panel.click_check,
        panel.lock_check,
        panel.visibility_check,
        panel.action_enabled_check,
        panel.action_type_combo,
        panel.action_target_edit,
        panel.movement_enabled_check,
        panel.movement_bounce_check,
        panel.movement_vx_spin,
        panel.movement_vy_spin,
        panel.movement_gravity_spin,
        panel.movement_friction_spin,
    ):
        widget.blockSignals(blocked)


def load_editor(panel, window):
    panel.loading_editor = True
    panel.set_editor_signals_blocked(True)

    try:
        enabled = window is not None
        animated_types = {
            AssetType.GIF,
            AssetType.APNG,
            AssetType.WEBM,
            AssetType.FRAME_ANIMATION,
            AssetType.SPRITE_STRIP,
            AssetType.SPRITESHEET,
        }

        panel.clear_overlay_selection()

        if enabled:
            window.set_selected(True)

        panel.editor_name.setText(window.asset.name if enabled else "Select an overlay to edit it.")
        panel.editor_type.setText(f"Type: {window.asset_type}" if enabled else "")

        panel.editor_placeholder.setVisible(not enabled)
        panel.selected_group.setVisible(enabled)
        panel.overlay_controls_group.setVisible(enabled)
        panel.transform_group.setVisible(enabled)
        panel.behavior_group.setVisible(enabled)
        panel.action_group.setVisible(enabled)
        panel.movement_group.setVisible(enabled)

        panel.scale_slider.setEnabled(enabled)
        panel.opacity_slider.setEnabled(enabled)
        panel.speed_row.setVisible(enabled and window.asset_type in animated_types)
        panel.speed_slider.setEnabled(enabled and window.asset_type in animated_types)

        panel.top_check.setEnabled(enabled)
        panel.click_check.setEnabled(enabled)
        panel.lock_check.setEnabled(enabled)
        panel.visibility_check.setEnabled(enabled)

        panel.inspector_lock_button.setEnabled(enabled)
        panel.inspector_edit_button.setEnabled(enabled)
        panel.inspector_metadata_button.setEnabled(enabled)
        panel.inspector_remove_button.setEnabled(enabled)
        panel.reload_button.setEnabled(enabled)

        for widget in (
            panel.action_enabled_check,
            panel.action_type_combo,
            panel.action_target_edit,
            panel.action_browse_button,
            panel.action_test_button,
            panel.movement_enabled_check,
            panel.movement_bounce_check,
            panel.movement_vx_spin,
            panel.movement_vy_spin,
            panel.movement_gravity_spin,
            panel.movement_friction_spin,
        ):
            widget.setEnabled(enabled)

        panel.scale_slider.setValue(window.scale if enabled else 100)
        panel.opacity_slider.setValue(window.opacity if enabled else 100)
        panel.speed_slider.setValue(window.speed if enabled else 100)

        panel.top_check.setChecked(window.always_on_top if enabled else False)
        panel.click_check.setChecked(window.click_through if enabled else False)
        panel.lock_check.setChecked(window.locked if enabled else False)
        panel.visibility_check.setChecked(bool(getattr(window, "intended_visible", False)) if enabled else False)

        panel.inspector_lock_button.setText("Unlock" if enabled and window.locked else "Lock")

        action = normalized_action_config(window.action if enabled else None)
        panel.action_enabled_check.setChecked(action["enabled"])

        action_index = panel.action_type_combo.findData(action["type"])
        panel.action_type_combo.setCurrentIndex(max(0, action_index))
        panel.action_target_edit.setText(action["target"])

        movement = normalized_movement_config(window.movement if enabled else None)
        panel.movement_enabled_check.setChecked(movement["enabled"])
        panel.movement_bounce_check.setChecked(movement["bounce"])
        panel.movement_vx_spin.setValue(movement["velocity_x"])
        panel.movement_vy_spin.setValue(movement["velocity_y"])
        panel.movement_gravity_spin.setValue(movement["gravity"])
        panel.movement_friction_spin.setValue(movement["friction"])

        panel.scale_label.setText(f"Scale: {panel.scale_slider.value()}%")
        panel.opacity_label.setText(f"Opacity: {panel.opacity_slider.value()}%")
        panel.speed_label.setText(f"Speed: {panel.speed_slider.value()}%")

        panel.rebuild_runtime_editor(window if enabled else None)

    finally:
        panel.set_editor_signals_blocked(False)
        panel.loading_editor = False


def rebuild_runtime_editor(panel, window):
    panel.clear_layout(panel.spritesheet_layout)
    panel.clear_layout(panel.composite_layout)

    panel.layer_value_sliders = {}
    panel.animation_combo = None

    panel.spritesheet_group.hide()
    panel.composite_group.hide()

    if window is None:
        return

    if window.asset_type == AssetType.COMPOSITE_UI:
        values = window.clipped_layer_values()

        if not values:
            return

        for name, value in values.items():
            display_name = panel.display_layer_name(name)

            label = QLabel(f"{display_name}: {round(value * 100)}%")

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(round(value * 100))
            slider.valueChanged.connect(
                lambda slider_value, layer=name, layer_label=label, name_text=display_name: (
                    panel.editor_layer_value_changed(
                        layer,
                        slider_value,
                        layer_label,
                        name_text,
                    )
                )
            )

            panel.layer_value_sliders[name] = slider
            panel.composite_layout.addWidget(panel.slider_row(label, slider))

        panel.composite_group.show()
        return

    if window.asset_type == AssetType.SPRITESHEET:
        animations = window.available_animations()

        if not animations:
            return

        panel.animation_combo = QComboBox()
        panel.animation_combo.addItems(animations)

        if window.current_animation in animations:
            panel.animation_combo.setCurrentText(window.current_animation)

        panel.animation_combo.currentTextChanged.connect(panel.editor_animation_changed)

        panel.spritesheet_layout.addWidget(QLabel("Animation"))
        panel.spritesheet_layout.addWidget(panel.animation_combo)
        panel.spritesheet_group.show()
        return


def clear_layout(panel, layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()

        if widget is not None:
            widget.deleteLater()


def display_layer_name(panel, name):
    return str(name).replace("_", " ").strip().title() or "Layer"


def mark_saved(panel):
    if panel.loading_editor:
        return

    panel.saved_label.setText("Saved")
    panel.saved_timer.start(1400)


def editor_layer_value_changed(panel, layer_name, slider_value, label, display_name):
    label.setText(f"{display_name}: {slider_value}%")

    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        try:
            panel.selected_window.set_layer_value(layer_name, slider_value / 100)
            panel.mark_saved()
        except Exception as exc:
            log_warning("Unable to update composite layer value %s: %s", layer_name, exc)


def editor_animation_changed(panel, animation_name):
    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        if not panel.selected_window.set_animation(animation_name):
            log_warning("Unable to switch to animation: %s", animation_name)
            QMessageBox.warning(panel, "Animation", f"Unable to switch to animation: {animation_name}")
        else:
            panel.mark_saved()


def reload_selected_asset(panel):
    if panel.selected_window not in state.WINDOWS:
        return

    asset = detect_asset(panel.selected_window.asset_path)

    if asset is None:
        log_warning("Unable to reload selected asset definition: %s", panel.selected_window.asset_path)
        QMessageBox.warning(panel, "Reload Asset", "Unable to reload this asset definition.")
        return

    if not panel.selected_window.reload_asset_definition(asset):
        log_warning("Reload failed for selected asset: %s", panel.selected_window.asset_path)
        QMessageBox.warning(panel, "Reload Asset", "Reload failed. The running overlay was kept unchanged.")
        return

    panel.load_editor(panel.selected_window)
    panel.refresh_active()


def editor_scale_changed(panel, value):
    panel.scale_label.setText(f"Scale: {value}%")

    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.set_scale(value)
        panel.mark_saved()


def editor_opacity_changed(panel, value):
    panel.opacity_label.setText(f"Opacity: {value}%")

    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.set_opacity_percent(value)
        panel.mark_saved()


def editor_speed_changed(panel, value):
    panel.speed_label.setText(f"Speed: {value}%")

    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.set_speed(value)
        panel.mark_saved()


def editor_top_changed(panel, checked):
    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.always_on_top = checked
        panel.selected_window.apply_window_flags()
        persist_runtime_state("overlay_always_on_top_changed")
        panel.mark_saved()


def editor_click_changed(panel, checked):
    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.click_through = checked
        panel.selected_window.apply_click_through()
        persist_runtime_state("overlay_click_through_changed")
        panel.mark_saved()


def editor_visibility_changed(panel, checked):
    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.set_intended_visible(checked)
        persist_runtime_state("overlay_visibility_changed")
        panel.refresh_active()
        panel.mark_saved()


def editor_lock_changed(panel, checked):
    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.locked = checked
        panel.inspector_lock_button.setText("Unlock" if checked else "Lock")
        persist_runtime_state("overlay_lock_changed")
        panel.refresh_active()
        panel.mark_saved()


def current_action_config(panel):
    return {
        "enabled": panel.action_enabled_check.isChecked(),
        "type": panel.action_type_combo.currentData() or ACTION_OPEN_FILE,
        "target": panel.action_target_edit.text().strip(),
    }


def editor_action_changed(panel):
    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.set_action(panel.current_action_config())
        panel.mark_saved()


def browse_action_target(panel):
    action_type = panel.action_type_combo.currentData()

    if action_type == ACTION_OPEN_URL:
        QMessageBox.information(panel, "Action", "Enter an http or https URL in the target field.")
        return

    if action_type == ACTION_OPEN_FOLDER:
        path = QFileDialog.getExistingDirectory(panel, "Choose Action Folder", str(BASE_DIR))
    elif action_type == ACTION_LAUNCH_APP:
        path, _ = QFileDialog.getOpenFileName(
            panel,
            "Choose Application",
            str(BASE_DIR),
            "Applications (*.exe);;All files (*)",
        )
    else:
        path, _ = QFileDialog.getOpenFileName(
            panel,
            "Choose Action File",
            str(BASE_DIR),
            "All files (*)",
        )

    if path:
        panel.action_target_edit.setText(path)
        panel.editor_action_changed()


def test_selected_action(panel):
    if panel.selected_window not in state.WINDOWS:
        return

    panel.editor_action_changed()

    ok, message = panel.selected_window.run_action()

    if not ok:
        QMessageBox.warning(panel, "Run Action", message)


def current_movement_config(panel):
    return {
        "enabled": panel.movement_enabled_check.isChecked(),
        "velocity_x": panel.movement_vx_spin.value(),
        "velocity_y": panel.movement_vy_spin.value(),
        "bounce": panel.movement_bounce_check.isChecked(),
        "gravity": panel.movement_gravity_spin.value(),
        "friction": panel.movement_friction_spin.value(),
    }


def editor_movement_changed(panel):
    if not panel.loading_editor and panel.selected_window in state.WINDOWS:
        panel.selected_window.set_movement(panel.current_movement_config())
        panel.mark_saved()
