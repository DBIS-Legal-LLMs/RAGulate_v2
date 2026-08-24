from pydantic import BaseModel


class HighlightRect(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class LocateResponse(BaseModel):
    page: int | None
    rects: list[HighlightRect]
    page_width: float
    page_height: float
