"""FastAPI router for serving PDF files and locating text within them."""
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.pdf.locator import locate_text_in_pdf
from app.pdf.resolver import resolve_pdf_path
from app.schemas.pdf import LocateResponse


class LocateRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Full text chunk to locate and highlight")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdf", tags=["PDF"])


@router.get("/{document_name}", response_class=FileResponse, summary="Stream a source PDF file")
async def serve_pdf(document_name: str):
    """Stream the PDF identified by document_name (stem, no extension).

    Returns 404 if the file cannot be found in any known data directory.
    Content-Disposition is set to inline so browsers display the PDF directly.
    """
    pdf_path = resolve_pdf_path(document_name)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail=f"PDF '{document_name}' not found")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={pdf_path.name}"},
    )


@router.get(
    "/{document_name}/locate",
    response_model=LocateResponse,
    summary="Locate a text fragment in a PDF and return its page and bounding boxes",
)
async def locate_in_pdf(
    document_name: str,
    q: str = Query(..., min_length=10, description="Text fragment to search for"),
):
    """Use PyMuPDF to find the first occurrence of q in the PDF.

    Returns the 0-based page index, bounding rectangles in PDF points, and
    the page dimensions so the caller can compute percentage-based positions.
    If no match is found, page is null and rects is empty — the caller should
    still open the PDF (on page 0) for context.
    """
    pdf_path = resolve_pdf_path(document_name)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail=f"PDF '{document_name}' not found")

    # locate_text_in_pdf is CPU-bound (full-document scan) — keep it off the event loop.
    result = await asyncio.to_thread(locate_text_in_pdf, pdf_path, q)
    if result is None:
        logger.info("No match for query in %s", document_name)
        return LocateResponse(page=None, rects=[], page_width=0, page_height=0)

    return LocateResponse(
        page=result["page"],
        rects=result["rects"],
        page_width=result["page_width"],
        page_height=result["page_height"],
    )


@router.post(
    "/{document_name}/locate",
    response_model=LocateResponse,
    summary="Locate a full text chunk in a PDF and return its page and bounding boxes",
)
async def locate_in_pdf_post(document_name: str, body: LocateRequest):
    """POST variant of the locate endpoint — accepts the full chunk text in the
    request body so URL length limits don't truncate long passages."""
    pdf_path = resolve_pdf_path(document_name)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail=f"PDF '{document_name}' not found")

    # locate_text_in_pdf is CPU-bound (full-document scan) — keep it off the event loop.
    result = await asyncio.to_thread(locate_text_in_pdf, pdf_path, body.text)
    if result is None:
        logger.info("No match for text in %s", document_name)
        return LocateResponse(page=None, rects=[], page_width=0, page_height=0)

    return LocateResponse(
        page=result["page"],
        rects=result["rects"],
        page_width=result["page_width"],
        page_height=result["page_height"],
    )
