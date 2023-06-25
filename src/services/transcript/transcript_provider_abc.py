from __future__ import annotations
from typing import TYPE_CHECKING
from abc import abstractmethod, ABC

from src.schemas import TranscriptEntry

if TYPE_CHECKING:
    from aiohttp import ClientSession


class TranscriptProvider(ABC):
    """Класс для инкапсуляции лоигики получения текста из видео"""
    def __init__(
        self,
        url: str,
        session: ClientSession,
    ) -> None:
        self.url = url
        self.session = session

    @abstractmethod
    async def get_transcript(self) -> list[TranscriptEntry]:
        raise NotImplementedError
