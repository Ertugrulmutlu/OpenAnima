from PySide6.QtCore import QPoint

from openanima_app.runtime import recovery, state


class FakeWindow:
    def __init__(self):
        self.click_through = True
        self.locked = True
        self.visible = False
        self.raised = False
        self.pos = QPoint(0, 0)

    def setVisible(self, visible):
        self.visible = visible

    def raise_(self):
        self.raised = True

    def apply_click_through(self):
        self.click_applied = True

    def centered_on_primary_screen(self):
        return QPoint(100, 100)

    def clamped_position(self, pos):
        return pos

    def move(self, pos):
        self.pos = pos


def test_recovery_actions_update_overlay_state(monkeypatch):
    saved = []
    window = FakeWindow()
    state.WINDOWS = [window]
    monkeypatch.setattr(recovery, "persist_runtime_state", lambda reason, windows=None, force_empty=False: saved.append(reason))

    recovery.show_all_overlays()
    recovery.disable_click_through_for_all()
    recovery.unlock_all_overlays()
    recovery.bring_all_overlays_to_center()

    assert window.visible is True
    assert window.raised is True
    assert window.click_through is False
    assert window.click_applied is True
    assert window.locked is False
    assert window.pos == QPoint(100, 100)
    assert saved == [
        "recovery_show_all_overlays",
        "recovery_disable_click_through",
        "recovery_unlock_all",
        "recovery_bring_all_to_center",
    ]

    state.WINDOWS = []
