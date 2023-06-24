from __future__ import annotations
from typing import TYPE_CHECKING
import re

import youtube_transcript_api
from youtube_transcript_api import _errors as youtube_transcript_errors
from fastapi.concurrency import run_in_threadpool

from src.schemas import TranscriptEntry
from src.logger import get_logger
from .whisper import whisper_transcript

if TYPE_CHECKING:
    from aiohttp import ClientSession


_YOUTUBE_REGEX = r'^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*'
_transcript_api = youtube_transcript_api.YouTubeTranscriptApi()
logger = get_logger()


async def get_english_transcript(
    url: str,
    force_whisper: bool,
    session: ClientSession
) -> list[TranscriptEntry]:
    if force_whisper:
        return await whisper_transcript(session, url)
    try:
        return await _get_youtube_english_transcript(url, session)
    except youtube_transcript_errors.TranscriptsDisabled:
        logger.info('No transcripts for %s, use whisper fallback', url)
        return await whisper_transcript(session, url)


def _youtuble_url_to_video_id(url: str) -> str:
    if match := re.match(pattern=_YOUTUBE_REGEX, string=url):
        return match[2]
    raise ValueError('Invalid youtube video URL')


async def _get_transcripts(url: str) -> youtube_transcript_api.TranscriptList:
    video_id = _youtuble_url_to_video_id(url)
    return await run_in_threadpool(_transcript_api.list_transcripts, video_id)


def _best_transcript_for_translatate_in_english(
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


async def _get_best_for_translatate_transcript(url: str) -> youtube_transcript_api.Transcript:
    return _best_transcript_for_translatate_in_english(await _get_transcripts(url))


async def _get_youtube_english_transcript(
    url: str,
    _: ClientSession,
) -> list[TranscriptEntry]:
    transcript = await _get_best_for_translatate_transcript(url)
    transcript_data = await run_in_threadpool(transcript.fetch)
    return [TranscriptEntry(**entry) for entry in transcript_data]
