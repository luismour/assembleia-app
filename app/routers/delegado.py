import secrets
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Union
from app.database import get_db
from app import models
from app.email_utils import enviar_token_email

router = APIRouter(prefix="/api")

# --- VALIDADOR CPF ---
def validar_cpf_algo(cpf: str) -> bool:
    numbers = [int(digit) for digit in cpf if digit.isdigit()]
    if len(numbers) != 11: return False
    if len(set(numbers)) == 1: return False
    sum_prod = sum(a*b for a, b in zip(numbers[0:9], range(10, 1, -1)))
    expected = (sum_prod * 10 % 11) % 10
    if numbers[9] != expected: return False
    sum_prod = sum(a*b for a, b in zip(numbers[0:10], range(11, 1, -1)))
    expected = (sum_prod * 10 % 11) % 10
    if numbers[10] != expected: return False
    return True

# --- MODELOS ---
class LoginRequest(BaseModel):
    token: str
    cpf: str

class VotoRequest(BaseModel):
    token: str
    pauta_id: str
    opcao: Union[str, List[str]]

class CadastroInput(BaseModel):
    nome: str
    grupo: str
    cpf: str
    email: EmailStr

class HeartbeatInput(BaseModel):
    token: str

# --- ROTAS ---

@router.post("/login")
def login_delegado(dados: LoginRequest, db: Session = Depends(get_db)):
    token_input = dados.token.strip().upper()
    user = db.query(models.Usuario).filter(models.Usuario.token == token_input).first()
    
    if not user:
        raise HTTPException(404, "Código de acesso inválido.")
    
    # Valida CPF
    if not validar_cpf_algo(dados.cpf):
        raise HTTPException(400, "CPF inválido.")

    cpf_digitado = "".join(filter(str.isdigit, dados.cpf))
    cpf_salvo = "".join(filter(str.isdigit, user.cpf or ""))
    
    if cpf_digitado != cpf_salvo:
        raise HTTPException(401, "O CPF informado não corresponde a este código.")

    if not user.checkin:
        raise HTTPException(403, "Delegado não credenciado. Dirija-se à mesa.")

    # Concorrência
    if user.last_seen:
        agora = datetime.utcnow()
        tempo_limite = agora - timedelta(seconds=15)
        if user.last_seen > tempo_limite:
            raise HTTPException(409, "Sessão ativa em outro dispositivo.")

    user.last_seen = datetime.utcnow()
    db.commit()

    # --- RETORNA DICIONÁRIO PARA GARANTIR CAMPOS ---
    return {
        "id": user.id,
        "nome": user.nome,
        "grupo": user.grupo, 
        "token": user.token,
        "checkin": user.checkin,
        "email": user.email
    }

@router.post("/heartbeat")
def heartbeat(dados: HeartbeatInput, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.token == dados.token).first()
    if user:
        user.last_seen = datetime.utcnow()
        db.commit()
    return {"status": "alive"}

@router.post("/logout-delegado")
def logout_delegado(dados: HeartbeatInput, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.token == dados.token).first()
    if user:
        user.last_seen = datetime.utcnow() - timedelta(minutes=10)
        db.commit()
    return {"status": "logged_out"}

@router.get("/pauta-ativa")
def get_pauta_ativa(credencial: str = None, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.token == credencial).first()
    
    asm = db.query(models.Assembleia).filter(models.Assembleia.ativa == True).first()
    if not asm: return {"evento": "Escoteiros", "pauta": None}

    pauta = db.query(models.Pauta).filter(models.Pauta.assembleia_id == asm.id, models.Pauta.status == "ABERTA").first()
    if not pauta:
        pauta = db.query(models.Pauta).filter(models.Pauta.assembleia_id == asm.id).order_by(models.Pauta.id.desc()).first()

    if not pauta: return {"evento": asm.titulo, "pauta": None}

    votos_db = db.query(models.Voto).filter(models.Voto.pauta_id == pauta.id).all()
    candidatos_lista = json.loads(pauta.candidatos_str) if pauta.candidatos_str else []
    
    if pauta.tipo == "SIMPLES":
        contagem = {"favor": 0, "contra": 0, "abstencao": 0}
        for v in votos_db:
            val = json.loads(v.escolha_str)
            if val in contagem: contagem[val] += 1
    else:
        contagem = {c: 0 for c in candidatos_lista}
        for v in votos_db:
            escolhas = json.loads(v.escolha_str)
            if isinstance(escolhas, list):
                for c in escolhas:
                    if c in contagem: contagem[c] += 1
            elif escolhas in contagem:
                contagem[escolhas] += 1

    pode_votar = True
    meus_votos = []
    
    if user:
        voto_existente = db.query(models.Voto).filter(models.Voto.pauta_id == pauta.id, models.Voto.usuario_id == user.id).first()
        if voto_existente:
            pode_votar = False
            raw_voto = json.loads(voto_existente.escolha_str)
            meus_votos = raw_voto if isinstance(raw_voto, list) else [raw_voto]

    return {
        "evento": asm.titulo,
        "pauta": {
            "id": pauta.id,
            "titulo": pauta.titulo,
            "status": pauta.status,
            "tipo": pauta.tipo,
            "candidatos": candidatos_lista,
            "max_escolhas": pauta.max_escolhas,
            "total_votos": len(votos_db)
        },
        "meus_votos": meus_votos,
        "pode_votar": pode_votar,
        "resultados": contagem
    }

