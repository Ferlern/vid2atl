import json
import contextlib


def try_loads(json_string: str):
    """
    Пытается исправить частые ошибки в JSON ответе от нейросети.
    Это проблемная часть проекта, правильный JSON обязателен.
    Перед массовым использованием это нужно как-то исправить или избежать необходимости json ответа
    """
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(json_string)
    json_string = (
        json_string.
        replace(', ...', '').
        replace(',...', '').
        replace('"end": ...', '"end": "0:00:00').
        replace('"end": "end"', '"end": "00:00:00"')
    )
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(json_string)
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(json_string.rstrip('}'))
    return json.loads(json_string.rstrip(']'))
