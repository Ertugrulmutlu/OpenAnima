from openanima_app import state
from openanima_app.logging_utils import log_error, log_warning, recent_warnings_and_errors


def test_warning_is_recorded_for_diagnostics():
    state.CONFIG_WARNINGS.clear()
    state.RECENT_DIAGNOSTICS.clear()

    log_warning("Config warning for %s", "tests")

    assert state.CONFIG_WARNINGS == ["Config warning for tests"]
    assert recent_warnings_and_errors() == [
        {"level": "WARNING", "message": "Config warning for tests"}
    ]


def test_recent_diagnostics_filters_info_messages():
    state.RECENT_DIAGNOSTICS.clear()
    state.RECENT_DIAGNOSTICS.append({"level": "INFO", "message": "startup"})

    log_error("Failure for %s", "tests")

    assert recent_warnings_and_errors() == [
        {"level": "ERROR", "message": "Failure for tests"}
    ]
