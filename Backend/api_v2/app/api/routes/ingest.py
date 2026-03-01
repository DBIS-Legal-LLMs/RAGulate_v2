from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
import pdfplumber, uuid, io
from ...services.rag_service import get_rag, LLMProviderName, DEFAULT_MODEL

router = APIRouter(prefix="/ingest", tags=["ingest"])
job_status: dict[str, str] = {}

def _extract_text(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    print(text)
    return text

async def _process(job_id: str, text: str, provider: LLMProviderName, model_id: str):
    try:
        rag = await get_rag(provider=provider, model_id=model_id)
        await rag.ainsert(text)
        job_status[job_id] = "done"
    except Exception as e:
        job_status[job_id] = f"error: {str(e)}"

@router.post("/pdf")
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    provider: LLMProviderName = Query(default="ollama"),
    model: str = Query(default=None),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Nur PDFs erlaubt")
    file_bytes = await file.read()
    text = _extract_text(file_bytes)
    if not text.strip():
        raise HTTPException(422, "Kein Text im PDF gefunden")

    model_id = model or DEFAULT_MODEL[provider]
    job_id = str(uuid.uuid4())
    job_status[job_id] = "processing"
    background_tasks.add_task(_process, job_id, text, provider, model_id)

    return {"job_id": job_id, "status": "processing", "filename": file.filename, "provider": provider, "model": model_id}

@router.get("/status/{job_id}")
def ingest_status(job_id: str):
    status = job_status.get(job_id)
    if not status:
        raise HTTPException(404, "Job nicht gefunden")
    return {"job_id": job_id, "status": status}