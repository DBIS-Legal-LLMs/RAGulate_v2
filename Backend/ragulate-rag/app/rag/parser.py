import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def normalize_key(value: str) -> str:
    """Normalize entity names for deduplication."""
    return value.strip().lower()


def clean_text(value: str) -> str:
    """
    Remove soft hyphens (U+00AD) that appear in PDF-extracted text,
    collapse internal whitespace, and strip surrounding whitespace.
    """
    return re.sub(r"\s+", " ", value.replace("­", "")).strip()


def make_preview(content: str, max_chars: int = 200) -> str:
    """Generate a word-boundary-safe preview of content."""
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rsplit(" ", 1)[0] + "…"


def split_description(desc: str) -> List[str]:
    """Split descriptions on <SEP> into a clean list."""
    if not desc:
        return []
    return [clean_text(d) for d in str(desc).split("<SEP>") if d.strip()]


def source_name(file_path: Optional[str]) -> Optional[str]:
    """
    Reduce a file path to a display name: final path component with known
    document extensions stripped.

    Why not a generic `\\.[^.]+$`: filenames like "..._v2.0_en" contain a dot
    inside the stem; stripping the last dot segment would eat ".0_en" and
    break the PDF lookup downstream.
    """
    if not file_path:
        return None
    name = str(file_path).strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"\.(pdf|txt|md|html?|docx?)$", "", name, flags=re.IGNORECASE)
    return name or None


def parse_rag_data(raw_data: Dict) -> Dict:
    """
    Map LightRAG's structured aquery_data() output into the shape the UI
    expects:
    - entities
    - relationships
    - documents
    - meta

    Expected input format (LightRAG >= 1.4):
    {
        "status": "success" | "failure",
        "data": {
            "entities": [{"entity_name", "entity_type", "description", ...}],
            "relationships": [{"src_id", "tgt_id", "description", ...}],
            "chunks": [{"content", "file_path", "reference_id", ...}],
            "references": [{"reference_id", "file_path"}],
        },
        "metadata": {...}
    }
    """
    result = {
        "entities": [],
        "relationships": [],
        "documents": [],
        "meta": {}
    }

    if not isinstance(raw_data, dict):
        return result

    if raw_data.get("status") != "success":
        logger.warning(
            "parse_rag_data: query did not succeed (status=%s, message=%s)",
            raw_data.get("status"), raw_data.get("message"),
        )

    data = raw_data.get("data") or {}

    # reference_id -> display name, for chunks that only carry a numeric ref
    ref_map = {
        str(ref.get("reference_id")): source_name(ref.get("file_path"))
        for ref in data.get("references") or []
        if ref.get("reference_id") is not None
    }

    # -------------------------------
    # Entity Processing
    # -------------------------------
    entity_map = {}  # normalized_name -> entity_id
    entity_id_counter = 1

    for obj in data.get("entities") or []:
        name = str(obj.get("entity_name") or "").strip()
        if not name:
            continue

        norm_name = normalize_key(name)
        if norm_name in entity_map:
            continue

        entity_id = f"entity_{entity_id_counter}"
        entity_id_counter += 1
        entity_map[norm_name] = entity_id

        entity_type = str(obj.get("entity_type") or "Unknown")
        descriptions = split_description(obj.get("description") or "")

        result["entities"].append({
            "id": entity_id,
            "label": name,
            "type": entity_type,
            "description": descriptions,
            "description_text": "\n".join(descriptions),
        })

    # -------------------------------
    # Document Processing
    # -------------------------------
    doc_id_counter = 1

    for obj in data.get("chunks") or []:
        content = clean_text(str(obj.get("content") or ""))
        if not content:
            continue

        doc_id = f"doc_{doc_id_counter}"
        doc_id_counter += 1

        resolved_ref = (
            source_name(obj.get("file_path"))
            or ref_map.get(str(obj.get("reference_id") or "").strip())
        )

        result["documents"].append({
            "id": doc_id,
            "source_document": resolved_ref,
            "content": content,
            "preview": make_preview(content)
        })

    # -------------------------------
    # Relationship Processing
    # -------------------------------
    seen_rels = set()

    for obj in data.get("relationships") or []:
        source = str(obj.get("src_id") or "").strip()
        target = str(obj.get("tgt_id") or "").strip()
        label = clean_text(str(obj.get("description") or obj.get("keywords") or ""))

        if not source or not target:
            continue

        # Ensure entities exist (auto-create if referenced but not declared)
        for node in [source, target]:
            norm = normalize_key(node)
            if norm not in entity_map:
                entity_id = f"entity_{entity_id_counter}"
                entity_id_counter += 1
                entity_map[norm] = entity_id

                result["entities"].append({
                    "id": entity_id,
                    "label": node,
                    "type": "Unknown",
                    "description": [],
                    "description_text": "",
                })

        source_id = entity_map[normalize_key(source)]
        target_id = entity_map[normalize_key(target)]

        # Deduplicate relationships.
        # BPMN flows are directed edges; the label is part of the key so
        # distinct relationships between the same pair are all kept.
        rel_key = (source_id, target_id, normalize_key(label))
        if rel_key in seen_rels:
            continue
        seen_rels.add(rel_key)

        result["relationships"].append({
            "source": source_id,
            "source_label": source,
            "target": target_id,
            "target_label": target,
            "label": label
        })

    # -------------------------------
    # Top-level Metadata
    # -------------------------------
    result["meta"] = {
        "entity_count": len(result["entities"]),
        "relationship_count": len(result["relationships"]),
        "document_count": len(result["documents"])
    }

    return result
