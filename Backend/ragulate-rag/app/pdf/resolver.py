import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Successful resolutions only — misses are re-scanned so newly added corpus
# files are still picked up without a restart.
_resolve_cache: dict[str, Path] = {}


def _normalise(name: str) -> str:
    return name.lower().replace("-", "_").replace(" ", "_")


def resolve_pdf_path(document_name: str) -> Path | None:
    """Map a document_name stem (no extension) to the PDF file on disk.

    Searches the whole PDF data directory recursively, mirroring how ingestion
    discovers documents, so new corpus folders are picked up automatically.
    Matching is case-insensitive and treats hyphens and underscores as
    equivalent, because full_doc_id values use hyphens while some filenames
    use underscores.

    Successful lookups are cached (validated against the filesystem on each
    hit) so repeated citation requests skip the recursive directory walk.
    """
    cached = _resolve_cache.get(document_name)
    if cached is not None:
        if cached.is_file():
            return cached
        del _resolve_cache[document_name]

    base = Path(settings.pdf_data_dir)
    if not base.is_dir():
        return None
    needle = _normalise(document_name)

    prefix_matches: list[Path] = []
    for pdf_file in base.rglob("*.pdf"):
        stem_norm = _normalise(pdf_file.stem)
        if stem_norm == needle:
            _resolve_cache[document_name] = pdf_file
            return pdf_file
        # Fallback: tolerate truncated identifiers (e.g. "..._v2" → "..._v2.0_en").
        # Only used if no exact match is found across all dirs.
        if needle and stem_norm.startswith(needle):
            prefix_matches.append(pdf_file)

    if len(prefix_matches) == 1:
        _resolve_cache[document_name] = prefix_matches[0]
        return prefix_matches[0]

    if len(prefix_matches) > 1:
        # Ambiguous prefix — returning an arbitrary candidate could highlight
        # the wrong PDF
        logger.warning(
            "resolve_pdf_path: %d PDFs match prefix %r (%s) — refusing to guess",
            len(prefix_matches),
            document_name,
            ", ".join(sorted(p.name for p in prefix_matches)),
        )

    return None
