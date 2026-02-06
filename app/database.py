import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Tenta pegar a URL do Render
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# DIAGNÓSTICO: Imprime no log do Render o que está acontecendo
if not SQLALCHEMY_DATABASE_URL:
    print("ALERTA CRÍTICO: Variável DATABASE_URL não encontrada! Usando SQLite temporário.")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
else:
    print("SUCESSO: Variável DATABASE_URL encontrada! Conectando ao PostgreSQL...")

# 2. Correção para o Render (postgres:// -> postgresql://)
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Criação do Engine
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()