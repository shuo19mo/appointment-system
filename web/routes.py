from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")
router = APIRouter(tags=["Web"])


@router.get("/", response_class=HTMLResponse)
@router.get("/teachers", response_class=HTMLResponse)
@router.get("/courses", response_class=HTMLResponse)
@router.get("/schedules", response_class=HTMLResponse)
async def dashboard(request: Request):
    runtime = request.app.state.llm_runtime
    model_name = getattr(runtime, "model_name", "deepseek-v4-flash")
    return templates.TemplateResponse(request, "index.html", {"model_name": model_name})
