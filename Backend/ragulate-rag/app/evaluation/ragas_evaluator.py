from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import math
import os
import threading
from dataclasses import dataclass
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


SUPPORTED_METRICS = ("faithfulness", "context_utilization")


@dataclass
class _EvaluatorBundle:
    llm: object
    embeddings: object
    metrics: dict  # name -> ragas metric instance


_bundle: Optional[_EvaluatorBundle] = None
_bundle_lock = asyncio.Lock()


def _build_langchain_llm():
    """Build a LangChain chat model based on the configured binding."""
    # Ragas can override the LLM model without affecting the LightRAG engine.
    llm_model = settings.ragas_llm_model or settings.llm_model

    if settings.llm_binding == "openai":
        os.environ["OPENAI_API_KEY"] = settings.llm_api_key
        if settings.llm_api_base:
            os.environ["OPENAI_API_BASE"] = settings.llm_api_base
        from langchain_openai import ChatOpenAI

        api_key = os.environ["OPENAI_API_KEY"]
        if not api_key:
            raise RuntimeError(
                "Ragas evaluator: OPENAI_API_KEY / llm_api_key is required "
                "when llm_binding='openai'."
            )
        kwargs = {"model": llm_model, "api_key": api_key, "temperature": 0.0}
        if settings.llm_api_base:
            kwargs["base_url"] = settings.llm_api_base
        return ChatOpenAI(**kwargs)

    if settings.llm_binding == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "Ragas evaluator: GEMINI_API_KEY is required when llm_binding='gemini'."
            )
        return ChatGoogleGenerativeAI(
            model=llm_model,
            google_api_key=api_key,
            temperature=0.0,
        )

    raise ValueError(
        f"Ragas evaluator: unsupported llm_binding '{settings.llm_binding}'. "
        f"Use 'openai' or 'gemini'."
    )


class _OpenAIFloatEmbeddings:

    def __init__(self):
        self._client = None  # created lazily on the background loop
        self._loop = asyncio.new_event_loop()
        threading.Thread(
            target=self._loop.run_forever, name="ragas-embeddings", daemon=True
        ).start()

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        from app.rag.openai_embeddings import create_embed_client, embed_texts_float

        if self._client is None:
            self._client = create_embed_client()
        return await embed_texts_float(self._client, texts)

    def _submit(self, texts: list[str]) -> concurrent.futures.Future:
        return asyncio.run_coroutine_threadsafe(self._embed(texts), self._loop)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._submit(texts).result()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.wrap_future(self._submit(texts))

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]


def _build_langchain_embeddings():
    """Build a LangChain-compatible embedding model based on the configured binding."""
    if settings.embedding_binding == "openai":
        api_key = settings.embedding_api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("Ragas evaluator: OpenAI embedding api_key is required.")
        return _OpenAIFloatEmbeddings()

    if settings.embedding_binding == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        return GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=api_key,
        )

    if settings.embedding_binding == "local":
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=settings.embedding_model)

    raise ValueError(
        f"Ragas evaluator: unsupported embedding_binding '{settings.embedding_binding}'."
    )


async def _get_bundle() -> _EvaluatorBundle:
    """Lazily build the evaluator LLM + embeddings + Ragas metric instances."""
    global _bundle
    if _bundle is not None:
        return _bundle

    async with _bundle_lock:
        if _bundle is not None:
            return _bundle

        effective_llm_model = settings.ragas_llm_model or settings.llm_model
        logger.info(
            "Initialising Ragas evaluator bundle — judge LLM: %s (binding=%s), "
            "embeddings: %s (binding=%s)",
            effective_llm_model,
            settings.llm_binding,
            settings.embedding_model,
            settings.embedding_binding,
        )

        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.metrics import ContextUtilization, Faithfulness

        lc_llm = _build_langchain_llm()
        lc_emb = _build_langchain_embeddings()

        evaluator_llm = LangchainLLMWrapper(lc_llm)
        evaluator_emb = LangchainEmbeddingsWrapper(lc_emb)

        metrics = {
            "faithfulness": Faithfulness(llm=evaluator_llm),
            "context_utilization": ContextUtilization(llm=evaluator_llm),
        }

        _bundle = _EvaluatorBundle(llm=evaluator_llm, embeddings=evaluator_emb, metrics=metrics)
        logger.info("Ragas evaluator bundle ready.")
        return _bundle


def _build_sample(query: str, contexts: list[str], response: str):
    """Build a Ragas SingleTurnSample for the requested metrics."""
    from ragas.dataset_schema import SingleTurnSample

    # Ragas expects retrieved_contexts to be non-empty for context_precision/faithfulness.
    safe_contexts = [c for c in (contexts or []) if c and c.strip()]
    return SingleTurnSample(
        user_input=query,
        retrieved_contexts=safe_contexts or [""],
        response=response,
    )


async def _score_one(metric, sample) -> Optional[float]:
    """Score a single sample with one metric, returning None on failure or timeout."""
    try:
        score = await asyncio.wait_for(
            metric.single_turn_ascore(sample),
            timeout=settings.ragas_metric_timeout,
        )
        if score is None or math.isnan(score):
            return None
        return float(score)
    except asyncio.TimeoutError:
        logger.warning(
            "Ragas metric %s timed out after %.0fs — skipping",
            type(metric).__name__,
            settings.ragas_metric_timeout,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ragas metric %s failed: %s", type(metric).__name__, exc)
        return None


async def evaluate_samples(
    samples: list[dict],
    requested_metrics: Optional[list[str]] = None,
    concurrency: int = 4,
) -> dict:
    """
    Evaluate a batch of (id, query, contexts, response) dicts and return
    per-sample scores plus aggregate means.

    Each sample is scored across all requested metrics concurrently, and
    samples themselves are scored concurrently up to `concurrency`.
    """
    bundle = await _get_bundle()

    if requested_metrics:
        unknown = [m for m in requested_metrics if m not in SUPPORTED_METRICS]
        if unknown:
            raise ValueError(f"Unsupported metric(s): {unknown}. Supported: {SUPPORTED_METRICS}")
        active_metrics = {k: v for k, v in bundle.metrics.items() if k in requested_metrics}
    else:
        active_metrics = bundle.metrics

    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _score_sample(s: dict) -> dict:
        async with semaphore:
            ragas_sample = _build_sample(s["query"], s.get("contexts", []), s["response"])
            scores = await asyncio.gather(
                *[_score_one(m, ragas_sample) for m in active_metrics.values()]
            )
            result: dict = {"id": s["id"]}
            for name, value in zip(active_metrics.keys(), scores):
                result[name] = value
            return result

    per_sample = await asyncio.gather(*[_score_sample(s) for s in samples])

    aggregate: dict = {"sample_count": len(per_sample), "failed_count": 0}
    for name in active_metrics.keys():
        values = [r[name] for r in per_sample if r.get(name) is not None]
        aggregate[f"{name}_mean"] = (sum(values) / len(values)) if values else None
    aggregate["failed_count"] = sum(
        1 for r in per_sample if all(r.get(m) is None for m in active_metrics.keys())
    )

    return {"samples": per_sample, "aggregate": aggregate}
