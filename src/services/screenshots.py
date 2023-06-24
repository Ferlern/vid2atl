from typing import Sequence

import cv2
from vidgear.gears import CamGear

from src.logger import get_logger


logger = get_logger()


def extract_frames(
    url: str,
    screenshot_periods: Sequence[tuple[int, int]],
) -> list[list[bytes]]:
    stream = CamGear(
        source=url,  # type: ignore
        stream_mode=True,
        time_delay=1,
    ).start()

    currentframe = 0
    second = 0
    frames = []
    for start, end in screenshot_periods:
        logger.debug('Creating new selector, start=%d, end=%d, frame=%d, second=%d',
                     start, end, currentframe, second)
        selector = UniformSelector(3, start, end)
        perios_screenshots = []

        while True:
            frame = stream.read()
            currentframe += 1
            if frame is None:
                break

            second = int(currentframe // stream.framerate)

            if selector.check(frame, second):
                logger.info('Saving frame %d for %s', currentframe, url)
                _, buffer = cv2.imencode('.png', frame)
                perios_screenshots.append(buffer.tobytes())

            if second > end:
                break

        frames.append(perios_screenshots)

    stream.stop()
    return frames


class UniformSelector:
    def __init__(
        self,
        screenshots_count: int,
        start: int,
        end: int
    ) -> None:
        self.screenshots_count = screenshots_count
        self.start = start
        self.end = end
        self._saved = set()

        seconds_per_screenshot = int((end - start) / screenshots_count)
        first = int(start + seconds_per_screenshot / 2)

        self._to_save = [first + seconds_per_screenshot*n for n in range(screenshots_count)]

    def check(self, _, second: int) -> bool:
        if all((
            second in self._to_save,
            second not in self._saved
        )):
            # logger.debug('second %f denied', )
            self._saved.add(second)
            return True
        return False
