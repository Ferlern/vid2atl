import json
import contextlib


def try_loads(json_string: str):
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(json_string)
    json_string = (json_string.replace(', ...', '').replace(',...', '').replace(
        '"end": "end"', '"end": "00:00:00"'
    ))
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(json_string)
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(json_string.rstrip('}'))
    return json.loads(json_string.rstrip(']'))
