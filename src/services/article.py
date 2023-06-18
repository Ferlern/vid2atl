from __future__ import annotations
import asyncio
import base64
from typing import TYPE_CHECKING
from fastapi.concurrency import run_in_threadpool
from src.schemas import Article, ArticleTopic
from src.logger import get_logger
from .translation import translate_text
from .gpt import generate_article_text
from .transcript import get_english_transcript
from .screenshots import extract_frames

if TYPE_CHECKING:
    from aiohttp import ClientSession

logger = get_logger()


async def generate_article(
    url: str,
    number_of_paragraphs: int,
    lang: str,
    session: ClientSession
) -> Article:
    logger.info('generating article for %s', url)
    logger.info('gathering english transcript for %s', url)
    transcript = await get_english_transcript(url, session)
    logger.info('generating article text for %s', url)
    article = await generate_article_text(transcript, number_of_paragraphs, session)
    screenshot_seconds = []
    for topic in article.topics:
        mid_sec = (get_sec(topic.start) + get_sec(topic.end)) // 2
        screenshot_seconds.append(int(mid_sec))
    logger.info('gathering frames and translating to %s for %s', lang, url)
    tasks = [run_in_threadpool(extract_frames, url, screenshot_seconds)]
    if lang != 'en':
        tasks.append(translate_article(article, session=session, lang=lang))  # type: ignore
    frames, *_ = await asyncio.gather(*tasks)
    logger.info('encoding images for %s', url)
    for topic, frame in zip(article.topics, frames):
        encoded_frame = base64.b64encode(frame)
        topic.image = encoded_frame.decode('utf-8')
    return article


async def translate_article(
    article: Article,
    lang: str,
    session: ClientSession,
) -> None:
    article.title, *_ = await asyncio.gather(
        translate_text(article.title, src='en', dest=lang, session=session),
        *[translate_article_topic(
            topic,
            lang=lang,
            session=session
        ) for topic in article.topics]
    )


async def translate_article_topic(
    topic: ArticleTopic,
    lang: str,
    session: ClientSession,
) -> None:
    topic.subtitle, topic.text = await asyncio.gather(
        translate_text(topic.subtitle, src='en', dest=lang, session=session),
        translate_text(topic.text, src='en', dest=lang, session=session),
    )


def get_sec(time_str: str) -> int:
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)