@router.post("/votar")
def registrar_voto(dados: VotoRequest, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.token == dados.token).first()
    if not user: raise HTTPException(401, "Token inválido")
    if not user.checkin: raise HTTPException(403, "Check-in necessário")

    pauta = db.query(models.Pauta).filter(models.Pauta.id == dados.pauta_id).first()
    if not pauta or pauta.status != "ABERTA": raise HTTPException(400, "Votação fechada")
    
    existente = db.query(models.Voto).filter(models.Voto.pauta_id == pauta.id, models.Voto.usuario_id == user.id).first()
    if existente: raise HTTPException(400, "Já votou")

    if pauta.tipo == "ELEICAO":
        if not isinstance(dados.opcao, list): raise HTTPException(400, "Erro formato lista")
        if len(dados.opcao) > pauta.max_escolhas: raise HTTPException(400, "Limite excedido")
        validos = json.loads(pauta.candidatos_str)
        for c in dados.opcao:
            if c not in validos: raise HTTPException(400, f"Inválido: {c}")

    novo_voto = models.Voto(
        pauta_id=pauta.id,
        usuario_id=user.id,
        escolha_str=json.dumps(dados.opcao)
    )
    db.add(novo_voto)
    db.commit()
    
    return {"msg": "Voto registrado"}

@router.get("/historico")
def get_historico(credencial: str, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.token == credencial).first()
    if not user: return []
    
    asm = db.query(models.Assembleia).filter(models.Assembleia.ativa == True).first()
    if not asm: return []

    pautas = db.query(models.Pauta).filter(models.Pauta.assembleia_id == asm.id).all()
    pautas.reverse() 
    
    res = []
    for p in pautas:
        voto = db.query(models.Voto).filter(models.Voto.pauta_id == p.id, models.Voto.usuario_id == user.id).first()
        if voto or p.status == "ENCERRADA":
            v_val = json.loads(voto.escolha_str) if voto else []
            v_fmt = v_val if isinstance(v_val, list) else ([v_val] if v_val else [])
            res.append({"titulo": p.titulo, "status": p.status, "votos": v_fmt})
    return res

# === AUTO-CADASTRO ATUALIZADO ===
@router.post("/auto-cadastro")
async def auto_cadastro(
    dados: CadastroInput, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    if not dados.nome or not dados.grupo or not dados.cpf or not dados.email:
        raise HTTPException(400, "Dados incompletos")

    if not validar_cpf_algo(dados.cpf):
        raise HTTPException(400, "CPF inválido. Verifique os números.")

    cpf_limpo = "".join(filter(str.isdigit, dados.cpf))

    # Verifica CPF duplicado
    todos = db.query(models.Usuario).all()
    for u in todos:
        if "".join(filter(str.isdigit, u.cpf)) == cpf_limpo:
            raise HTTPException(400, "CPF já cadastrado")

    # Gera ID
    existentes = [u for u in todos if u.grupo == dados.grupo]
    prox = 1
    if existentes:
        try:
            ids = [int(u.id.split('-')[1]) for u in existentes]
            prox = max(ids) + 1
        except: prox = len(existentes) + 1
    
    user_id = f"{dados.grupo}-{prox}"

    # Gera Token
    while True:
        token = secrets.token_hex(3).upper()
        if not db.query(models.Usuario).filter(models.Usuario.token == token).first():
            break

    # Salva com Email
    novo = models.Usuario(
        id=user_id, nome=dados.nome.strip().title(), grupo=dados.grupo,
        cpf=dados.cpf, email=dados.email, token=token, checkin=False
    )
    db.add(novo)
    db.commit()

    # Envia email em segundo plano
    background_tasks.add_task(enviar_token_email, dados.email, dados.nome, token, user_id)

    return {"msg": "Sucesso", "token": token, "id": user_id}