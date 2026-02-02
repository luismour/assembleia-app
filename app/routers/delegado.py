from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api")

# --- DATABASE ---
db = {
    "pautas": [],
    "usuarios": {},        
    "lista_grupos": [],
    "grupos_meta": {}      
}

# --- MODELS ---
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
        self.status = "AGUARDANDO" 
        # Structure change: credencial -> list of votes
        # Ex: { "107-1": ["favor"], "15-2": ["favor", "abstencao"] }
        self.votos = {} 

def get_pauta_ativa():
    for p in db["pautas"]:
        if p.status == "ABERTA":
            return p
    if db["pautas"]:
        return db["pautas"][-1]
    return None

# --- ROUTERS ---

@router.post("/login")
def login_delegado(credencial: str):
    if credencial not in db["usuarios"]:
        raise HTTPException(status_code=404, detail="Credencial inválida.")
    return db["usuarios"][credencial]

@router.get("/pauta-ativa")
def get_pauta_ativa_endpoint(credencial: Optional[str] = None):
    pauta = get_pauta_ativa()
    if not pauta: return {"pauta": None}

    votos_usuario = []
    pode_votar = True
    
    if credencial and credencial in pauta.votos:
        votos_usuario = pauta.votos[credencial]
        # Logic: Can vote if they have less than 2 votes
        if len(votos_usuario) >= 2:
            pode_votar = False

    # Count votes (flattening the lists)
    contagem = {"favor": 0, "contra": 0, "abstencao": 0}
    for lista_votos in pauta.votos.values():
        for v in lista_votos:
            if v in contagem:
                contagem[v] += 1

    return {
        "pauta": {
            "id": pauta.id,
            "titulo": pauta.titulo,
            "status": pauta.status,
            "total_votos": sum(len(v) for v in pauta.votos.values())
        },
        "meus_votos": votos_usuario,
        "pode_votar": pode_votar,
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
    if pauta_alvo.status != "ABERTA": raise HTTPException(400, "A votação não está aberta.")
    if dados.credencial not in db["usuarios"]: raise HTTPException(401, "Usuário inválido")

    # Initialize list if not exists
    if dados.credencial not in pauta_alvo.votos:
        pauta_alvo.votos[dados.credencial] = []

    # Check limit of 2 votes
    if len(pauta_alvo.votos[dados.credencial]) >= 2:
        raise HTTPException(400, "Você já registrou seus 2 votos nesta pauta.")

    pauta_alvo.votos[dados.credencial].append(dados.opcao)
    return {"msg": "Voto computado"}

@router.get("/historico")
def get_historico(credencial: str):
    if credencial not in db["usuarios"]:
        raise HTTPException(404, "Usuário não encontrado")
    
    historico = []
    # Iterate backwards to show newest first
    for p in reversed(db["pautas"]):
        votos = p.votos.get(credencial, [])
        if votos: # Only show agendas where they voted
            historico.append({
                "titulo": p.titulo,
                "status": p.status,
                "votos": votos
            })
            
    return historico