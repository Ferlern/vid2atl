from __future__ import annotations
import asyncio
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Iterable, Sequence

from fastapi.concurrency import run_in_threadpool
from youtube_transcript_api import _errors as youtube_transcript_errors

from src.schemas import Article, ArticleTopic, TranscriptEntry, ArticleRequest, GenerationTime
from src.logger import get_logger
from src.utils.time_ import get_sec
from .gpt import gpt_json_request, gpt_request
from .transcript.youtube import YouTubeTranscriptProvider
from .transcript.whisper import WhisperTranscriptProvider
from .screenshots.frame_selector import extract_frames
from .screenshots.postprocessor import get_postrocessor

if TYPE_CHECKING:
    from aiohttp import ClientSession

logger = get_logger()
PROMPT = """
Choose a title and description for video subtitles and break subtitles into small topics which should cover the entire subtitles.
You will receive subtitles in the following format (start - video subtitles):
hh:mm:ss - subtitles
hh:mm:ss - subtitles
...

Respond with valid JSON in the following format (Substitude text in [square brackets]):
{"title": "[title]", "description": "[summarize what was said in the subtitles]", "topics": [{"start": "[hh:mm:ss]", "end": "[hh:mm:ss]"}, ...]}
"start" and "end" indicate the beginning and end of the discussion on this topic in video subtitles. Topics must cover all video subtitles and should last more than a minute."""  # noqa: E501

TOPIC_PROMPT = """
Your task is to combine video subtitles into separate whole sentences in first person without losing the meaning, combine multiple video subtitles into one sentence to achive this task.
Highlight the actions that are asked to be done in subtitles with <b> at the beginning and </b> at the end. Make some sentences as oredred lists (1 ... 2 ... 3 ...)

Each sentence should tell one thought but may contain multiple <b>bolded</b> actions. Also provide title which expresses the meaning of all sentences.
Respond in russian language
You will receive subtitles in the following format:
hh:mm:ss - subtitles
hh:mm:ss - subtitles
...

Respond in russian language. Response template:
[title]
[hh:mm:ss - hh:mm:ss] [generated sentence]
[hh:mm:ss - hh:mm:ss] [generated sentence]
...

Substitude [hh:mm:ss - hh:mm:ss] with time, for example [00:01:22 - 00:01:35] and [generated sentences] with generated sentence. Do not provide text that does not fit the template.

Response example:
Удаление порграмм на операционной системе Windows
[00:00:00 - 00:00:11] Сегодня мы поговорим о том, <b>как удалить программы на windows</b> 
[00:00:11 - 00:00:25] Для этого выполним действия:
1. Открываем пуск
2. Пишем "установка и удаление"
3. выбираем нужно меню
[00:00:25 - 00:00:37] В этом окне <b>используем поиск</b> для нахождения нужной программы
[00:00:37 - 00:00:47] Нажимаем "удалить" и ждём завершения удаления
"""  # noqa: E501


