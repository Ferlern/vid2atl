from typing import Optional

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass


_YOUTUBE_REGEX = r'^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*'
_TIME_REGEX = r'^\d{1,2}:\d\d:\d\d$'


@dataclass
class TranscriptEntry:
    text: str
    start: float
    duration: float


class ArticleRequest(BaseModel):
    number_of_paragraphs: int
    url: str = Field(regex=_YOUTUBE_REGEX)
    lang: str = 'en'


class ArticleTopic(BaseModel):
    subtitle: str
    start: str = Field(regex=_TIME_REGEX)
    end: str = Field(regex=_TIME_REGEX)
    text: str
    image: Optional[str] = None


class Article(BaseModel):
    title: str
    topics: list[ArticleTopic]
