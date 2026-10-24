"""Translation backends: Claude (context-aware, best for dialogue) and Google Translate."""
from __future__ import annotations

import asyncio
import html
import json
import logging
import time
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
                        batch_size: int | None = None, on_progress=None) -> list[str]:
    """Translate cue texts, preserving leading {\\an8}-style tags and empty cues."""
    batch_size = batch_size or getattr(tr, "batch_size", 40)
    split = [split_leading_tags(t) for t in texts]
    todo = [i for i, (_, body) in enumerate(split) if body.strip()]
    result = [body for _, body in split]
    sem, done = asyncio.Semaphore(getattr(tr, "concurrency", 4)), 0

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


class LLMTranslator:
    """Shared prompt + retry logic for chat models; subclasses implement `_complete`."""
    concurrency = 4
    SYSTEM = (
        "You are a professional subtitle translator. The input is a JSON object mapping line ids "
        "to subtitle lines, consecutive dialogue from one film/show. Translate every line into "
        "{lang}, using the surrounding lines for context, gender, tone and slang; write natural "
        "spoken {lang}, not literal text. Keep HTML tags like <i> and line breaks (\\n) in place, "
        "and keep names, numbers and sound cues like [music] consistent. Reply with ONLY a JSON "
        "object with exactly the same ids, each mapped to its translated line."
    )

    async def _complete(self, system: str, user: str) -> str:
        raise NotImplementedError

    async def translate_batch(self, texts: list[str], target: str) -> list[str]:
        """Lines are keyed by id, so a dropped or merged line only costs a retry of the missing
        ids (not the whole batch); lines still missing after 3 tries keep their original text."""
        system = self.SYSTEM.format(lang=LANGUAGES.get(target, target))
        pending = {str(i): t for i, t in enumerate(texts)}
        done: dict[str, str] = {}
        for attempt in range(3):
            if not pending:
                break
            raw = await self._complete(system, json.dumps(pending, ensure_ascii=False))
            try:
                out = _parse_object(raw)
            except ValueError:
                log.warning("unparseable model output (attempt %d, %d lines)", attempt + 1, len(pending))
                continue
            for k in list(pending):
                if isinstance(out.get(k), str):
                    done[k] = out[k]
                    del pending[k]
            if pending:
                log.warning("model skipped %d/%d lines (attempt %d)", len(pending), len(texts), attempt + 1)
        return [done.get(str(i), t) for i, t in enumerate(texts)]


class ClaudeTranslator(LLMTranslator):
    def __init__(self, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def _complete(self, system: str, user: str) -> str:
        msg = await self.client.messages.create(
            model=self.model, max_tokens=8192, system=system,
            messages=[{"role": "user", "content": user}])
        return msg.content[0].text


class GeminiTranslator(LLMTranslator):
    """Free-tier friendly: requests are spaced out, a 429 waits for the delay Google asks for,
    and a model that keeps failing is skipped for a while in favour of the next one."""
    concurrency = 2  # overlaps request latency; MIN_INTERVAL still caps the request rate
    batch_size = 60  # fewer, bigger requests: the free tier limits requests per minute
    MIN_INTERVAL = 4.0  # seconds between request starts (~15 per minute)
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    RETRY_STATUS = (429, 500, 503)
    ATTEMPTS = 3
    MAX_WAIT = 45  # never sleep longer than this for one retry
    COOLDOWN = 60  # seconds to skip a model after it failed with an overload / quota error

    def __init__(self, api_key: str, models: list[str]):
        self.key, self.models = api_key, models
        self.http = httpx.AsyncClient(timeout=60)
        self._cool: dict[str, float] = {}
        self._gate = asyncio.Lock()
        self._next_slot = 0.0

    async def _throttle(self):
        async with self._gate:
            wait = self._next_slot - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_slot = time.monotonic() + self.MIN_INTERVAL

    @staticmethod
    def _retry_delay(r: httpx.Response) -> float | None:
        """Seconds Google asks us to wait (RetryInfo in the error body, or Retry-After)."""
        try:
            for d in r.json()["error"].get("details", []):
                if d.get("@type", "").endswith("RetryInfo"):
                    return float(str(d["retryDelay"]).rstrip("s"))
        except (ValueError, KeyError, TypeError):
            pass
        try:
            return float(r.headers["retry-after"])
        except (KeyError, ValueError):
            return None

    async def _complete(self, system: str, user: str) -> str:
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3}}
        last: Exception | None = None
        now = time.monotonic()
        usable = [m for m in self.models if self._cool.get(m, 0) <= now]
        for model in usable or self.models:  # everything cooling down: just try them all again
            for attempt in range(self.ATTEMPTS):
                delay = 2.0
                await self._throttle()
                try:
                    r = await self.http.post(self.URL.format(model=model), json=body,
                                             headers={"x-goog-api-key": self.key})
                    if r.status_code not in self.RETRY_STATUS:
                        r.raise_for_status()
                        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    last = httpx.HTTPStatusError(f"{model}: HTTP {r.status_code}", request=r.request, response=r)
                    if r.status_code == 429:
                        delay = self._retry_delay(r) or 5.0 * (attempt + 1)
                except httpx.TimeoutException as e:
                    last = e
                log.warning("gemini %s failed (attempt %d): %r", model, attempt + 1, last)
                if attempt < self.ATTEMPTS - 1:
                    await asyncio.sleep(min(delay, self.MAX_WAIT))
            self._cool[model] = time.monotonic() + self.COOLDOWN
        raise last or RuntimeError("no Gemini model configured")


def _parse_object(raw: str) -> dict:
    raw = raw.strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object")
    try:
        data = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(str(e)) from e
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data
