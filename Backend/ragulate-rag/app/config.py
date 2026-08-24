from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # --- Gemini API Key ---
    gemini_api_key: str = ""

    # --- LLM Settings ---
    llm_model: str = "meta-llama/Llama-3.2-3B-Instruct"
    llm_binding: str = "openai"  # "gemini" or "openai"
    llm_api_key: str = ""        # Only for openai binding 
    llm_api_base: str = "https://api-inference.huggingface.co/v1/"

    # --- Embedding Settings ---
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    embedding_binding: str = "local"  # "gemini", "openai", or "local"
    embedding_api_key: str = ""        # Only for openai binding
    embedding_api_base: str = ""       # Only for openai binding

    # --- Rerank Settings ---
    rerank_binding: str = "local"  # "local" or "cohere"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_api_key: str = ""
    rerank_api_base: str = "https://openrouter.ai/api/v1/rerank"
    rerank_top_n: int = 10

    # --- Ragas Evaluation Overrides ---
    # Override only the LLM used for metric scoring (leave blank to use LLM_MODEL).
    ragas_llm_model: str = ""           # e.g. "openai/gpt-4o-mini"

    # --- Neo4j Settings (RAGulate's own instance, distinct from GRIPL's) ---
    neo4j_uri: str = "neo4j://localhost:7688"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "ragulate-rag-2026"

    # --- Timeouts (seconds) ---
    rag_query_timeout: float = 300.0    # POST /api/query end-to-end retrieval
    ragas_metric_timeout: float = 600.0  # single Ragas metric scoring call

    # --- LightRAG Working Directory ---
    rag_working_dir: str = "./rag_working_dir"

    # --- Data Paths ---
    extracted_data_dir: str = "./data/extracted"
    pdf_data_dir: str = "./data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a single instance that the rest of the app imports.
settings = Settings()
