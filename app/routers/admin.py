from fastapi import APIRouter, HTTPException, Depends, Body
from app.models import PautaModel, GrupoModel, LoginAdminModel
from app.database import db, Pauta, get_pauta_por_id
from app.security import verificar_admin, criar_token_admin, remover_token, SENHA_ADMIN

router = APIRouter(prefix="/api")

# --- AUTH ---
@router.post("/admin/login")
def admin_login(body: LoginAdminModel):
    if body.senha == SENHA_ADMIN:
        return {"token": criar_token_admin(), "msg": "Login autorizado"}
    raise HTTPException(401, "Senha incorreta")

@router.post("/admin/logout")
def admin_logout(x_admin_token: str = None):
    remover_token(x_admin_token)
    return {"msg": "Saiu"}

# --- GRUPOS ---
@router.get("/grupos", dependencies=[Depends(verificar_admin)])
def listar_grupos():
    return sorted(db["lista_grupos"])

@router.post("/grupos", dependencies=[Depends(verificar_admin)])
def adicionar_grupo(grupo: GrupoModel):
    num = grupo.numero.strip()
    if num in db["lista_grupos"]:
        raise HTTPException(400, "Grupo já cadastrado")
    
    db["lista_grupos"].append(num)
    # Gera credenciais
    db["delegados"][f"{num}-1"] = {"id": f"{num}-1", "grupo": num, "nome": f"GE {num} - Del. 1"}
    db["delegados"][f"{num}-2"] = {"id": f"{num}-2", "grupo": num, "nome": f"GE {num} - Del. 2"}
    return {"msg": "Grupo cadastrado"}

@router.delete("/grupos/{numero}", dependencies=[Depends(verificar_admin)])
def remover_grupo(numero: str):
    if numero in db["lista_grupos"]:
        db["lista_grupos"].remove(numero)
        db["delegados"].pop(f"{numero}-1", None)
        db["delegados"].pop(f"{numero}-2", None)
        return {"msg": "Grupo removido"}
    raise HTTPException(404, "Grupo não encontrado")

# --- PAUTAS ADMIN ---
@router.get("/dados-admin", dependencies=[Depends(verificar_admin)])
def get_dados_admin():
    resultado = []
    total_possivel = len(db["lista_grupos"]) * 2
    
    for p in reversed(db["pautas"]):
        contagem = {"favor": 0, "contra": 0, "abstencao": 0}
        for v in p.votos.values():
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

@router.post("/pautas", dependencies=[Depends(verificar_admin)])
def criar_pauta(pauta: PautaModel):
    nova_pauta = Pauta(pauta.titulo)
    db["pautas"].append(nova_pauta)
    return {"msg": "Pauta criada", "id": nova_pauta.id}

@router.post("/pautas/{pauta_id}/status", dependencies=[Depends(verificar_admin)])
def mudar_status(pauta_id: str, status: str = Body(..., embed=True)):
    pauta = get_pauta_por_id(pauta_id)
    if not pauta:
        raise HTTPException(404, "Pauta não encontrada")
    
    if status == "ABERTA":
        for outra in db["pautas"]:
            if outra.status == "ABERTA": outra.status = "ENCERRADA"
    
    pauta.status = status
    return {"msg": "Status alterado"}