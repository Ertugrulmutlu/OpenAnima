from pathlib import Path


ALPHA_MODE_ELEMENT_ID = b"\x53\xc0"


def webm_likely_has_alpha(path):
    path = Path(path)
    if path.suffix.lower() != ".webm":
        return False
    try:
        data = path.read_bytes()
    except OSError:
        return False

    offset = 0
    while True:
        index = data.find(ALPHA_MODE_ELEMENT_ID, offset)
        if index < 0:
            return False
        value = _read_ebml_uint_after_id(data, index + len(ALPHA_MODE_ELEMENT_ID))
        if value is not None:
            return value != 0
        offset = index + 1


def _read_ebml_uint_after_id(data, offset):
    length_size, length = _read_vint(data, offset, mask_marker=True)
    if length_size <= 0 or length <= 0:
        return None
    value_start = offset + length_size
    value_end = value_start + length
    if value_end > len(data):
        return None
    value = 0
    for byte in data[value_start:value_end]:
        value = (value << 8) | byte
    return value


def _read_vint(data, offset, mask_marker):
    if offset >= len(data):
        return 0, 0
    first = data[offset]
    marker = 0x80
    size = 1
    while size <= 8 and not (first & marker):
        marker >>= 1
        size += 1
    if size > 8 or offset + size > len(data):
        return 0, 0
    value = first & (~marker if mask_marker else 0xFF)
    for index in range(1, size):
        value = (value << 8) | data[offset + index]
    return size, value
