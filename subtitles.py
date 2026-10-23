"""Minimal SRT / WebVTT parser that keeps timing and structure intact."""
from __future__ import annotations

import re
from dataclasses import dataclass

ENCODINGS = ("utf-8-sig", "cp1256", "cp1252")
LEADING_TAGS = re.compile(r"^(?:\{[^}]*\})+")


@dataclass
class Block:
    """A subtitle block. `head` is everything before the text (id + timing line)."""
    head: list[str]
    text: list[str]
    is_cue: bool


def decode(data: bytes) -> str:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    for enc in ENCODINGS:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def parse(content: str) -> list[Block]:
    blocks: list[Block] = []
    for raw in re.split(r"\n{2,}", content.replace("\r\n", "\n").replace("\r", "\n").strip("\n")):
        lines = raw.split("\n")
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            blocks.append(Block(lines, [], False))  # WEBVTT header, NOTE, STYLE...
        else:
            blocks.append(Block(lines[: idx + 1], lines[idx + 1 :], True))
    return blocks


def cue_texts(blocks: list[Block]) -> list[str]:
    return ["\n".join(b.text) for b in blocks if b.is_cue]


def render(blocks: list[Block], translations: list[str]) -> str:
    it = iter(translations)
    out = []
    for b in blocks:
        text = next(it).split("\n") if b.is_cue else b.text
        out.append("\n".join(b.head + text))
    return "\n\n".join(out) + "\n"


def split_leading_tags(text: str) -> tuple[str, str]:
    """Separate ASS-style prefixes like {\\an8} so translators never see them."""
    m = LEADING_TAGS.match(text)
    return (m.group(0), text[m.end():]) if m else ("", text)
