from __future__ import annotations
from typing import TYPE_CHECKING
import os
import json
from datetime import timedelta
from dotenv import load_dotenv
from pydantic.tools import parse_obj_as
from src.schemas import Article, TranscriptEntry
from src.logger import get_logger

if TYPE_CHECKING:
    from aiohttp import ClientSession

load_dotenv()

TOKEN = os.getenv('API_TOKEN') or ''
PATH = os.getenv('API_ENDPOINT') or ''
if not TOKEN or not PATH:
    raise RuntimeError('Invalid .env')

PROMPT = """
Your task is to create an article from video subtitles.
You will receive subtitles in the following format:
hh:mm:ss - subtitles
hh:mm:ss - subtitles
...

Article must have title. The article should be divided into {} subtopics with headings. Respond with JSON in the following format (Substitude text in [square brackets]):
{{"title": "[title]", "topics": [{{"subtitle": "[subtitle]", "start": "[hh:mm:ss]", "end": "[hh:mm:ss]", "text": "[retelling of what was said in third person]"}}, ...]}}"""

logger = get_logger()


async def gpt_request(
    system: str,
    user: str,
    session: ClientSession,
) -> str:
    payload = {
        "messages": [
            {
                "role": "system",
                "content": system
            },
            {
                "role": "user",
                "content": user,
            },
        ],
        # "model": "gpt-4",
        # "model": "claude-instant-100k",
        # "model": "gpt-3.5-turbo",
        "model": "gpt-3.5-turbo-16k",
        "temperature": 1,
        "presence_penalty": 0,
        "top_p": 1,
        "frequency_penalty": 0,
        "stream": False,
    }
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'text/event-stream',
    }

    async with session.post(PATH, headers=headers, json=payload) as response:
        text = (await response.text()).lstrip('data:').rstrip('\n')
    resp_json = json.loads(text)
    content = resp_json['choices'][0]['message']['content']
    logger.debug('Model response: %s', content)
    return content


def format_transcript(transcript_entries: list[TranscriptEntry]) -> list[str]:
    result = []
    for entry in transcript_entries:
        start = entry.start
        text = entry.text
        result.append(f'{timedelta(seconds=int(start))} - {text}')
    return result


async def generate_article_text(
    transcript_entries: list[TranscriptEntry],
    number_of_paragraphs: int,
    session: ClientSession,
) -> Article:
    # TODO move this to ./article
    subtitles = format_transcript(transcript_entries)
    resp = await gpt_request(PROMPT.format(number_of_paragraphs), '\n'.join(subtitles), session)
    article_dict = json.loads(resp)
    return parse_obj_as(Article, article_dict)
