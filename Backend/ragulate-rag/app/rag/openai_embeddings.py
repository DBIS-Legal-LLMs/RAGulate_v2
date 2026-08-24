"""Shared OpenAI helpers: rate-limit retry and float-encoded embeddings.

Both the LightRAG engine (app.rag.engine) and the Ragas evaluator
(app.evaluation.ragas_evaluator) embed via the OpenAI API.

* encoding_format="float": the OpenAI SDK defaults to base64, which some
  providers (e.g. OpenRouter) don't support for all models — they return
  response.data = None.
* retry_on_rate_limit: exponential-backoff retry on 429/5xx, so evaluation
  runs get the same resilience as normal RAG queries.
"""

import asyncio
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

# Rate-limit retry settings
MAX_RETRIES = 8          # up to ~4 min total wait on worst case
BASE_DELAY = 2.0         # seconds
MAX_DELAY = 120.0        # cap per-retry wait


async def retry_on_rate_limit(coro_factory, label: str = "API call"):

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            err_msg = str(exc).lower()
            is_rate_limit = (
                status == 429
                or "429" in err_msg
                or "rate limit" in err_msg
                or "rate_limit" in err_msg
                or "ratelimit" in err_msg
                or "too many requests" in err_msg
                or status in (502, 503, 529)
            )
            if is_rate_limit and attempt < MAX_RETRIES:
                delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)
                logger.warning(
                    "%s: rate-limited (attempt %d/%d). "
                    "Retrying in %.1fs …  [%s]",
                    label, attempt, MAX_RETRIES, delay, exc,
                )
                print(
                    f"Rate-limited on {label} (attempt {attempt}/{MAX_RETRIES}). "
                    f"Waiting {delay:.0f}s before retry…"
                )
                await asyncio.sleep(delay)
            else:
                raise


def create_embed_client():
    """Create an AsyncOpenAI client from the configured embedding settings.

    Callers should hold on to the client and reuse it — a new client per
    call means a new TCP/TLS handshake per call. Note that an AsyncOpenAI
    client is bound to the event loop it is first used on, so it must not
    be shared across loops.
    """
    from openai import AsyncOpenAI

    return AsyncOpenAI(
        api_key=settings.embedding_api_key or os.environ.get("OPENAI_API_KEY", ""),
        base_url=settings.embedding_api_base or None,
    )


async def embed_texts_float(client, texts: list[str]) -> list[list[float]]:
    """Embed texts with encoding_format="float", retrying on rate limits."""

    async def _do_embed():
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
            encoding_format="float",
        )
        return [dp.embedding for dp in response.data]

    return await retry_on_rate_limit(_do_embed, label="Embedding")
