from typing import Sequence

import cv2
from vidgear.gears import CamGear

from src.logger import get_logger


logger = get_logger()


def extract_frames(
    url: str,
    screenshot_seconds: Sequence[int],
) -> list[bytes]:
    stream = CamGear(
        source=url,  # type: ignore
        stream_mode=True,
        time_delay=1,
    ).start()

    currentframe = 0
    frames = []
    captured = set()

    while True:
        frame = stream.read()
        currentframe += 1
        if frame is None:
            break

        second = currentframe // stream.framerate
        if second not in screenshot_seconds or second in captured:
            continue

        logger.info('Saving frame %d for %s', currentframe, url)
        _, buffer = cv2.imencode('.png', frame)
        frames.append(buffer.tobytes())
        captured.add(second)

    stream.stop()
    return frames
