from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Admin(Base):
    __tablename__ = "admins"
    usuario = Column(String, primary_key=True, index=True)
    senha_hash = Column(String)

class Assembleia(Base):
    __tablename__ = "assembleias"
    id = Column(String, primary_key=True, index=True)
    titulo = Column(String)
    ativa = Column(Boolean, default=False)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String, primary_key=True, index=True) 
    token = Column(String, unique=True, index=True)   
    nome = Column(String)
    grupo = Column(String)
    cpf = Column(String)
    email = Column(String) 
    checkin = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)

class Pauta(Base):
    __tablename__ = "pautas"
    id = Column(String, primary_key=True, index=True)
    titulo = Column(String)
    assembleia_id = Column(String, ForeignKey("assembleias.id"))
    status = Column(String, default="AGUARDANDO")
    tipo = Column(String, default="SIMPLES")      
    max_escolhas = Column(Integer, default=1)
    candidatos_str = Column(Text, default="")     

class Voto(Base):
    __tablename__ = "votos"
    id = Column(Integer, primary_key=True, index=True)
    pauta_id = Column(String, ForeignKey("pautas.id"))
    usuario_id = Column(String, ForeignKey("usuarios.id"))
    escolha_str = Column(Text)