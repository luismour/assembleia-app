from fastapi import APIRouter, HTTPException
from typing import Optional
from app.models import VotoModel
from app.database import db, get_pauta_ativa

router = APIRouter(prefix="/api")

@router.post("/login")
def login(credencial: str):
    delegado = db["delegados"].get(credencial)
    if not delegado: 
        raise HTTPException(401, "Credencial inválida! Cadastre o grupo primeiro.")
    return delegado

@router.get("/pauta-ativa")
def get_pauta_ativa_endpoint(credencial: Optional[str] = None):
    pauta = get_pauta_ativa()
    if not pauta: return {"pauta": None}

    ja_votou = False
    if credencial and credencial in pauta.votos: ja_votou = True

    contagem = {"favor": 0, "contra": 0, "abstencao": 0}
    for v in pauta.votos.values(): contagem[v] += 1

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
def votar(voto: VotoModel):
    if voto.credencial not in db["delegados"]:
        raise HTTPException(401, "Não autorizado")
    
    pauta = get_pauta_ativa()
    # Verifica validade
    if not pauta or pauta.id != voto.pauta_id or pauta.status != "ABERTA":
        raise HTTPException(400, "Votação fechada ou inválida")
    
    if voto.credencial in pauta.votos:
        raise HTTPException(400, "Já votou!")
        
    pauta.votos[voto.credencial] = voto.opcao
    return {"msg": "Voto computado"}