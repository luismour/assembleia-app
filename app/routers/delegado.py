from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api")

# --- BANCO DE DADOS EM MEMÓRIA (GLOBAL) ---
# É aqui que corrigimos o erro: inicializando todas as chaves
db = {
    "pautas": [],
    "usuarios": {},        # <--- AQUI ESTAVA FALTANDO
    "lista_grupos": [],
    "grupos_meta": {}      # <--- Importante para a nova lógica de quantidade
}

# --- MODELOS ---
class LoginRequest(BaseModel):
    credencial: str

class VotoRequest(BaseModel):
    credencial: str
    pauta_id: str
    opcao: str # 'favor' ou 'contra'

class Pauta:
    def __init__(self, id, titulo):
        self.id = id
        self.titulo = titulo
        self.status = "CRIADA" # CRIADA, ABERTA, ENCERRADA
        self.votos = {} # { "107-1": "favor" }

# --- FUNÇÕES AUXILIARES ---
def get_pauta_ativa():
    # Retorna a pauta ABERTA ou a última ENCERRADA para exibição
    for p in db["pautas"]:
        if p.status == "ABERTA":
            return p
    # Se nenhuma aberta, pega a última (se houver)
    if db["pautas"]:
        return db["pautas"][-1]
    return None

# --- ROTAS DELEGADO ---

@router.post("/login")
def login_delegado(credencial: str):
    # Verifica se o usuário existe no DB
    if credencial not in db["usuarios"]:
        raise HTTPException(status_code=404, detail="Credencial inválida ou grupo não cadastrado.")
    
    return db["usuarios"][credencial]

@router.get("/pauta-ativa")
def get_pauta_ativa_endpoint(credencial: Optional[str] = None):
    pauta = get_pauta_ativa()
    if not pauta: return {"pauta": None}

    ja_votou = False
    if credencial and credencial in pauta.votos: ja_votou = True

    # Contagem parcial (apenas Favor e Contra)
    contagem = {"favor": 0, "contra": 0}
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
    # 1. Achar a pauta
    pauta_alvo = None
    for p in db["pautas"]:
        if p.id == dados.pauta_id:
            pauta_alvo = p
            break
    
    if not pauta_alvo:
        raise HTTPException(404, "Pauta não encontrada")
    
    if pauta_alvo.status != "ABERTA":
        raise HTTPException(400, "Votação encerrada ou não iniciada.")

    # 2. Verificar usuario
    if dados.credencial not in db["usuarios"]:
        raise HTTPException(401, "Usuário inválido")

    # 3. Registrar Voto
    pauta_alvo.votos[dados.credencial] = dados.opcao
    return {"msg": "Voto computado"}