class ArticleGenerator:
    """
    Генерирует статьи на основе запроса.
    
    Поддерживает возможность указать количество подтем, обрезать видео, может выбирать из видео
    самые интересные скриншоты для статьи (алгоритмами компьютерного зрения) и указывает тайминги,
    что и когда было сказано в видео. Может использовать теги `<b>` `</b>` для выделения важного
    текста и нумерованные списки (1 ... 2 ...) для перечислений действий
    """
    def __init__(
        self,
        request: ArticleRequest,
        session: ClientSession
    ) -> None:
        self.request = request
        self.session = session
        self._article: Article

    async def generate_article(self) -> Article:
        """Выполняет все шаги по генерации статьи и возвращает её"""
        start_time = time.monotonic()
        request = self.request
        url = request.url

        logger.info('generating article for %s', url)
        logger.info('gathering transcript for %s', url)
        transcript_generation_start_time = time.monotonic()
        transcript = await self._get_transacript()
        transcript_generation_time = time.monotonic() - transcript_generation_start_time
        if request.start or request.end:
            transcript = _truncate_transcript(transcript, request.start, request.end)
        logger.debug('transcript for %s %s', url, transcript)

        logger.info('generating article title and themes for %s', url)
        await self._generate_partial_article(transcript)
        article = self._article

        screenshot_periods = [
            (get_sec(topic.start), get_sec(topic.end)) for topic in article.topics
        ]
        logger.info('gathering frames and generating content for %s', url)
        logger.debug('Screenshot Periods %s', screenshot_periods)
        images_start_time = time.monotonic()
        frames, _ = await asyncio.gather(
            run_in_threadpool(
                extract_frames,
                url,
                screenshot_periods,
                request.number_of_screenshots,
                request.selector,
            ),
            self._generate_article_content(transcript)
        )
        article.generation_time.images = time.monotonic() - images_start_time
        logger.info('process images for %s using %s', url, request.image_format)
        postprocessor = get_postrocessor(request.image_format)()
        processed_images = await asyncio.gather(
            *[postprocessor.process_many(topic_frames, self.session) for topic_frames in frames]
        )
        for topic, processed_topic_frames in zip(article.topics, processed_images):
            topic.images = processed_topic_frames
        article.generation_time.total = time.monotonic() - start_time
        article.generation_time.transcript = transcript_generation_time
        return article

    async def _get_transacript(self) -> list[TranscriptEntry]:
        """Выбирает TranscriptProvider исходя из запроса и запрашивает транскрипцию"""
        url = self.request.url
        if self.request.force_whisper:
            provider = WhisperTranscriptProvider(url, self.session)
        else:
            provider = YouTubeTranscriptProvider(url, self.session)
        try:
            return await provider.get_transcript()
        except youtube_transcript_errors.TranscriptsDisabled:
            logger.info('No transcripts for %s, use whisper fallback', url)
            provider = WhisperTranscriptProvider(url, self.session)
            return await provider.get_transcript()

    async def _generate_partial_article(
        self,
        transcript_entries: Sequence[TranscriptEntry],
    ) -> None:
        """Генерирует тему и временные промежутки подтем"""
        start_time = time.monotonic()
        number_of_paragraphs = self.request.number_of_paragraphs
        subtitles = _format_transcript(transcript_entries)
        article_dict = await gpt_json_request(PROMPT, '\n'.join(subtitles), self.session)
        topics = [ArticleTopic(**topic_data) for topic_data in article_dict['topics']]
        if number_of_paragraphs < len(topics):
            number_of_seconds = transcript_entries[-1].start - transcript_entries[0].start
            approximate_topic_length = number_of_seconds / number_of_paragraphs
            topics = _recombine_topics(approximate_topic_length, topics)
        if number_of_paragraphs != len(topics):
            logger.warning('Number of topics is not equal to the requested')

        self._article = Article(
            title=article_dict['title'],
            description=article_dict['description'],
            topics=topics,
            generation_time=GenerationTime(title=time.monotonic() - start_time),
        )

    async def _generate_article_content(
        self,
        transcript_entries: Sequence[TranscriptEntry],
    ) -> None:
        """Генерирует контент и зоголовок для каждой темы"""
        start_time = time.monotonic()
        topics = self._article.topics

        transcript_entries_for_topics = [
            _select_transcript_entries_for_topic(
                transcript_entries, topic
            ) for topic in topics
        ]
        # TODO remove this hack, to do this, rewrite first prompt
        if all((
            transcript_entries[-1] not in transcript_entries_for_topics[-1],
            transcript_entries_for_topics[-1],
        )):
            transcript_entries_for_topics[-1].append(transcript_entries[-1])

        logger.debug(
            'Lenght of transcript: %d before splitting, %d after',
            len(transcript_entries),
            sum(len(entry) for entry in transcript_entries_for_topics)
        )

        topic_datas = await asyncio.gather(*[
            gpt_request(
                TOPIC_PROMPT, '\n'.join(_format_transcript(transcript_entries)), self.session
            ) for transcript_entries in transcript_entries_for_topics if transcript_entries
        ])
        for data, filtered_topics in zip(topic_datas, topics):
            title, *paragraphs = data.splitlines()
            if not paragraphs:
                filtered_topics.title = 'Не удалось сгенерировать'
                filtered_topics.paragraphs = title
            else:
                filtered_topics.title = title
                filtered_topics.paragraphs = '\n'.join(paragraphs)
        filtered_topics = list(filter(lambda topic: topic.paragraphs, topics))
        if len(filtered_topics) != len(topics):
            logger.warning(
                'Some topics has no paragraphs so was removed. This means that the model '
                'gave the wrong answer, the quality of the article may suffer.'
            )
        self._article.generation_time.content = time.monotonic() - start_time


def _format_transcript(transcript_entries: Iterable[TranscriptEntry]) -> list[str]:
    """Приводит TranscriptEntry к формату строки, которая будет отправлена языковой модели"""
    result = []
    for entry in transcript_entries:
        start = entry.start
        text = entry.text
        result.append(f'{timedelta(seconds=int(start))} - {text}')
    return result


def _recombine_topics(
    approximate_topic_length: float,
    old_topics: list[ArticleTopic]
) -> list[ArticleTopic]:
    """
    Соединяет несколько подтем в одну для достижения указанного количества
    В теории качество сгенерированных тем не должно пострадать, ведь они будут компиляцией цельных,
    пусть и, возможно, независимых тем
    """
    last_topic_end = get_sec(old_topics[-1].end)
    topics = []
    topic_start_time = old_topics[0].start
    topic_start_second = get_sec(topic_start_time)
    for old_topic in old_topics:
        end_time = get_sec(old_topic.end)
        if (
            end_time - topic_start_second > approximate_topic_length and
            last_topic_end - topic_start_second > approximate_topic_length
        ):
            topics.append(ArticleTopic(
                start=topic_start_time,
                end=old_topic.end,
            ))
            topic_start_time = old_topic.end
            topic_start_second = end_time
    if end_time != topic_start_second:  # type: ignore
        topics.append(ArticleTopic(
            start=topic_start_time,
            end=old_topic.end,  # type: ignore
        ))

    return topics


def _select_transcript_entries_for_topic(
    transcript_entries: Sequence[TranscriptEntry],
    topic: ArticleTopic,
) -> list[TranscriptEntry]:
    """
    Выбирает субтитры, которые подходят под указанную тему исходя из времени.
    Это необходимо, ведь отправка всех субтитров может привести к нехватке токенов у языковой модели
    """
    start = get_sec(topic.start)
    end = get_sec(topic.end)
    return [entry for entry in transcript_entries if start <= entry.start <= end]


def _truncate_transcript(
    transcript: list[TranscriptEntry],
    start: float,
    end: float
) -> list[TranscriptEntry]:
    """Выбирает субтитры, которые подходят по времени."""
    return [entry for entry in transcript if start < entry.start < end]
