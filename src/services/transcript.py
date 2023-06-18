from __future__ import annotations
from typing import TYPE_CHECKING
import re
import asyncio
import youtube_transcript_api
from fastapi.concurrency import run_in_threadpool
from src.schemas import TranscriptEntry
from src.logger import get_logger
from .translation import translate

if TYPE_CHECKING:
    from aiohttp import ClientSession


YOUTUBE_REGEX = r'^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*'
transcriptAPI = youtube_transcript_api.YouTubeTranscriptApi()
logger = get_logger()


def youtuble_url_to_video_id(url: str) -> str:
    if match := re.match(pattern=YOUTUBE_REGEX, string=url):
        return match[2]
    raise ValueError('Invalid youtube video URL')


def best_transcript_for_translatate_in_english(
    transcripts: youtube_transcript_api.TranscriptList
) -> youtube_transcript_api.Transcript:
    best_langueges = [
        'en', 'es', 'fr', 'de', 'it', 'pt', 'nl',
        'sv', 'da', 'no', 'fi', 'ru', 'ar', 'ja', 'ko', 'zh'
    ]

    def max_key(transcript: youtube_transcript_api.Transcript):
        language_code = transcript.language_code
        if language_code in best_langueges:
            return -best_langueges.index(language_code) - transcript.is_generated
        return float('-inf')

    return max(transcripts, key=max_key)


async def get_transcripts(url: str) -> youtube_transcript_api.TranscriptList:
    video_id = youtuble_url_to_video_id(url)
    return await run_in_threadpool(transcriptAPI.list_transcripts, video_id)


async def get_best_for_translatate_transcript(url: str) -> youtube_transcript_api.Transcript:
    return best_transcript_for_translatate_in_english(await get_transcripts(url))


async def get_english_transcript(url: str, session: ClientSession) -> list[TranscriptEntry]:
    transcript = await get_best_for_translatate_transcript(url)
    if transcript.language_code == 'en':
        transcript_data = await run_in_threadpool(transcript.fetch)
    elif 'en' in transcript.translation_languages:
        transcript_data = await run_in_threadpool(transcript.translate('en').fetch)
    else:
        transcript_data = await run_in_threadpool(transcript.fetch)
        await translate_transcript_data(transcript_data, session=session)
    logger.debug(transcript_data)
    return [TranscriptEntry(**entry) for entry in transcript_data]


async def translate_transcript_data(data: list[dict], session: ClientSession) -> None:
    # TODO translate chuncks of text and then split it back into dict
    translate_results = await asyncio.gather(
        *[translate(entry['text'], session=session) for entry in data]
    )
    for entry, translated_entry in zip(data, translate_results):
        entry['text'] = translated_entry.translated
