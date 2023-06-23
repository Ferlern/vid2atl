from __future__ import annotations
import asyncio
import base64
import json
from datetime import timedelta
from typing import TYPE_CHECKING, Iterable

from fastapi.concurrency import run_in_threadpool
from pydantic.tools import parse_obj_as

from src.schemas import Article, ArticleTopic, TranscriptEntry, PersonType, ArticleRequest
from src.logger import get_logger
from .gpt import gpt_request
from .translation import translate_text
from .transcript import get_english_transcript
from .screenshots import extract_frames

if TYPE_CHECKING:
    from aiohttp import ClientSession

logger = get_logger()
PROMPT = """
Your task is to create an article from video subtitles.
You will receive subtitles in the following format:
hh:mm:ss - subtitles
hh:mm:ss - subtitles
...

Article must have title. The article should be divided into {number_of_subtopics} subtopics with headings.
Try to make subtopics of the same size. If there are too many topics in the subtitles for the specified number of article subtopics, put several topics in one. For example "Arrays and Hash tables". If there are too few topics in subtitles, divide them into parts, for example "Arrays (intro)" and "Arrays (continued)"
{aditional_prompt}
Respond with valid JSON in the following format (Substitude text in [square brackets]):
{{"title": "[title]", "topics": [{{"subtitle": "[subtitle]", "start": "[hh:mm:ss]", "end": "[hh:mm:ss]", "text": "[Describe in detail what was said in {person} person]"}}, ...]}}"""  # noqa: E501


async def generate_article(
    request: ArticleRequest,
    session: ClientSession
) -> Article:
    url = request.url
    logger.info('generating article for %s', url)
    logger.info('gathering english transcript for %s', url)
    transcript = await get_english_transcript(url, request.force_whisper, session)
    logger.debug('transcript for %s %s', url, transcript)
    logger.info('generating article text for %s', url)
    article = await _generate_article_text(
        transcript,
        request.number_of_paragraphs,
        person=request.person,
        aditional_prompt=request.aditional_prompt,
        session=session,
    )
    screenshot_seconds = []
    for topic in article.topics:
        mid_sec = (_get_sec(topic.start) + _get_sec(topic.end)) // 2
        screenshot_seconds.append(int(mid_sec))
    logger.info('gathering frames and translating to %s for %s', request.lang, url)
    tasks = [run_in_threadpool(extract_frames, url, screenshot_seconds)]
    if request.lang != 'en':
        tasks.append(translate_article(article, session=session, lang=request.lang))  # type: ignore
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
        *[_translate_article_topic(
            topic,
            lang=lang,
            session=session
        ) for topic in article.topics]
    )


def _format_transcript(transcript_entries: Iterable[TranscriptEntry]) -> list[str]:
    result = []
    for entry in transcript_entries:
        start = entry.start
        text = entry.text
        result.append(f'{timedelta(seconds=int(start))} - {text}')
    return result


async def _generate_article_text(
    transcript_entries: Iterable[TranscriptEntry],
    number_of_paragraphs: int,
    person: PersonType,
    aditional_prompt: str,
    session: ClientSession,
) -> Article:
    subtitles = _format_transcript(transcript_entries)
    prompt = PROMPT.format(
        number_of_subtopics=number_of_paragraphs,
        aditional_prompt=aditional_prompt,
        person=person.value,
    )
    resp = await gpt_request(prompt, '\n'.join(subtitles), session)
    article_dict = json.loads(resp)
    return parse_obj_as(Article, article_dict)


async def _translate_article_topic(
    topic: ArticleTopic,
    lang: str,
    session: ClientSession,
) -> None:
    topic.subtitle, topic.text = await asyncio.gather(
        translate_text(topic.subtitle, src='en', dest=lang, session=session),
        translate_text(topic.text, src='en', dest=lang, session=session),
    )


def _get_sec(time_str: str) -> int:
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)
