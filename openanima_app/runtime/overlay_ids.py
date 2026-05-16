import re
import secrets

from . import state


PERSISTENT_ID_PATTERN = re.compile(r"^oa_[0-9a-f]{12}$")


def next_runtime_id():
    value = f"overlay_{state.LOCAL_API_NEXT_RUNTIME_ID:06d}"
    state.LOCAL_API_NEXT_RUNTIME_ID += 1
    return value


def is_valid_persistent_id(value):
    return isinstance(value, str) and bool(PERSISTENT_ID_PATTERN.fullmatch(value))


def generate_persistent_id():
    existing = {str(getattr(window, "persistent_id", "")) for window in state.WINDOWS}
    while True:
        value = f"oa_{secrets.token_hex(6)}"
        if value not in existing:
            return value


def normalize_api_alias(value):
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    return normalized[:64]


def persistent_id_from_config(config):
    if isinstance(config, dict) and is_valid_persistent_id(config.get("persistent_id")):
        return config["persistent_id"]
    return generate_persistent_id()
