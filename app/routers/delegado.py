from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api")

# --- BANCO DE DADOS EM MEMÓRIA ---
db = {
    "pautas": [],
    "usuarios": {},        
    "lista_grupos": [],
    "grupos_meta": {}      
}

# --- MODELOS ---
class LoginRequest(BaseModel):
    credencial: str

class VotoRequest(BaseModel):
    credencial: str
    pauta_id: str
    opcao: str 

class Pauta:
    def __init__(self, id, titulo):
        self.id = id
        self.titulo = titulo
        self.status = "CRIADA"
        self.votos = {} 

def get_pauta_ativa():
    for p in db["pautas"]:
        if p.status == "ABERTA":
            return p
    if db["pautas"]:
        return db["pautas"][-1]
    return None

@router.post("/login")
def login_delegado(credencial: str):
    if credencial not in db["usuarios"]:
        raise HTTPException(status_code=404, detail="Credencial inválida.")
    return db["usuarios"][credencial]

@router.get("/pauta-ativa")
def get_pauta_ativa_endpoint(credencial: Optional[str] = None):
    pauta = get_pauta_ativa()
    if not pauta: return {"pauta": None}

    ja_votou = False
    if credencial and credencial in pauta.votos: ja_votou = True

    # --- AQUI: ADICIONADA ABSTENCAO ---
    contagem = {"favor": 0, "contra": 0, "abstencao": 0}
    for v in pauta.votos.values():
        if v in contagem:
            contagem[v] += 1

    return {
        "pauta": {
            "id": pauta.id,
            "titulo": pauta.titulo,
            "status": pauta.status,
            "total_votos": len(pauta.votos)
        },
        "ja_votou": ja_votou,
        "resultados": contagem
    }

@router.post("/votar")
def registrar_voto(dados: VotoRequest):
    pauta_alvo = None
    for p in db["pautas"]:
        if p.id == dados.pauta_id:
            pauta_alvo = p
            break
    
    if not pauta_alvo: raise HTTPException(404, "Pauta não encontrada")
    if pauta_alvo.status != "ABERTA": raise HTTPException(400, "Votação encerrada.")
    if dados.credencial not in db["usuarios"]: raise HTTPException(401, "Usuário inválido")

    pauta_alvo.votos[dados.credencial] = dados.opcao
    return {"msg": "Voto computado"}