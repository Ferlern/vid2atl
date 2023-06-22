from __future__ import annotations
from typing import TYPE_CHECKING
import os
import json

from dotenv import load_dotenv

from src.logger import get_logger

if TYPE_CHECKING:
    from aiohttp import ClientSession

load_dotenv()

TOKEN = os.getenv('API_TOKEN') or ''
PATH = os.getenv('API_ENDPOINT') or ''
if not TOKEN or not PATH:
    raise RuntimeError('Invalid .env')


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
