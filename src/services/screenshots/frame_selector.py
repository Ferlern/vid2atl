from __future__ import annotations
from abc import abstractmethod, ABC
from typing import Sequence

import cv2
from vidgear.gears import CamGear

from src.schemas import SelectorType
from src.logger import get_logger


logger = get_logger()


def get_selector(selector_type: SelectorType) -> type[FrameSelector]:
    selectors_mapping = {
        SelectorType.UNIFORM: UniformSelector
    }
    return selectors_mapping[selector_type]


class FrameSelector(ABC):
    def __init__(
        self,
        screenshots_count: int,
        start: int,
        end: int
    ) -> None:
        self.screenshots_count = screenshots_count
        self.start = start
        self.end = end

    @abstractmethod
    def check(self, frame, second: int) -> bool:
        raise NotImplementedError


class UniformSelector(FrameSelector):
    def __init__(
        self,
        screenshots_count: int,
        start: int,
        end: int
    ) -> None:
        super().__init__(screenshots_count, start, end)

        self._saved = set()
        seconds_per_screenshot = int((end - start) / screenshots_count)
        first = int(start + seconds_per_screenshot / 2)

        self._to_save = [first + seconds_per_screenshot*n for n in range(screenshots_count)]

    def check(self, _, second: int) -> bool:
        if all((
            second in self._to_save,
            second not in self._saved
        )):
            self._saved.add(second)
            return True
        return False


def extract_frames(
    url: str,
    screenshot_periods: Sequence[tuple[int, int]],
    number_of_screenshots: int,
    selector_type: SelectorType,
) -> list[list[bytes]]:
    selector_class = get_selector(selector_type)
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
        selector = selector_class(number_of_screenshots, start, end)
        period_screenshots = []

        while True:
            frame = stream.read()
            currentframe += 1
            if frame is None:
                break

            second = int(currentframe // stream.framerate)

            if selector.check(frame, second):
                logger.info('Saving frame %d for %s', currentframe, url)
                _, buffer = cv2.imencode('.png', frame)
                period_screenshots.append(buffer.tobytes())

            if second > end:
                break

        frames.append(period_screenshots)

    stream.stop()
    return frames
