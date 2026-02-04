from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api")

# --- BANCO DE DADOS EM MEMÓRIA ---
db = {
    "assembleias": [],     
    "assembleia_ativa": None, 
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
    def __init__(self, id, titulo, assembleia_id):
        self.id = id
        self.titulo = titulo
        self.assembleia_id = assembleia_id 
        self.status = "AGUARDANDO" 
        self.votos = {} 

def get_pauta_ativa():
    if not db["assembleia_ativa"]:
        return None

    pautas_da_assembleia = [p for p in db["pautas"] if p.assembleia_id == db["assembleia_ativa"]]
    
    for p in pautas_da_assembleia:
        if p.status == "ABERTA":
            return p
    if pautas_da_assembleia:
        return pautas_da_assembleia[-1]
    return None

def get_nome_assembleia():
    aid = db["assembleia_ativa"]
    if not aid: return "Escoteiros do Brasil"
    for a in db["assembleias"]:
        if a["id"] == aid: return a["titulo"]
    return "Evento Escoteiro"

# --- ROTAS ---

@router.post("/login")
def login_delegado(credencial: str):
    if credencial not in db["usuarios"]:
        raise HTTPException(status_code=404, detail="Credencial inválida.")
    return db["usuarios"][credencial]

@router.get("/pauta-ativa")
def get_pauta_ativa_endpoint(credencial: Optional[str] = None):
    # Retorna também o nome do evento para o front
    nome_evento = get_nome_assembleia()
    
    pauta = get_pauta_ativa()
    
    # Estrutura base de resposta
    response = {
        "evento": nome_evento,
        "pauta": None,
        "meus_votos": [],
        "pode_votar": False,
        "resultados": {"favor": 0, "contra": 0, "abstencao": 0}
    }

    if not pauta: 
        return response

    votos_usuario = []
    pode_votar = True
    
    if credencial and credencial in pauta.votos:
        votos_usuario = pauta.votos[credencial]
        if len(votos_usuario) >= 1:
            pode_votar = False

    contagem = {"favor": 0, "contra": 0, "abstencao": 0}
    for lista_votos in pauta.votos.values():
        for v in lista_votos:
            if v in contagem:
                contagem[v] += 1

    response.update({
        "pauta": {
            "id": pauta.id,
            "titulo": pauta.titulo,
            "status": pauta.status,
            "total_votos": sum(len(v) for v in pauta.votos.values())
        },
        "meus_votos": votos_usuario,
        "pode_votar": pode_votar,
        "resultados": contagem
    })
    
    return response

@router.post("/votar")
def registrar_voto(dados: VotoRequest):
    pauta_alvo = None
    for p in db["pautas"]:
        if p.id == dados.pauta_id:
            pauta_alvo = p
            break
    
    if not pauta_alvo: raise HTTPException(404, "Pauta não encontrada")
    if pauta_alvo.status != "ABERTA": raise HTTPException(400, "A votação não está aberta.")

    if pauta_alvo.assembleia_id != db["assembleia_ativa"]:
        raise HTTPException(400, "Esta pauta não pertence à assembleia ativa.")

    if dados.credencial not in db["usuarios"]: raise HTTPException(401, "Usuário inválido")

    if dados.credencial not in pauta_alvo.votos:
        pauta_alvo.votos[dados.credencial] = []

    if len(pauta_alvo.votos[dados.credencial]) >= 1:
        raise HTTPException(400, "Você já votou nesta pauta.")

    pauta_alvo.votos[dados.credencial].append(dados.opcao)
    return {"msg": "Voto computado"}

@router.get("/historico")
def get_historico(credencial: str):
    if credencial not in db["usuarios"]:
        raise HTTPException(404, "Usuário não encontrado")
    
    historico = []
    aid = db["assembleia_ativa"]
    
    for p in reversed(db["pautas"]):
        if p.assembleia_id == aid: 
            votos = p.votos.get(credencial, [])
            if votos or p.status == "ENCERRADA":
                historico.append({
                    "titulo": p.titulo,
                    "status": p.status,
                    "votos": votos
                })
            
    return historico