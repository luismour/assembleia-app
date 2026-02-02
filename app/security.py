from fastapi import HTTPException, Header
from uuid import uuid4
from typing import Optional

SENHA_ADMIN = "saps"
admin_tokens = set()

def verificar_admin(x_admin_token: Optional[str] = Header(None)):
    if x_admin_token not in admin_tokens:
        raise HTTPException(status_code=401, detail="Acesso não autorizado")
    return True

def criar_token_admin():
    token = str(uuid4())
    admin_tokens.add(token)
    return token

def remover_token(token: str):
    if token in admin_tokens:
        admin_tokens.remove(token)