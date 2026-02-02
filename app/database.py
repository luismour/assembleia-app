from uuid import uuid4

class Pauta:
    def __init__(self, titulo):
        self.id = str(uuid4())[:8]
        self.titulo = titulo
        self.status = "AGUARDANDO"
        self.votos = {} # {credencial: opcao}

# --- BANCO DE DADOS EM MEMÓRIA ---
# Instanciamos aqui para ser importado globalmente
db = {
    "delegados": {},      # Armazena usuários: {'107-1': {...}}
    "lista_grupos": [],   # Armazena numerais: ['107', '14']
    "pautas": []          # Lista de objetos Pauta
}

# Funções auxiliares para não acessar o dict direto nas rotas
def get_pauta_por_id(pauta_id: str):
    for p in db["pautas"]:
        if p.id == pauta_id:
            return p
    return None

def get_pauta_ativa():
    pauta_ativa = None
    # 1. Procura aberta
    for p in db["pautas"]:
        if p.status == "ABERTA":
            pauta_ativa = p
            break
    # 2. Se não tem aberta, pega a última encerrada
    if not pauta_ativa and db["pautas"]:
         ultimo = db["pautas"][-1]
         if ultimo.status == "ENCERRADA":
             pauta_ativa = ultimo
    return pauta_ativa