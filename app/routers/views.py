from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

# Configuração dos Templates
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(os.path.dirname(current_dir), "templates")
templates = Jinja2Templates(directory=templates_dir)

@router.get("/admin", response_class=HTMLResponse)
def view_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/", response_class=HTMLResponse)
def view_delegado(request: Request):
    return templates.TemplateResponse("delegado.html", {"request": request})

@router.get("/telao", response_class=HTMLResponse)
def view_telao(request: Request):
    return templates.TemplateResponse("telao.html", {"request": request})