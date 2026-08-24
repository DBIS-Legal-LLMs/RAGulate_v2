import asyncio
import logging
import os
from pathlib import Path
from lightrag import LightRAG
from app.config import settings
from app.rag.openai_embeddings import (
    create_embed_client,
    embed_texts_float,
    retry_on_rate_limit,
)

logger = logging.getLogger(__name__)


def _set_neo4j_env_vars():
    os.environ["NEO4J_URI"] = settings.neo4j_uri
    os.environ["NEO4J_USERNAME"] = settings.neo4j_username
    os.environ["NEO4J_PASSWORD"] = settings.neo4j_password


def _get_llm_func():
    #Returns the appropriate LLM function based on LLM_BINDING setting.
    if settings.llm_binding == "gemini":
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
        from lightrag.llm.gemini import gemini_model_complete
        return gemini_model_complete

    elif settings.llm_binding == "openai":
        os.environ["OPENAI_API_KEY"] = settings.llm_api_key
        if settings.llm_api_base:
            os.environ["OPENAI_API_BASE"] = settings.llm_api_base
        from lightrag.llm.openai import openai_complete

        # Wrap the upstream function so every call gets auto-retry.
        async def _openai_complete_with_retry(*args, **kwargs):
            return await retry_on_rate_limit(
                lambda: openai_complete(*args, **kwargs),
                label="LLM",
            )

        return _openai_complete_with_retry

    else:
        raise ValueError(
            f"Unknown LLM_BINDING: '{settings.llm_binding}'. "
            f"Supported values: 'gemini', 'openai'"
        )


def _get_embedding_func():
    """
    Returns the appropriate embedding function based on EMBEDDING_BINDING.

    WHY A CUSTOM WRAPPER:
        LightRAG's built-in gemini_embed has @wrap_embedding_func_with_attrs
        that hardcodes embedding_dim=1536. But model dimesion may vary.
        If we pass gemini_embed directly, LightRAG sees a mismatch.
    """
    from lightrag.utils import EmbeddingFunc

    if settings.embedding_binding == "gemini":
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key

        # We call the google-genai SDK directly instead of LightRAG's built-in gemini_embed.
        async def _gemini_embed(texts: list[str]) -> "np.ndarray":
            import numpy as np
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key)

            config = types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=settings.embedding_dim,
            )

            response = await client.aio.models.embed_content(
                model=settings.embedding_model,
                contents=texts,
                config=config,
            )

            embeddings = np.array(
                [np.array(e.values, dtype=np.float32) for e in response.embeddings]
            )

            # L2 normalize for dimensions < 3072
            if settings.embedding_dim < 3072:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                norms = np.where(norms == 0, 1, norms)
                embeddings = embeddings / norms

            return embeddings

        return EmbeddingFunc(
            embedding_dim=settings.embedding_dim,
            max_token_size=8192,
            func=_gemini_embed,
        )

    elif settings.embedding_binding == "openai":
        # Uses the shared float-encoding + retry helper instead of LightRAG's
        # openai_embed (see app.rag.openai_embeddings for why).
        # One client for all embedding batches — avoids a new TCP/TLS
        # handshake per call. Safe here because LightRAG always invokes the
        # embedding func from the same (FastAPI) event loop.
        embed_client = create_embed_client()

        async def _openai_embed_wrapper(texts: list[str]) -> "np.ndarray":
            import numpy as np

            vectors = await embed_texts_float(embed_client, texts)
            return np.array([np.array(v, dtype=np.float32) for v in vectors])

        return EmbeddingFunc(
            embedding_dim=settings.embedding_dim,
            max_token_size=8192,
            func=_openai_embed_wrapper,
        )

    elif settings.embedding_binding == "local":
        from lightrag.utils import EmbeddingFunc
        from sentence_transformers import SentenceTransformer

        # Load the local model here
        import logging
        logging.info(f"Loading local SentenceTransformer model: {settings.embedding_model}")
        model = SentenceTransformer(settings.embedding_model)

        async def _local_embed(texts: list[str]) -> "np.ndarray":
            import numpy as np
            embeddings = await asyncio.to_thread(model.encode, texts)
            return np.array(embeddings, dtype=np.float32)

        return EmbeddingFunc(
            embedding_dim=settings.embedding_dim,
            max_token_size=8192,
            func=_local_embed,
        )

    else:
        raise ValueError(
            f"Unknown EMBEDDING_BINDING: '{settings.embedding_binding}'. "
            f"Supported values: 'gemini', 'openai', 'local'"
        )


_MAX_RERANK_DOCS = 20  # cap before CPU inference to bound latency on constrained Docker CPU

def _get_rerank_func():
    if settings.rerank_binding == "local":
        import asyncio
        from sentence_transformers import CrossEncoder

        logger.info("Loading local reranker: %s", settings.rerank_model)
        _model = CrossEncoder(settings.rerank_model)

        async def _local_rerank(query: str, documents: list, top_n: int = None):
            docs = documents[:_MAX_RERANK_DOCS]
            pairs = [(query, doc) for doc in docs]

            def _predict():
                return _model.predict(pairs, batch_size=8, show_progress_bar=False)

            scores = await asyncio.to_thread(_predict)
            ranked = sorted(
                [{"index": i, "relevance_score": float(s)} for i, s in enumerate(scores)],
                key=lambda x: x["relevance_score"],
                reverse=True,
            )
            return ranked[:top_n] if top_n else ranked

        return _local_rerank

    if settings.rerank_binding == "cohere":
        if not settings.rerank_api_key:
            return None
        from functools import partial
        from lightrag.rerank import cohere_rerank

        return partial(
            cohere_rerank,
            api_key=settings.rerank_api_key,
            model=settings.rerank_model,
            base_url=settings.rerank_api_base,
        )

    return None


async def create_rag_instance() -> LightRAG:
    """
    RETURNS:
        A LightRAG instance.
        - await rag.ainsert(text)  — to ingest documents
        - await rag.aquery(query)  — to retrieve context
    """
    working_dir = Path(settings.rag_working_dir)
    working_dir.mkdir(parents=True, exist_ok=True)

    _set_neo4j_env_vars()

    llm_func = _get_llm_func()
    embedding_func = await asyncio.to_thread(_get_embedding_func)
    rerank_func = await asyncio.to_thread(_get_rerank_func)

    rag = LightRAG(
        working_dir=str(working_dir),
        llm_model_func=llm_func,
        llm_model_name=settings.llm_model,
        embedding_func=embedding_func,
        rerank_model_func=rerank_func,
        graph_storage="Neo4JStorage",
        vector_storage="NanoVectorDBStorage",
        kv_storage="JsonKVStorage",
    )
    
    await rag.initialize_storages()

    return rag
