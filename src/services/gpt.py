from __future__ import annotations
from typing import TYPE_CHECKING
import io
import json

from src.logger import get_logger
from src.utils.json_ import try_loads
from src.settings import PATH, TOKEN

if TYPE_CHECKING:
    from aiohttp import ClientSession


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
        "model": "gpt-3.5-turbo-16k",
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


async def gpt_json_request(
    system: str,
    user: str,
    session: ClientSession,
):
    content = await gpt_request(system=system, user=user, session=session)
    return try_loads(content)
