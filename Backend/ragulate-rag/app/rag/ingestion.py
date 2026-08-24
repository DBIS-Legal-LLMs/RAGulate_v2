from pathlib import Path
from lightrag import LightRAG
from app.config import settings


def discover_documents(data_dir: str | None = None) -> list[Path]:

    directory = Path(data_dir or settings.extracted_data_dir)

    if not directory.exists():
        raise FileNotFoundError(
            f"Data directory not found: {directory}\n"
            f"Have you run scripts/extract_pdfs.py first?"
        )

    files = sorted(directory.rglob("*.txt"))

    if not files:
        raise FileNotFoundError(
            f"No .txt files found in {directory}\n"
            f"Have you run scripts/extract_pdfs.py first?"
        )

    return files


async def ingest_documents(
    rag: LightRAG,
    documents: list[Path],
    batch_description: str = "", # Optional label for logging 
) -> dict:
    stats = {
        "total": len(documents),
        "successful": 0,
        "failed": 0,
        "errors": [],
    }

    prefix = f"[{batch_description}] " if batch_description else ""

    for i, doc_path in enumerate(documents, start=1):
        filename = doc_path.name
        print(f"\n{prefix}[{i}/{len(documents)}] Ingesting: {filename}")

        try:
            text = doc_path.read_text(encoding="utf-8")

            if not text.strip():
                print(f"   SKIPPED: Empty file")
                stats["failed"] += 1
                stats["errors"].append((filename, "Empty file"))
                continue

            print(f"   Characters: {len(text):,}")

            await rag.ainsert(text, ids=[doc_path.stem], file_paths=[doc_path.stem])

            print(f"   Done!")
            stats["successful"] += 1

        except Exception as e:
            print(f"   ERROR: {e}")
            stats["failed"] += 1
            stats["errors"].append((filename, str(e)))

    return stats
