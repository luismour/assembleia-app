import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.routers.delegado import db
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

load_dotenv()

router = APIRouter(prefix="/api")

SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-padrao-caso-nao-ache-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_DB = {
    "admin": "$2b$12$wB.sROrmXCmvh2ei3RpqBuWCAQY6LY7xupTfKi5pV06LDZqUvAGXe"
}

class SenhaAdmin(BaseModel):
    usuario: str = "admin"
    senha: str

class PautaInput(BaseModel):
    titulo: str

class StatusPauta(BaseModel):
    status: str

class GrupoInput(BaseModel):
    numero: str
    quantidade: int = 2

def verificar_senha(senha_pura, senha_hash):
    return pwd_context.verify(senha_pura, senha_hash)

def criar_token_acesso(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verificar_admin(x_admin_token: str = Header(None), token_query: str = Query(None)):
    token = x_admin_token or token_query
    
    if not token:
        raise HTTPException(status_code=401, detail="Token não fornecido")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario: str = payload.get("sub")
        if not usuario or usuario not in ADMIN_DB:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        return usuario
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

@router.post("/admin/login")
def admin_login(dados: SenhaAdmin):
    if dados.usuario not in ADMIN_DB:
        raise HTTPException(status_code=400, detail="Usuário ou senha incorretos")
    
    senha_hash = ADMIN_DB[dados.usuario]
    
    if not verificar_senha(dados.senha, senha_hash):
        raise HTTPException(status_code=400, detail="Usuário ou senha incorretos")
    
    token_jwt = criar_token_acesso(data={"sub": dados.usuario})
    
    return {"token": token_jwt}

@router.post("/admin/logout")
def admin_logout():
    return {"message": "Saiu"}

@router.get("/grupos")
def listar_grupos(usuario: str = Depends(verificar_admin)):
    lista = []
    if "grupos_meta" not in db: db["grupos_meta"] = {}
    for numero, qtd in db["grupos_meta"].items():
        lista.append({"numero": numero, "quantidade": qtd})
    lista.sort(key=lambda x: int(x["numero"]) if x["numero"].isdigit() else x["numero"])
    return lista

@router.post("/grupos")
def cadastrar_grupo(dados: GrupoInput, usuario: str = Depends(verificar_admin)):
    if "grupos_meta" not in db: db["grupos_meta"] = {}
    if "usuarios" not in db: db["usuarios"] = {}
    if "lista_grupos" not in db: db["lista_grupos"] = []

    if dados.numero in db["grupos_meta"]: raise HTTPException(status_code=400, detail="Grupo já cadastrado.")

    db["grupos_meta"][dados.numero] = dados.quantidade
    if dados.numero not in db["lista_grupos"]: db["lista_grupos"].append(dados.numero)

    for i in range(1, dados.quantidade + 1):
        credencial = f"{dados.numero}-{i}"
        db["usuarios"][credencial] = {
            "id": credencial, 
            "nome": f"Delegado {i} - GE {dados.numero}/PE",
            "grupo": dados.numero
        }
    return {"msg": "Grupo cadastrado."}

@router.delete("/grupos/{numero}")
def remover_grupo(numero: str, usuario: str = Depends(verificar_admin)):
    if "grupos_meta" not in db: db["grupos_meta"] = {}
    db["grupos_meta"].pop(numero, 0)
    if numero in db["lista_grupos"]: db["lista_grupos"].remove(numero)
    usuarios_para_remover = [k for k, v in db["usuarios"].items() if v["grupo"] == numero]
    for k in usuarios_para_remover: del db["usuarios"][k]
    return {"msg": "Grupo removido"}

@router.get("/dados-admin")
def get_dados_admin(usuario: str = Depends(verificar_admin)):
    if "grupos_meta" not in db: db["grupos_meta"] = {}
    total_delegados = sum(db["grupos_meta"].values())
    total_votos_possiveis = total_delegados 

    resultado = []
    for p in reversed(db["pautas"]):
        contagem = {"favor": 0, "contra": 0, "abstencao": 0}
        
        for lista_votos in p.votos.values():
            for v in lista_votos:
                if v in contagem:
                    contagem[v] += 1
        
        total_realizado = sum(len(v) for v in p.votos.values())

        resultado_texto = "EM ANDAMENTO"
        if p.status == "ENCERRADA":
            if contagem["favor"] > contagem["contra"]:
                resultado_texto = "APROVADA"
            elif contagem["contra"] >= contagem["favor"] and total_realizado > 0:
                resultado_texto = "REPROVADA"
            else:
                resultado_texto = "SEM VOTOS"

        resultado.append({
            "id": p.id,
            "titulo": p.titulo,
            "status": p.status,
            "total_votos": total_realizado,
            "esperados": total_votos_possiveis,
            "resultados": contagem,
            "resultado_final": resultado_texto
        })
    return resultado

@router.post("/pautas")
def criar_pauta(dados: PautaInput, usuario: str = Depends(verificar_admin)):
    from app.routers.delegado import Pauta
    import uuid
    nova_pauta = Pauta(id=str(uuid.uuid4()), titulo=dados.titulo)
    db["pautas"].append(nova_pauta)
    return nova_pauta

@router.post("/pautas/{id}/status")
def mudar_status_pauta(id: str, dados: StatusPauta, usuario: str = Depends(verificar_admin)):
    if dados.status == "ABERTA":
        for p in db["pautas"]:
            if p.status == "ABERTA": p.status = "ENCERRADA"
    for p in db["pautas"]:
        if p.id == id:
            p.status = dados.status
            return {"msg": "Status atualizado"}
    raise HTTPException(404, "Pauta não encontrada")

@router.get("/exportar")
def exportar_relatorio(x_admin_token: str = Header(None), token: str = Query(None)):
    usuario = verificar_admin(x_admin_token, token)
    
    wb = Workbook()
    
    ws_resumo = wb.active
    ws_resumo.title = "Resumo Geral"
    ws_resumo.append(["ID", "Título da Pauta", "Status", "Resultado", "Total Votos", "Favor", "Contra", "Abstenção"])
    
    for cell in ws_resumo[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="002d62", end_color="002d62", fill_type="solid")

    for p in db["pautas"]:
        favor = 0
        contra = 0
        abstencao = 0
        total = 0
        
        for lista_votos in p.votos.values():
            for v in lista_votos:
                total += 1
                if v == "favor": favor += 1
                elif v == "contra": contra += 1
                elif v == "abstencao": abstencao += 1
        
        resultado_txt = "-"
        if p.status == "ENCERRADA":
            if favor > contra: resultado_txt = "APROVADA"
            elif contra >= favor and total > 0: resultado_txt = "REPROVADA"
            else: resultado_txt = "SEM VOTOS"

        ws_resumo.append([p.id, p.titulo, p.status, resultado_txt, total, favor, contra, abstencao])

    ws_detalhado = wb.create_sheet(title="Votos Detalhados")
    ws_detalhado.append(["Pauta", "Credencial", "Voto"])
    
    for p in db["pautas"]:
        for credencial, lista_votos in p.votos.items():
            for voto in lista_votos:
                ws_detalhado.append([p.titulo, credencial, voto])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    headers = {'Content-Disposition': 'attachment; filename="Relatorio_Votacao.xlsx"'}
    return StreamingResponse(buffer, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')