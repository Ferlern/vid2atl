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


class PostrocessorType(str, Enum):
    BASE64 = 'base64'
    IMGUR = 'imgur'


class SelectorType(str, Enum):
    UNIFORM = 'uniform'


class ArticleRequest(BaseModel):
    number_of_paragraphs: int = Field(ge=2, default=3)
    number_of_screenshots: int = Field(ge=1, default=3)
    url: str = Field(regex=_YOUTUBE_REGEX)
    start: int = Field(ge=0, default=0)
    end: int = Field(ge=0, default=0)
    force_whisper: bool = False
    selector: SelectorType = SelectorType.UNIFORM
    image_format: PostrocessorType = PostrocessorType.BASE64


class ArticleTopic(BaseModel):
    start: str = Field(regex=_TIME_REGEX)
    end: str = Field(regex=_TIME_REGEX)
    title: Optional[str] = None
    paragraphs: Optional[str] = None
    images: list[str] = []


class GenerationTime(BaseModel):
    total: float = 0
    images: float = 0
    title: float = 0
    transcript: float = 0
    content: float = 0


class Article(BaseModel):
    title: str
    description: str
    topics: list[ArticleTopic]
    generation_time: GenerationTime
