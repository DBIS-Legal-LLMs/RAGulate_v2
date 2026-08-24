import asyncio
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
# Unlike GRIPL (one shared .env.local for the whole monorepo), this service
# has its own .env right next to it — see .env.example.
load_dotenv(project_root / ".env")


async def main():
    from app.config import settings
    from app.rag.engine import create_rag_instance
    from app.rag.ingestion import discover_documents, ingest_documents

    print("=" * 60)
    print("ragulate-rag — Document Ingestion")
    print("=" * 60)

    # Show current configuration so you can verify settings
    print(f"\nConfiguration:")
    print(f"  LLM:         {settings.llm_model} ({settings.llm_binding})")
    print(f"  Embedding:   {settings.embedding_model} (dim={settings.embedding_dim})")
    print(f"  Graph DB:    Neo4j @ {settings.neo4j_uri}")
    print(f"  Working dir: {settings.rag_working_dir}")
    print(f"  Data dir:    {settings.extracted_data_dir}")

    # Discover documents
    print(f"\n--- Step 1: Discovering documents ---")
    try:
        documents = discover_documents()
        print(f"Found {len(documents)} document(s)")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Create LightRAG instance
    print(f"\n--- Step 2: Connecting to LightRAG + Neo4j ---")
    try:
        rag = await create_rag_instance()
        print("Connected successfully!")
    except Exception as e:
        print(f"ERROR: Failed to initialize LightRAG: {e}")
        print(f"\nCommon causes:")
        print(f"  - Neo4j is not running (run: docker compose up ragulate-neo4j)")
        print(f"  - LLM_API_KEY is invalid or not set in .env")
        sys.exit(1)

    # Ingest documents
    print(f"\n--- Step 3: Ingesting documents ---")
    start_time = time.time()

    stats = await ingest_documents(
        rag=rag,
        documents=documents,
        batch_description="GDPR corpus",
    )

    elapsed = time.time() - start_time

    # Summary
    print(f"\n{'=' * 60}")
    print(f"INGESTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Documents:  {stats['successful']}/{stats['total']} successful")
    print(f"  Time:       {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")

    if stats["errors"]:
        print(f"\n  ERRORS ({stats['failed']}):")
        for filename, error in stats["errors"]:
            print(f"    - {filename}: {error}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
