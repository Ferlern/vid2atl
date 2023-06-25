from contextlib import asynccontextmanager
from logging.config import dictConfig

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from aiohttp import ClientSession

from .schemas import ArticleRequest
from .dependencies import http_client
from .services.article import ArticleGenerator
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/article/")
async def create_article(
    article_request: ArticleRequest,
    session: ClientSession = Depends(http_client),
):
    generator = ArticleGenerator(request=article_request, session=session)
    article = await generator.generate_article()
    return article.dict()
