"""Translation backends: Claude (context-aware, best for dialogue) and Google Translate."""
from __future__ import annotations

import asyncio
import html
import json
import logging
from typing import Protocol

import httpx

from subtitles import split_leading_tags

log = logging.getLogger(__name__)

LANGUAGES = {
    "fa": "Persian", "en": "English", "ar": "Arabic", "tr": "Turkish", "ru": "Russian",
    "de": "German", "fr": "French", "es": "Spanish", "it": "Italian", "pt": "Portuguese",
    "zh-CN": "Chinese (Simplified)", "ja": "Japanese", "ko": "Korean", "hi": "Hindi",
    "ur": "Urdu", "az": "Azerbaijani",
}


class Translator(Protocol):
    async def translate_batch(self, texts: list[str], target: str) -> list[str]: ...


async def translate_all(tr: Translator, texts: list[str], target: str,
                        batch_size: int = 40, concurrency: int = 4, on_progress=None) -> list[str]:
    """Translate cue texts, preserving leading {\\an8}-style tags and empty cues."""
    split = [split_leading_tags(t) for t in texts]
    todo = [i for i, (_, body) in enumerate(split) if body.strip()]
    result = [body for _, body in split]
    sem, done = asyncio.Semaphore(concurrency), 0

    async def run(chunk: list[int]):
        nonlocal done
        async with sem:
            out = await tr.translate_batch([split[i][1] for i in chunk], target)
        for i, t in zip(chunk, out):
            result[i] = t
        done += len(chunk)
        if on_progress:
            await on_progress(done, len(todo))

    await asyncio.gather(*(run(todo[i:i + batch_size]) for i in range(0, len(todo), batch_size)))
    return [prefix + body for (prefix, _), body in zip(split, result)]


class GoogleTranslator:
    URL = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self, api_key: str):
        self.key = api_key
        self.http = httpx.AsyncClient(timeout=60)

    async def translate_batch(self, texts: list[str], target: str) -> list[str]:
        out: list[str] = []
        for i in range(0, len(texts), 100):  # API limit: 128 strings per request
            r = await self.http.post(self.URL, params={"key": self.key}, json={
                "q": texts[i:i + 100], "target": target, "format": "html"})
            r.raise_for_status()
            out += [html.unescape(t["translatedText"]) for t in r.json()["data"]["translations"]]
        return out


class ClaudeTranslator:
    SYSTEM = (
        "You are a professional subtitle translator. Translate each numbered subtitle line into "
        "{lang}. The lines are consecutive dialogue from one film/show, so use surrounding lines "
        "for context, gender, tone and slang; write natural spoken {lang}, not literal text. "
        "Keep HTML tags like <i> and line breaks (\\n) in place, and keep names, numbers and "
        "sound cues like [music] consistent. Reply with ONLY a JSON array of strings, the same "
        "length and order as the input."
    )

    def __init__(self, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def translate_batch(self, texts: list[str], target: str) -> list[str]:
        lang = LANGUAGES.get(target, target)
        for attempt in range(2):
            msg = await self.client.messages.create(
                model=self.model, max_tokens=8192, system=self.SYSTEM.format(lang=lang),
                messages=[{"role": "user", "content": json.dumps(texts, ensure_ascii=False)}])
            try:
                out = _parse_array(msg.content[0].text)
                if len(out) == len(texts):
                    return out
            except ValueError:
                pass
            log.warning("bad model output (attempt %d, %d lines)", attempt + 1, len(texts))
        if len(texts) == 1:
            return texts  # give up on this line, keep the original
        mid = len(texts) // 2  # misaligned output: retry on smaller halves
        return (await self.translate_batch(texts[:mid], target)
                + await self.translate_batch(texts[mid:], target))


def _parse_array(raw: str) -> list[str]:
    raw = raw.strip()
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end < 0:
        raise ValueError("no JSON array")
    data = json.loads(raw[start:end + 1])
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise ValueError("not a list of strings")
    return data
