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
        SelectorType.UNIFORM: UniformSelector,
        SelectorType.SIMILARITY: SimilaritySelector,
        SelectorType.CIRCLE_RECTANGLE: CircleRectangleSelecor,
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
    def feed(self, frame: cv2.Mat, second: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_result(self) -> list[cv2.Mat]:
        raise NotImplementedError


class UniformSelector(FrameSelector):
    """Вибирает скриншоты равномерно на всём промежутке"""

    def __init__(
        self,
        screenshots_count: int,
        start: int,
        end: int
    ) -> None:
        super().__init__(screenshots_count, start, end)

        self._saved: dict[int, cv2.Mat] = {}
        seconds_per_screenshot = int((end - start) / screenshots_count)
        first = int(start + seconds_per_screenshot / 2)

        self._to_save = [first + seconds_per_screenshot*n for n in range(screenshots_count)]

    def feed(self, frame: cv2.Mat, second: int) -> None:
        if all((
            second in self._to_save,
            second not in self._saved
        )):
            # TODO remove
            logger.debug('save frame at second %d', second)
            self._saved[second] = frame

    def get_result(self) -> list[cv2.Mat]:
        return list(self._saved.values())


class SimilaritySelector(FrameSelector):
    """
    Вибирает скриншоты исходя из их схожести с предыдущим.
    В приоритете скриншоты, которые наиболее похожи на предыдущие.
    На данный момент полностью игнорирует время создания скриншота,
    из-за чего могут быть выбраны скриншоты в ряд.
    """

    def __init__(
        self,
        screenshots_count: int,
        start: int,
        end: int
    ) -> None:
        super().__init__(screenshots_count, start, end)
        self._candidates: list[tuple[cv2.Mat, cv2.Mat]] = []
        self._last_second = 0

    def feed(self, frame: cv2.Mat, second: int) -> None:
        if self._candidates and second - self._last_second <= 5:
            return

        # TODO remove
        logger.debug('calculate hist for frame at second %d', second)
        hist = cv2.calcHist([frame], [0], None, [256], [0, 256])
        self._candidates.append((frame, hist))
        self._last_second = second

    def get_result(self) -> list[cv2.Mat]:
        rated_candidates = []
        for current_candidate, next_candidate in zip(self._candidates, self._candidates[1:]):
            rating = cv2.compareHist(
                current_candidate[1], next_candidate[1], cv2.HISTCMP_BHATTACHARYYA
            )
            rated_candidates.append((rating, current_candidate[0]))
        rated_candidates.sort(key=lambda candidate: candidate[0])
        logger.debug([cand[0] for cand in rated_candidates])
        return [candidate[1] for candidate in rated_candidates[:self.screenshots_count]]


class CircleRectangleSelecor(FrameSelector):
    """
    Вибирает скриншоты исходя из количества кругов и четырёхугольников на них.
    Это частая примета информативности. В приоритете скриншоты с большим числом фигур.
    На данный момент полностью игнорирует время создания скриншота,
    из-за чего могут быть выбраны скриншоты в ряд.
    """

    def __init__(
        self,
        screenshots_count: int,
        start: int,
        end: int
    ) -> None:
        super().__init__(screenshots_count, start, end)
        self._candidates: list[tuple[int, cv2.Mat]] = []
        self._last_second = 0

    def feed(self, frame: cv2.Mat, second: int) -> None:
        if second - self._last_second <= 10:
            return

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thresh_frame = cv2.threshold(gray_frame, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        circles = cv2.HoughCircles(gray_frame, cv2.HOUGH_GRADIENT, 1.2, 100)
        rectangles = cv2.findContours(thresh_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rectangles = rectangles[0] if len(rectangles) == 2 else rectangles[1]
        self._candidates.append((circles.shape[2] + len(rectangles), frame))
        self._last_second = second

    def get_result(self) -> list[cv2.Mat]:
        candidates = self._candidates
        candidates.sort(reverse=True, key=lambda candidate: candidate[0])
        return [candidate[1] for candidate in candidates[:self.screenshots_count]]


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
            selector.feed(frame, second)

            if second > end:
                break

        result = selector.get_result()
        for frame in result:
            _, buffer = cv2.imencode('.png', frame)
            period_screenshots.append(buffer.tobytes())
        frames.append(period_screenshots)

    stream.stop()
    return frames
