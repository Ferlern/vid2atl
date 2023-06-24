from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import base64
import asyncio

from src.logger import get_logger
from src.schemas import PostrocessorType
from src.settings import IMGUR_TOKEN, IMGUR_ID
if TYPE_CHECKING:
    from aiohttp import ClientSession


logger = get_logger()
IMGUR_URL = "https://api.imgur.com/3/upload.json"


def get_postrocessor(postrocessor_type: PostrocessorType) -> type[Postrocessor]:
    postpocessors_mapping = {
        PostrocessorType.BASE64: Base64Postrocessor,
        PostrocessorType.IMGUR: ImgurPostrocessor,
    }
    return postpocessors_mapping[postrocessor_type]


class Postrocessor(ABC):
    @abstractmethod
    async def process(self, image: bytes, session: ClientSession) -> str:
        raise NotImplementedError

    async def process_many(self, images: list[bytes], session: ClientSession) -> list[str]:
        return await asyncio.gather(
            *[self.process(image, session) for image in images]
        )


class Base64Postrocessor(Postrocessor):
    async def process(self, image: bytes, session: ClientSession) -> str:
        return base64.b64encode(image).decode('utf-8')


class ImgurPostrocessor(Postrocessor):
    async def process(self, image: bytes, session: ClientSession) -> str:
        if not IMGUR_ID or not IMGUR_TOKEN:
            raise RuntimeError('Imgur ID or token is empty, ImgurPostrocessor will not work')

        headers = {"Authorization": f"Client-ID {IMGUR_ID}"}
        async with session.post(
            IMGUR_URL,
            headers=headers,
            json={
                'key': IMGUR_TOKEN,
                'image': base64.b64encode(image).decode(),
                'type': 'base64',
                'name': '11232.jpg',
                'title': 'My Picture no. 1'
            }
        ) as response:
            data = await response.json()
            return data['data']['link']
