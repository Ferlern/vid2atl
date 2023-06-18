from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from aiohttp import ClientSession
from logging.config import dictConfig
from .schemas import ArticleRequest
from .dependencies import http_client
from .services.article import generate_article
from .logger import LogConfig


dictConfig(LogConfig().dict())


@asynccontextmanager
async def lifespan(app: FastAPI):
    http_client.start()
    yield
    await http_client.stop()

app = FastAPI(lifespan=lifespan)


@app.post("/article/")
async def create_article(
    article_request: ArticleRequest,
    session: ClientSession = Depends(http_client),
):
    article = await generate_article(
        url=article_request.url,
        number_of_paragraphs=article_request.number_of_paragraphs,
        lang=article_request.lang,
        session=session,
    )
    return article.dict()
