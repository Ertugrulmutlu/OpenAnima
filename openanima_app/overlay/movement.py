from PySide6.QtCore import QPoint

DEFAULT_MOVEMENT = {
    "enabled": False,
    "velocity_x": 0.0,
    "velocity_y": 0.0,
    "bounce": True,
    "gravity": 0.0,
    "friction": 0.0,
}


def normalized_movement_config(config):
    if not isinstance(config, dict):
        return dict(DEFAULT_MOVEMENT)

    normalized = {
        "enabled": bool(config.get("enabled", False)),
        "velocity_x": _float(config.get("velocity_x"), DEFAULT_MOVEMENT["velocity_x"], -2000.0, 2000.0),
        "velocity_y": _float(config.get("velocity_y"), DEFAULT_MOVEMENT["velocity_y"], -2000.0, 2000.0),
        "bounce": bool(config.get("bounce", True)),
        "gravity": _float(config.get("gravity"), DEFAULT_MOVEMENT["gravity"], -2000.0, 2000.0),
        "friction": _float(config.get("friction"), DEFAULT_MOVEMENT["friction"], 0.0, 100.0),
    }
    for key, value in config.items():
        if key not in normalized and (isinstance(value, (str, int, float, bool)) or value is None):
            normalized[key] = value
    return normalized


def _float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))


def set_movement(window, config):
    from ..assets import persist_runtime_state

    window.movement = normalized_movement_config(config)
    window.runtime_velocity_x = float(window.movement.get("velocity_x", 0.0))
    window.runtime_velocity_y = float(window.movement.get("velocity_y", 0.0))
    window.update_movement_timer()
    persist_runtime_state("movement_changed")


def update_movement_timer(window):
    if window.movement.get("enabled"):
        window.runtime_velocity_x = float(window.movement.get("velocity_x", 0.0))
        window.runtime_velocity_y = float(window.movement.get("velocity_y", 0.0))
        window.movement_clock.restart()
        window.movement_timer.start()
    else:
        window.movement_timer.stop()


def advance_movement(window):
    if not window.movement.get("enabled"):
        window.movement_timer.stop()
        return

    elapsed = max(0.001, min(0.1, window.movement_clock.restart() / 1000.0))
    vx = window.runtime_velocity_x
    vy = window.runtime_velocity_y + float(window.movement.get("gravity", 0.0)) * elapsed
    friction = float(window.movement.get("friction", 0.0))
    if friction > 0:
        damping = max(0.0, 1.0 - friction * elapsed)
        vx *= damping
        vy *= damping

    next_x = window.x() + vx * elapsed
    next_y = window.y() + vy * elapsed
    geometry = window.available_geometry()
    if geometry is not None and window.movement.get("bounce", True):
        min_x = geometry.left()
        min_y = geometry.top()
        max_x = max(min_x, geometry.right() - max(1, window.width()) + 1)
        max_y = max(min_y, geometry.bottom() - max(1, window.height()) + 1)
        if next_x < min_x or next_x > max_x:
            vx *= -1
            next_x = min(max(next_x, min_x), max_x)
        if next_y < min_y or next_y > max_y:
            vy *= -1
            next_y = min(max(next_y, min_y), max_y)

    window.runtime_velocity_x = vx
    window.runtime_velocity_y = vy
    window.move(window.clamped_position(QPoint(round(next_x), round(next_y))))
