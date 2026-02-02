from pydantic import BaseModel

class PautaModel(BaseModel):
    titulo: str

class GrupoModel(BaseModel):
    numero: str

class VotoModel(BaseModel):
    credencial: str
    pauta_id: str
    opcao: str

class LoginAdminModel(BaseModel):
    senha: str