from __future__ import annotations
from typing import TYPE_CHECKING
import os
import io
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
        # "model": "gpt-4",
        "temperature": 1,
        "presence_penalty": 0,
        "top_p": 1,
        "frequency_penalty": 0,
        "stream": True,
    }
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'text/event-stream',
    }

    buffer = io.StringIO()
    async with session.post(PATH, headers=headers, json=payload) as response:
        async for event in response.content:
            if event == b'\n' or not event:
                continue
            try:
                resp_dict = json.loads(event.lstrip(b'data:').rstrip(b'\n'))
            except json.JSONDecodeError:
                logger.warning('Broken event from model: %s', event)
                raise
            if delta := resp_dict['choices'][0]['delta']:
                content = delta['content']
                buffer.write(content)
    content = buffer.getvalue()
    logger.debug('Model response: %s', content)
    return content
