import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # Importante
from app.routers import admin, delegado, views
import os

app = FastAPI(title="Sistema de Votação Escoteira")

static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app.mount("/static", StaticFiles(directory=static_path), name="static")

app.include_router(admin.router)
app.include_router(delegado.router)
app.include_router(views.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)