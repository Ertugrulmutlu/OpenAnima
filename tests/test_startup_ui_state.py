from openanima_app.runtime import state
from openanima_app.app import apply_control_panel_startup_state


class FakeControlPanel:
    def __init__(self):
        self.restored_ui = None
        self.shown = False
        self.hidden = False
        self.raised = False
        self.activated = False

    def restore_ui_state(self, ui):
        self.restored_ui = ui

    def show(self):
        self.shown = True

    def hide(self):
        self.hidden = True

    def raise_(self):
        self.raised = True

    def activateWindow(self):
        self.activated = True


def test_startup_respects_saved_hidden_control_panel_state():
    old_control_panel = state.CONTROL_PANEL
    try:
        panel = FakeControlPanel()
        state.CONTROL_PANEL = panel

        apply_control_panel_startup_state({"control_panel_visible": False, "last_page": "Desktop"})

        assert panel.restored_ui == {"control_panel_visible": False, "last_page": "Desktop"}
        assert panel.hidden is True
        assert panel.shown is False
    finally:
        state.CONTROL_PANEL = old_control_panel


def test_startup_shows_control_panel_by_default():
    old_control_panel = state.CONTROL_PANEL
    try:
        panel = FakeControlPanel()
        state.CONTROL_PANEL = panel

        apply_control_panel_startup_state({})

        assert panel.shown is True
        assert panel.raised is True
        assert panel.activated is True
        assert panel.hidden is False
    finally:
        state.CONTROL_PANEL = old_control_panel
