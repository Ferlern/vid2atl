from contextlib import asynccontextmanager
from logging.config import dictConfig

from fastapi import FastAPI, Depends
from aiohttp import ClientSession

from .schemas import ArticleRequest
from .dependencies import http_client
from .services.article import generate_article
from .logger import LogConfig
from .utils.pytube_hotfix import fix


dictConfig(LogConfig().dict())
fix()


@asynccontextmanager
async def _lifespan(_: FastAPI):
    http_client.start()
    yield
    await http_client.stop()

app = FastAPI(lifespan=_lifespan)


@app.post("/article/")
async def create_article(
    article_request: ArticleRequest,
    session: ClientSession = Depends(http_client),
):
    article = await generate_article(
        url=article_request.url,
        number_of_paragraphs=article_request.number_of_paragraphs,
        lang=article_request.lang,
        person=article_request.person,
        aditional_prompt=article_request.aditional_prompt,
        session=session,
    )
    return article.dict()
