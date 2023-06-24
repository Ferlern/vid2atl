from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass


_YOUTUBE_REGEX = r'^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*'
_TIME_REGEX = r'^\d{1,2}:\d{1,2}:\d{1,2}$'


@dataclass
class TranscriptEntry:
    text: str
    start: float
    duration: float


class PersonType(Enum):
    FIRST = 'first'
    THIRD = 'third'


class ArticleRequest(BaseModel):
    number_of_paragraphs: int = 0
    url: str = Field(regex=_YOUTUBE_REGEX)
    force_whisper: bool = False


class ArticleTopic(BaseModel):
    start: str = Field(regex=_TIME_REGEX)
    end: str = Field(regex=_TIME_REGEX)
    title: Optional[str] = None
    paragraphs: Optional[str] = None
    images: list[str] = []


class Article(BaseModel):
    title: str
    description: str
    topics: list[ArticleTopic]
