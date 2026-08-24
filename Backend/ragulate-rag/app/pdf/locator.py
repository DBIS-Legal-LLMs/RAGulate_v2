from functools import lru_cache
from pathlib import Path
from typing import NamedTuple, TypedDict
import re
import unicodedata

import fitz  # PyMuPDF
from rapidfuzz import fuzz


class LocateResult(TypedDict):
    page: int
    rects: list[dict]
    page_width: float
    page_height: float


_LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}
_NON_ALPHANUM = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")
_MIN_PAGE_SCORE = 65.0          # below this, the page is considered no match
_TOKEN_OVERLAP_FLOOR = 0.25     # skip pages whose token overlap with the chunk is too low
_PAGE_INDEX_CACHE_SIZE = 8      # PDFs kept fully extracted in memory
_RESULT_CACHE_SIZE = 256        # (pdf, query) → highlight results


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for lig, repl in _LIGATURES.items():
        text = text.replace(lig, repl)
    text = text.replace("­", "")            # soft hyphen
    text = re.sub(r"-\s*\n\s*", "", text)        # join hyphenated line breaks
    text = text.lower()
    text = _NON_ALPHANUM.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    return _normalize(text).split()


class _PageData(NamedTuple):
    """Pre-extracted, pre-normalized page content for alignment."""
    raw_words: tuple          # PyMuPDF word tuples (with bounding boxes)
    token_set: frozenset      # normalized tokens, for the overlap prefilter
    page_text: str            # normalized tokens joined with spaces
    offsets: tuple            # char offset of each token within page_text
    token_lengths: tuple      # length of each token
    token_to_raw: tuple       # normalized token index -> raw word index
    page_width: float
    page_height: float


@lru_cache(maxsize=_PAGE_INDEX_CACHE_SIZE)
def _load_page_index(path_str: str, mtime_ns: int, size: int) -> tuple[_PageData, ...]:
    """Extract and normalize every page of a PDF once; cached per file version.

    mtime_ns and size are part of the key purely for invalidation: if the PDF
    is replaced on disk, the key changes and the stale entry ages out.
    """
    doc = fitz.open(path_str)
    try:
        pages: list[_PageData] = []
        for page in doc:
            raw_words = tuple(page.get_text("words"))

            page_tokens: list[str] = []
            token_to_raw: list[int] = []
            for idx, w in enumerate(raw_words):
                for part in _normalize(w[4]).split():
                    page_tokens.append(part)
                    token_to_raw.append(idx)

            offsets: list[int] = []
            pos = 0
            for t in page_tokens:
                offsets.append(pos)
                pos += len(t) + 1

            pages.append(_PageData(
                raw_words=raw_words,
                token_set=frozenset(page_tokens),
                page_text=" ".join(page_tokens),
                offsets=tuple(offsets),
                token_lengths=tuple(len(t) for t in page_tokens),
                token_to_raw=tuple(token_to_raw),
                page_width=page.rect.width,
                page_height=page.rect.height,
            ))
        return tuple(pages)
    finally:
        doc.close()


def _group_rects_by_line(matched_words: list[tuple]) -> list[dict]:
    """One bounding rectangle per visual line — like a normal text selection."""
    lines: dict[tuple[int, int], list[tuple]] = {}
    for w in matched_words:
        key = (int(w[5]), int(w[6]))  # block_no, line_no
        lines.setdefault(key, []).append(w)

    rects: list[dict] = []
    for key in sorted(lines.keys()):
        ws = lines[key]
        rects.append({
            "x0": min(w[0] for w in ws),
            "y0": min(w[1] for w in ws),
            "x1": max(w[2] for w in ws),
            "y1": max(w[3] for w in ws),
        })
    return rects


def _align_chunk_to_page(
    pd: _PageData,
    chunk_set: set[str],
    chunk_text: str,
) -> tuple[float, list]:
    """Return (score, matched_raw_words) for the best alignment on this page."""
    if not pd.token_set:
        return 0.0, []

    # Cheap overlap prefilter so we skip clearly-irrelevant pages before the
    # O(n*m) alignment.
    overlap = len(chunk_set & pd.token_set) / max(len(chunk_set), 1)
    if overlap < _TOKEN_OVERLAP_FLOOR:
        return 0.0, []

    alignment = fuzz.partial_ratio_alignment(chunk_text, pd.page_text)
    if alignment is None or alignment.score < _MIN_PAGE_SCORE:
        return 0.0, []

    dest_start = alignment.dest_start
    dest_end = alignment.dest_end

    matched_raw: set[int] = set()
    for i, off in enumerate(pd.offsets):
        tok_end = off + pd.token_lengths[i]
        if tok_end <= dest_start:
            continue
        if off >= dest_end:
            break
        matched_raw.add(pd.token_to_raw[i])

    if not matched_raw:
        return 0.0, []

    return alignment.score, [pd.raw_words[i] for i in sorted(matched_raw)]


@lru_cache(maxsize=_RESULT_CACHE_SIZE)
def _locate_cached(path_str: str, mtime_ns: int, size: int, query: str) -> LocateResult | None:
    chunk_tokens = _tokenize(query)
    if not chunk_tokens:
        return None
    chunk_set = set(chunk_tokens)
    chunk_text = " ".join(chunk_tokens)

    pages = _load_page_index(path_str, mtime_ns, size)

    best_score = 0.0
    best_page_index = -1
    best_matched: list = []
    best_page: _PageData | None = None

    for page_index, pd in enumerate(pages):
        score, matched = _align_chunk_to_page(pd, chunk_set, chunk_text)
        if not matched:
            continue
        # Tiebreak slightly in favor of pages that matched more words, so a
        # full-passage hit beats a page that happens to score 100 on a
        # short overlap.
        weighted = score + 0.05 * len(matched)
        if weighted > best_score:
            best_score = weighted
            best_page_index = page_index
            best_matched = matched
            best_page = pd

    if best_page_index < 0 or not best_matched or best_page is None:
        return None

    return {
        "page": best_page_index,
        "rects": _group_rects_by_line(best_matched),
        "page_width": best_page.page_width,
        "page_height": best_page.page_height,
    }


def locate_text_in_pdf(pdf_path: Path, query: str) -> LocateResult | None:
    """Locate query text in PDF by fuzzy-aligning the chunk against each page.

    Words from the PDF are extracted with their bounding boxes, both sides are
    normalized (ligatures, hyphenation, case, punctuation), and rapidfuzz finds
    the best matching span per page. Matched words are then grouped by their
    visual line so the returned highlight is one clean rectangle per line —
    robust to whitespace, line-break, and ligature mismatches between the
    pre-extracted .txt chunks and the PDF text stream.

    Page extraction and results are cached per PDF file version (path + mtime
    + size), so repeated citation lookups against the same document skip the
    open/extract/tokenize work entirely.
    """
    stat = pdf_path.stat()
    result = _locate_cached(str(pdf_path), stat.st_mtime_ns, stat.st_size, query)
    if result is None:
        return None
    # Copy so callers can't mutate the cached entry.
    return {
        "page": result["page"],
        "rects": [dict(r) for r in result["rects"]],
        "page_width": result["page_width"],
        "page_height": result["page_height"],
    }
