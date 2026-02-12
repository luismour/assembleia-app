from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import admin, delegado
from app import models
from app.database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(admin.router)
app.include_router(delegado.router)

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request): return templates.TemplateResponse("delegado.html", {"request": request})

@app.get("/telao", response_class=HTMLResponse)
def read_telao(request: Request): return templates.TemplateResponse("telao.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
def read_admin(request: Request): return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/cadastro", response_class=HTMLResponse)
def read_cadastro(request: Request): return templates.TemplateResponse("cadastro.html", {"request": request})