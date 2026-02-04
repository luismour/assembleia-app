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
import uuid
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

load_dotenv()

router = APIRouter(prefix="/api")

SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-padrao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_DB = {
    # Hash da senha "saps"
    "admin": "$2b$12$Jf0VrIbgza8gk8YoXqYlxeho3.c2Y4ZGWKXyKESDrAxaYfZkPzkAa"
}

class SenhaAdmin(BaseModel):
    usuario: str = "admin"
    senha: str

class AssembleiaInput(BaseModel):
    titulo: str

class PautaInput(BaseModel):
    titulo: str

class StatusPauta(BaseModel):
    status: str

class GrupoNomesInput(BaseModel):
    numero: str
    nomes: List[str]

# --- FUNÇÕES AUXILIARES ---
def verificar_senha(senha_pura, senha_hash): 
    return pwd_context.verify(senha_pura, senha_hash)

def criar_token_acesso(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_admin(x_admin_token: str = Header(None), token_query: str = Query(None)):
    token = x_admin_token or token_query
    if not token: raise HTTPException(401, "Token não fornecido")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario: str = payload.get("sub")
        if not usuario or usuario not in ADMIN_DB: raise HTTPException(401, "Inválido")
        return usuario
    except JWTError: raise HTTPException(401, "Token inválido")

# --- LOGIN ADMIN ---
@router.post("/admin/login")
def admin_login(dados: SenhaAdmin):
    if dados.usuario not in ADMIN_DB: raise HTTPException(400, "Erro")
    if not verificar_senha(dados.senha, ADMIN_DB[dados.usuario]): raise HTTPException(400, "Erro")
    return {"token": criar_token_acesso(data={"sub": dados.usuario})}

@router.post("/admin/logout")
def admin_logout(): return {"message": "Saiu"}

# --- ROTA PÚBLICA (TELÃO) ---
@router.get("/telao-dados")
def get_telao_publico():
    aid = db["assembleia_ativa"]
    nome_evento = "Escoteiros do Brasil"
    if aid:
        for a in db["assembleias"]:
            if a["id"] == aid: nome_evento = a["titulo"]

    pautas = [p for p in reversed(db["pautas"]) if p.assembleia_id == aid] if aid else []
    pauta_ativa = None
    for p in pautas:
        if p.status == "ABERTA":
            pauta_ativa = p
            break
    if not pauta_ativa and pautas: pauta_ativa = pautas[0]

    if not pauta_ativa: return {"pauta": None, "evento": nome_evento}

    contagem = {"favor": 0, "contra": 0, "abstencao": 0}
    total = 0
    for lista in pauta_ativa.votos.values():
        for v in lista:
            contagem[v] += 1
            total += 1
            
    res_final = "EM ANDAMENTO"
    if pauta_ativa.status == "ENCERRADA":
        if contagem["favor"] > contagem["contra"]: res_final = "APROVADA"
        elif contagem["contra"] >= contagem["favor"] and total > 0: res_final = "REPROVADA"
        else: res_final = "SEM VOTOS"

    return {
        "evento": nome_evento,
        "pauta": {
            "titulo": pauta_ativa.titulo,
            "status": pauta_ativa.status,
            "total_votos": total,
            "resultados": contagem,
            "resultado_final": res_final
        }
    }

# --- ROTAS ADMIN ---

@router.get("/assembleias")
def listar_assembleias(usuario: str = Depends(verificar_admin)):
    return {"lista": db["assembleias"], "ativa": db["assembleia_ativa"]}

@router.post("/assembleias")
def criar_assembleia(dados: AssembleiaInput, usuario: str = Depends(verificar_admin)):
    nova = {"id": str(uuid.uuid4()), "titulo": dados.titulo, "data": datetime.now().isoformat()}
    db["assembleias"].append(nova)
    if not db["assembleia_ativa"]: db["assembleia_ativa"] = nova["id"]
    return nova

@router.post("/assembleias/{id}/ativar")
def ativar_assembleia(id: str, usuario: str = Depends(verificar_admin)):
    if not any(a["id"] == id for a in db["assembleias"]): raise HTTPException(404, "Não encontrada")
    db["assembleia_ativa"] = id
    return {"msg": "Ativada"}

@router.get("/grupos")
def listar_grupos(usuario: str = Depends(verificar_admin)):
    agrupado = {}
    for cred, user in db["usuarios"].items():
        g = user["grupo"]
        if g not in agrupado: agrupado[g] = []
        agrupado[g].append(user)
    
    lista = [{"numero": k, "quantidade": len(v), "delegados": v} for k, v in agrupado.items()]
    lista.sort(key=lambda x: int(x["numero"]) if x["numero"].isdigit() else x["numero"])
    return lista

@router.post("/grupos")
def cadastrar_grupo(dados: GrupoNomesInput, usuario: str = Depends(verificar_admin)):
    if "grupos_meta" not in db: db["grupos_meta"] = {}
    if "usuarios" not in db: db["usuarios"] = {}
    if "lista_grupos" not in db: db["lista_grupos"] = []
    
    prox = 1
    existentes = [k for k in db["usuarios"] if db["usuarios"][k]["grupo"] == dados.numero]
    if existentes: prox = max([int(k.split('-')[1]) for k in existentes]) + 1
    
    db["grupos_meta"][dados.numero] = len(existentes) + len(dados.nomes)
    if dados.numero not in db["lista_grupos"]: db["lista_grupos"].append(dados.numero)
    
    novos = []
    for nome in dados.nomes:
        cred = f"{dados.numero}-{prox}"
        obj = {"id": cred, "nome": nome.strip(), "grupo": dados.numero}
        db["usuarios"][cred] = obj
        novos.append(obj)
        prox += 1
    return {"msg": "Ok", "delegados": novos}

@router.delete("/grupos/{numero}")
def remover_grupo(numero: str, usuario: str = Depends(verificar_admin)):
    if "grupos_meta" in db: db["grupos_meta"].pop(numero, 0)
    if numero in db["lista_grupos"]: db["lista_grupos"].remove(numero)
    rem = [k for k, v in db["usuarios"].items() if v["grupo"] == numero]
    for k in rem: del db["usuarios"][k]
    return {"msg": "Removido"}

@router.delete("/usuarios/{credencial}")
def remover_delegado(credencial: str, usuario: str = Depends(verificar_admin)):
    if credencial in db["usuarios"]:
        del db["usuarios"][credencial]
        return {"msg": "Removido"}
    raise HTTPException(404, "Não encontrado")

@router.get("/dados-admin")
def get_dados_admin(usuario: str = Depends(verificar_admin)):
    aid = db["assembleia_ativa"]
    total_delegados = len(db["usuarios"])
    pautas = [p for p in reversed(db["pautas"]) if p.assembleia_id == aid] if aid else []
    
    res = []
    for p in pautas:
        cont = {"favor": 0, "contra": 0, "abstencao": 0}
        detalhes_votos = [] 

        for cred, lista_votos in p.votos.items():
            user_data = db["usuarios"].get(cred, {"nome": "Desconhecido", "grupo": "-"})
            for v in lista_votos:
                cont[v] += 1
                detalhes_votos.append({
                    "credencial": cred,
                    "nome": user_data["nome"],
                    "grupo": user_data["grupo"],
                    "voto": v
                })
        
        tot = sum(len(v) for v in p.votos.values())
        r_txt = "EM ANDAMENTO"
        if p.status == "ENCERRADA":
            if cont["favor"] > cont["contra"]: r_txt = "APROVADA"
            elif cont["contra"] >= cont["favor"] and tot > 0: r_txt = "REPROVADA"
            else: r_txt = "SEM VOTOS"
            
        res.append({
            "id": p.id, "titulo": p.titulo, "status": p.status,
            "total_votos": tot, "esperados": total_delegados,
            "resultados": cont, "resultado_final": r_txt,
            "votos_detalhados": detalhes_votos
        })
    
    t_asm = "Nenhuma Ativa"
    if aid:
        for a in db["assembleias"]:
            if a["id"] == aid: t_asm = a["titulo"]
            
    return {"pautas": res, "assembleia": t_asm}

@router.post("/pautas")
def criar_pauta(dados: PautaInput, usuario: str = Depends(verificar_admin)):
    aid = db["assembleia_ativa"]
    if not aid: raise HTTPException(400, "Sem assembleia ativa")
    from app.routers.delegado import Pauta
    nova = Pauta(id=str(uuid.uuid4()), titulo=dados.titulo, assembleia_id=aid)
    db["pautas"].append(nova)
    return nova

@router.post("/pautas/{id}/status")
def mudar_status_pauta(id: str, dados: StatusPauta, usuario: str = Depends(verificar_admin)):
    p = next((x for x in db["pautas"] if x.id == id), None)
    if not p: raise HTTPException(404, "404")
    if dados.status == "ABERTA":
        for x in db["pautas"]:
            if x.assembleia_id == p.assembleia_id and x.status == "ABERTA": x.status = "ENCERRADA"
    p.status = dados.status
    return {"msg": "Ok"}

# --- EXPORTAÇÃO EXCEL ---
@router.get("/exportar")
def exportar_relatorio(x_admin_token: str = Header(None), token: str = Query(None)):
    usuario = verificar_admin(x_admin_token, token)
    aid = db["assembleia_ativa"]
    
    titulo_evento = "Relatorio"
    if aid:
        for a in db["assembleias"]:
            if a["id"] == aid: titulo_evento = a["titulo"]

    wb = Workbook()
    
    # Estilos
    header_font = Font(name='Calibri', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="002d62", end_color="002d62", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    # Aba 1: Resumo
    ws1 = wb.active
    ws1.title = "Resumo Geral"
    
    ws1.merge_cells('A1:G1')
    ws1['A1'].value = f"RELATÓRIO: {titulo_evento.upper()}"
    ws1['A1'].font = Font(size=14, bold=True, color="002d62")
    ws1['A1'].alignment = center_align

    headers1 = ["Ordem", "Pauta / Pergunta", "Status", "Resultado", "Total Votos", "Favor", "Contra", "Abstenção"]
    ws1.append(headers1)
    for cell in ws1[2]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    pautas_filtradas = [p for p in db["pautas"] if p.assembleia_id == aid] if aid else []
    
    for idx, p in enumerate(pautas_filtradas, 1):
        f, c, a, t = 0, 0, 0, 0
        for lista in p.votos.values():
            for v in lista:
                t += 1
                if v == "favor": f += 1
                elif v == "contra": c += 1
                elif v == "abstencao": a += 1
        
        res_txt = "-"
        if p.status == "ENCERRADA":
            if f > c: res_txt = "APROVADA"
            elif c >= f and t > 0: res_txt = "REPROVADA"
            else: res_txt = "SEM VOTOS"

        ws1.append([idx, p.titulo, p.status, res_txt, t, f, c, a])
        for cell in ws1[ws1.max_row]:
            cell.border = thin_border
            cell.alignment = center_align
            if cell.column == 2: cell.alignment = left_align

    ws1.column_dimensions['B'].width = 50
    for col in ['A','C','D','E','F','G','H']: ws1.column_dimensions[col].width = 15

    # Aba 2: Votos Nominais
    ws2 = wb.create_sheet("Votos Nominais")
    headers2 = ["Pauta", "Credencial", "Nome do Delegado", "Grupo", "Voto Registrado", "Horário (Registro)"]
    ws2.append(headers2)
    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for p in pautas_filtradas:
        for cred, lista_votos in p.votos.items():
            user_data = db["usuarios"].get(cred, {"nome": "Desconhecido", "grupo": "-"})
            nome = user_data["nome"]
            grupo = user_data["grupo"]
            
            for voto in lista_votos:
                voto_fmt = voto.upper()
                if voto == "favor": voto_fmt = "A FAVOR"
                
                ws2.append([p.titulo, cred, nome, f"GE {grupo}", voto_fmt, datetime.now().strftime("%H:%M")])
                
                for cell in ws2[ws2.max_row]:
                    cell.border = thin_border
                    cell.alignment = left_align
                    if cell.column in [2, 5]: cell.alignment = center_align

    ws2.column_dimensions['A'].width = 40
    ws2.column_dimensions['B'].width = 12
    ws2.column_dimensions['C'].width = 35
    ws2.column_dimensions['D'].width = 15
    ws2.column_dimensions['E'].width = 15
    ws2.column_dimensions['F'].width = 15

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    headers = {'Content-Disposition': f'attachment; filename="Relatorio_{titulo_evento}.xlsx"'}
    return StreamingResponse(buffer, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')