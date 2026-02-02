from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from app.routers.delegado import db

router = APIRouter(prefix="/api")

class SenhaAdmin(BaseModel):
    senha: str

class PautaInput(BaseModel):
    titulo: str

class StatusPauta(BaseModel):
    status: str

class GrupoInput(BaseModel):
    numero: str
    quantidade: int = 2

def verificar_admin(x_admin_token: str = Header(None)):
    if x_admin_token != "token-secreto-admin-123":
        raise HTTPException(status_code=401, detail="Não autorizado")

@router.post("/admin/login")
def admin_login(dados: SenhaAdmin):
    if dados.senha == "saps":
        return {"token": "token-secreto-admin-123"}
    raise HTTPException(status_code=400, detail="Senha incorreta")

@router.post("/admin/logout")
def admin_logout():
    return {"message": "Saiu"}

@router.get("/grupos")
def listar_grupos(x_admin_token: str = Header(None)):
    verificar_admin(x_admin_token)
    lista = []
    
    if "grupos_meta" not in db:
        db["grupos_meta"] = {}

    for numero, qtd in db["grupos_meta"].items():
        lista.append({"numero": numero, "quantidade": qtd})
    
    lista.sort(key=lambda x: int(x["numero"]) if x["numero"].isdigit() else x["numero"])
    return lista

@router.post("/grupos")
def cadastrar_grupo(dados: GrupoInput, x_admin_token: str = Header(None)):
    verificar_admin(x_admin_token)
    
    if "grupos_meta" not in db: db["grupos_meta"] = {}
    if "usuarios" not in db: db["usuarios"] = {}    
    if "lista_grupos" not in db: db["lista_grupos"] = []

    if dados.numero in db["grupos_meta"]:
        raise HTTPException(status_code=400, detail="Grupo já cadastrado.")

    db["grupos_meta"][dados.numero] = dados.quantidade
    if dados.numero not in db["lista_grupos"]:
        db["lista_grupos"].append(dados.numero)

    for i in range(1, dados.quantidade + 1):
        credencial = f"{dados.numero}-{i}"
        
        db["usuarios"][credencial] = {
            "id": credencial, 
            "nome": f"Delegado {i} - GE {dados.numero}/PE",
            "grupo": dados.numero
        }
    
    return {"msg": f"Grupo {dados.numero} cadastrado com {dados.quantidade} delegados."}

@router.delete("/grupos/{numero}")
def remover_grupo(numero: str, x_admin_token: str = Header(None)):
    verificar_admin(x_admin_token)
    
    if "grupos_meta" not in db: db["grupos_meta"] = {}

    qtd = db["grupos_meta"].pop(numero, 0)
    
    if numero in db["lista_grupos"]:
        db["lista_grupos"].remove(numero)

    usuarios_para_remover = [k for k, v in db["usuarios"].items() if v["grupo"] == numero]
    for k in usuarios_para_remover:
        del db["usuarios"][k]

    return {"msg": "Grupo removido"}

@router.get("/dados-admin")
def get_dados_admin(x_admin_token: str = Header(None)):
    verificar_admin(x_admin_token)
    
    if "grupos_meta" not in db: db["grupos_meta"] = {}
    total_possivel = sum(db["grupos_meta"].values())

    resultado = []
    for p in reversed(db["pautas"]):
        contagem = {"favor": 0, "contra": 0}
        for v in p.votos.values():
            if v in contagem:
                contagem[v] += 1
        
        resultado.append({
            "id": p.id,
            "titulo": p.titulo,
            "status": p.status,
            "total_votos": len(p.votos),
            "esperados": total_possivel,
            "resultados": contagem
        })
    return resultado

@router.post("/pautas")
def criar_pauta(dados: PautaInput, x_admin_token: str = Header(None)):
    verificar_admin(x_admin_token)
    from app.routers.delegado import Pauta
    import uuid
    
    nova_pauta = Pauta(id=str(uuid.uuid4()), titulo=dados.titulo)
    db["pautas"].append(nova_pauta)
    return nova_pauta

@router.post("/pautas/{id}/status")
def mudar_status_pauta(id: str, dados: StatusPauta, x_admin_token: str = Header(None)):
    verificar_admin(x_admin_token)
    
    if dados.status == "ABERTA":
        for p in db["pautas"]:
            if p.status == "ABERTA":
                p.status = "ENCERRADA"

    for p in db["pautas"]:
        if p.id == id:
            p.status = dados.status
            return {"msg": "Status atualizado"}
    
    raise HTTPException(404, "Pauta não encontrada")