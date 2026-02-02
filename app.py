import uvicorn
from fastapi import FastAPI, HTTPException, Body, Header, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from uuid import uuid4

app = FastAPI()

SENHA_ADMIN = "saps"  
admin_tokens = set()  

class LoginAdminModel(BaseModel):
    senha: str

class PautaModel(BaseModel):
    titulo: str

class GrupoModel(BaseModel):
    numero: str

class VotoModel(BaseModel):
    credencial: str
    pauta_id: str
    opcao: str

class Pauta:
    def __init__(self, titulo):
        self.id = str(uuid4())[:8]
        self.titulo = titulo
        self.status = "AGUARDANDO"
        self.votos = {} 

delegados_db = {}
lista_grupos = []
dados = { "pautas": [] }

def verificar_admin(x_admin_token: Optional[str] = Header(None)):
    if x_admin_token not in admin_tokens:
        raise HTTPException(status_code=401, detail="Acesso não autorizado")
    return True

# --- API (BACKEND) ---

# AUTENTICAÇÃO DO ADMIN
@app.post("/api/admin/login")
def admin_login(body: LoginAdminModel):
    if body.senha == SENHA_ADMIN:
        novo_token = str(uuid4())
        admin_tokens.add(novo_token)
        return {"token": novo_token, "msg": "Login autorizado"}
    raise HTTPException(status_code=401, detail="Senha incorreta")

@app.post("/api/admin/logout")
def admin_logout(x_admin_token: Optional[str] = Header(None)):
    if x_admin_token in admin_tokens:
        admin_tokens.remove(x_admin_token)
    return {"msg": "Saiu"}

# GESTÃO DE GRUPOS 
@app.get("/api/grupos")
def listar_grupos(auth: bool = Depends(verificar_admin)):
    return sorted(lista_grupos)

@app.post("/api/grupos")
def adicionar_grupo(grupo: GrupoModel, auth: bool = Depends(verificar_admin)):
    num = grupo.numero.strip()
    if num in lista_grupos:
        raise HTTPException(400, "Grupo já cadastrado")
    
    lista_grupos.append(num)
    delegados_db[f"{num}-1"] = {"id": f"{num}-1", "grupo": num, "nome": f"GE {num} - Del. 1"}
    delegados_db[f"{num}-2"] = {"id": f"{num}-2", "grupo": num, "nome": f"GE {num} - Del. 2"}
    return {"msg": "Grupo cadastrado"}

@app.delete("/api/grupos/{numero}")
def remover_grupo(numero: str, auth: bool = Depends(verificar_admin)):
    if numero in lista_grupos:
        lista_grupos.remove(numero)
        delegados_db.pop(f"{numero}-1", None)
        delegados_db.pop(f"{numero}-2", None)
        return {"msg": "Grupo removido"}
    raise HTTPException(404, "Grupo não encontrado")

# GESTÃO DE PAUTAS
@app.get("/api/dados-admin")
def get_dados_admin(auth: bool = Depends(verificar_admin)):
    resultado = []
    total_possivel = len(lista_grupos) * 2
    
    for p in reversed(dados["pautas"]):
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

@app.post("/api/pautas")
def criar_pauta(pauta: PautaModel, auth: bool = Depends(verificar_admin)):
    nova_pauta = Pauta(pauta.titulo)
    dados["pautas"].append(nova_pauta)
    return {"msg": "Pauta criada", "id": nova_pauta.id}

@app.post("/api/pautas/{pauta_id}/status")
def mudar_status(pauta_id: str, status: str = Body(..., embed=True), auth: bool = Depends(verificar_admin)):
    for p in dados["pautas"]:
        if p.id == pauta_id:
            if status == "ABERTA":
                for outra in dados["pautas"]:
                    if outra.status == "ABERTA": outra.status = "ENCERRADA"
            p.status = status
            return {"msg": "Status alterado"}
    raise HTTPException(404, "Pauta não encontrada")

# API PÚBLICA (DELEGADOS)
@app.get("/api/pauta-ativa")
def get_pauta_ativa(credencial: Optional[str] = None):
    pauta_ativa = None
    for p in dados["pautas"]:
        if p.status == "ABERTA":
            pauta_ativa = p
            break
    
    if not pauta_ativa and dados["pautas"]:
         ultimo = dados["pautas"][-1]
         if ultimo.status == "ENCERRADA": pauta_ativa = ultimo

    if not pauta_ativa: return {"pauta": None}

    ja_votou = False
    if credencial and credencial in pauta_ativa.votos: ja_votou = True

    contagem = {"favor": 0, "contra": 0, "abstencao": 0}
    for v in pauta_ativa.votos.values(): contagem[v] += 1

    return {
        "pauta": {
            "id": pauta_ativa.id,
            "titulo": pauta_ativa.titulo,
            "status": pauta_ativa.status,
            "total_votos": len(pauta_ativa.votos)
        },
        "ja_votou": ja_votou,
        "resultados": contagem
    }

@app.post("/api/login")
def login(credencial: str):
    delegado = delegados_db.get(credencial)
    if not delegado: 
        raise HTTPException(401, "Credencial inválida! Cadastre o grupo primeiro.")
    return delegado

@app.post("/api/votar")
def votar(voto: VotoModel):
    if voto.credencial not in delegados_db: raise HTTPException(401, "Não autorizado")
    pauta = next((p for p in dados["pautas"] if p.id == voto.pauta_id), None)
    
    if not pauta or pauta.status != "ABERTA": raise HTTPException(400, "Votação fechada")
    if voto.credencial in pauta.votos: raise HTTPException(400, "Já votou!")
        
    pauta.votos[voto.credencial] = voto.opcao
    return {"msg": "Voto computado"}


# --- FRONTEND ADMIN ---
@app.get("/admin", response_class=HTMLResponse)
def serve_admin():
    return """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel Mesa - Admin</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #2c3e50; color: white; padding: 20px; }
        .container { max-width: 1100px; margin: auto; }
        .card { background: white; color: #333; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab-btn { padding: 10px 20px; border: none; background: #34495e; color: #bbb; cursor: pointer; border-radius: 5px 5px 0 0; font-size: 1.1em; font-weight: bold; }
        .tab-btn.active { background: white; color: #2c3e50; border-bottom: 2px solid white; }
        .row { display: flex; justify-content: space-between; align-items: center; }
        input { padding: 10px; width: 60%; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 15px; cursor: pointer; border: none; border-radius: 5px; font-weight: bold; color: white; }
        .btn-add { background: #27ae60; }
        .btn-del { background: #c0392b; width: auto; font-size: 0.8em; padding: 5px 10px;}
        .btn-open { background: #2980b9; }
        .btn-close { background: #c0392b; }
        .badge { padding: 5px 10px; border-radius: 4px; font-size: 0.8em; font-weight: bold; text-transform: uppercase;}
        .aberta { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .encerrada { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .grid-layout { display: grid; grid-template-columns: 1fr 400px; gap: 20px; }
        .chart-container { position: relative; height: 300px; width: 100%; display: flex; justify-content: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #eee; }
        
        /* ESTILOS DE LOGIN */
        .login-box { max-width: 400px; margin: 100px auto; text-align: center; }
        .login-input { width: 90%; margin: 10px 0; padding: 15px; }
        .btn-login { background: #3498db; width: 100%; padding: 15px; font-size: 1.2em; }
    </style>
</head>
<body>
    <div id="app" class="container">
        
        <div v-if="!token" class="card login-box">
            <h1>🔒 Acesso Restrito</h1>
            <p>Mesa Diretora</p>
            <input type="password" v-model="senhaInput" class="login-input" placeholder="Senha do Admin" @keyup.enter="logar">
            <button @click="logar" class="btn-login" style="color:white; font-weight:bold; border-radius:8px; border:none;">ENTRAR</button>
        </div>

        <div v-else>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <div class="tabs" style="margin-bottom:0;">
                    <button class="tab-btn" :class="{active: abaAtual === 'votacao'}" @click="abaAtual = 'votacao'">📊 Votação</button>
                    <button class="tab-btn" :class="{active: abaAtual === 'grupos'}" @click="abaAtual = 'grupos'">📝 Credenciamento</button>
                </div>
                <button @click="logout" style="background: none; color: #e74c3c; text-decoration: underline;">Sair</button>
            </div>

            <div v-show="abaAtual === 'votacao'" class="grid-layout">
                <div>
                    <div class="card">
                        <h3>📜 Nova Pauta</h3>
                        <div class="row">
                            <input v-model="novaPautaTexto" placeholder="Título da pauta...">
                            <button @click="criarPauta" class="btn-add">CRIAR</button>
                        </div>
                    </div>

                    <div v-for="pauta in pautas" :key="pauta.id" class="card">
                        <div class="row">
                            <div>
                                <span :class="['badge', pauta.status.toLowerCase()]">{{ pauta.status }}</span>
                                <h3 style="margin: 5px 0;">{{ pauta.titulo }}</h3>
                            </div>
                            <div>
                                <button v-if="pauta.status !== 'ABERTA'" @click="mudarStatus(pauta.id, 'ABERTA')" class="btn-open">ABRIR</button>
                                <button v-if="pauta.status === 'ABERTA'" @click="mudarStatus(pauta.id, 'ENCERRADA')" class="btn-close">ENCERRAR</button>
                            </div>
                        </div>
                        <div style="margin-top:10px; font-size: 0.9em; color: #666;">
                            Computados: <strong>{{ pauta.total_votos }}</strong> / Possíveis: {{ pauta.esperados }}
                        </div>
                    </div>
                </div>

                <div style="position: sticky; top: 20px; height: fit-content;">
                    <div class="card" style="text-align: center;">
                        <h3>Resultado Parcial</h3>
                        <div v-if="pautaAtiva">
                            <h4>{{ pautaAtiva.titulo }}</h4>
                            <div class="chart-container">
                                <canvas id="graficoVotos"></canvas>
                            </div>
                            <h2>{{ pautaAtiva.total_votos }} Votos</h2>
                        </div>
                        <div v-else>
                            <p style="color: #999; margin-top: 50px;">Nenhuma votação ativa.</p>
                        </div>
                    </div>
                </div>
            </div>

            <div v-show="abaAtual === 'grupos'" class="card">
                <h3>Cadastrar Grupo Escoteiro</h3>
                <div class="row" style="margin-bottom: 20px; background: #f9f9f9; padding: 20px; border-radius: 8px;">
                    <input v-model="novoGrupoInput" placeholder="Numeral do Grupo (Ex: 107)" style="width: 200px;">
                    <button @click="cadastrarGrupo" class="btn-add">CADASTRAR GRUPO</button>
                </div>

                <h3>Grupos Credenciados ({{ grupos.length }})</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Numeral</th>
                            <th>Credenciais Geradas</th>
                            <th>Ação</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="g in grupos" :key="g">
                            <td><strong>GE {{ g }}/PE</strong></td>
                            <td style="color: #2980b9;">{{ g }}-1 &nbsp; | &nbsp; {{ g }}-2</td>
                            <td><button @click="removerGrupo(g)" class="btn-del">REMOVER</button></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const { createApp } = Vue
        let chartInstance = null;

        createApp({
            data() { 
                return { 
                    token: localStorage.getItem('admin_token') || null,
                    senhaInput: '',
                    abaAtual: 'votacao',
                    pautas: [], grupos: [], novaPautaTexto: '', novoGrupoInput: '', pautaAtiva: null 
                } 
            },
            methods: {
                // --- AUTH ---
                async logar() {
                    try {
                        const res = await axios.post('/api/admin/login', { senha: this.senhaInput });
                        this.token = res.data.token;
                        localStorage.setItem('admin_token', this.token);
                        this.configurarAxios();
                        this.fetchDados();
                        this.fetchGrupos();
                    } catch (e) { alert('Senha incorreta!'); }
                },
                logout() {
                    axios.post('/api/admin/logout'); // Tenta avisar o server
                    this.token = null;
                    localStorage.removeItem('admin_token');
                    this.senhaInput = '';
                },
                configurarAxios() {
                    if (this.token) {
                        axios.defaults.headers.common['x-admin-token'] = this.token;
                    }
                },
                
                // --- DADOS ---
                async fetchDados() {
                    if (!this.token) return;
                    try {
                        const res = await axios.get('/api/dados-admin');
                        this.pautas = res.data;
                        if (this.pautas.length > 0) {
                            this.pautaAtiva = this.pautas[0]; 
                            this.updateChart();
                        }
                    } catch (e) { if(e.response.status === 401) this.logout(); }
                },
                async criarPauta() {
                    if(!this.novaPautaTexto) return;
                    await axios.post('/api/pautas', { titulo: this.novaPautaTexto });
                    this.novaPautaTexto = '';
                    this.fetchDados();
                },
                async mudarStatus(id, status) {
                    await axios.post(`/api/pautas/${id}/status`, { status: status });
                    this.fetchDados();
                },
                updateChart() {
                    if (!this.pautaAtiva || this.abaAtual !== 'votacao') return;
                    const ctx = document.getElementById('graficoVotos');
                    if (!ctx) return;

                    const dadosVotos = [
                        this.pautaAtiva.resultados.favor, 
                        this.pautaAtiva.resultados.contra, 
                        this.pautaAtiva.resultados.abstencao
                    ];

                    if (chartInstance) {
                        chartInstance.data.datasets[0].data = dadosVotos;
                        chartInstance.update();
                    } else {
                        chartInstance = new Chart(ctx, {
                            type: 'doughnut',
                            data: {
                                labels: ['A Favor', 'Contra', 'Abstenção'],
                                datasets: [{ data: dadosVotos, backgroundColor: ['#2ecc71', '#e74c3c', '#95a5a6'], borderWidth: 1 }]
                            },
                            options: { responsive: true, maintainAspectRatio: false, animation: { duration: 500 }, plugins: { legend: { position: 'bottom' } } }
                        });
                    }
                },
                // --- GRUPOS ---
                async fetchGrupos() {
                    if (!this.token) return;
                    const res = await axios.get('/api/grupos');
                    this.grupos = res.data;
                },
                async cadastrarGrupo() {
                    if(!this.novoGrupoInput) return;
                    try {
                        await axios.post('/api/grupos', { numero: this.novoGrupoInput });
                        this.novoGrupoInput = '';
                        this.fetchGrupos(); this.fetchDados();
                    } catch (e) { alert(e.response.data.detail); }
                },
                async removerGrupo(num) {
                    if(!confirm('Remover grupo ' + num + '?')) return;
                    await axios.delete('/api/grupos/' + num);
                    this.fetchGrupos(); this.fetchDados();
                }
            },
            mounted() {
                this.configurarAxios();
                if (this.token) {
                    this.fetchDados();
                    this.fetchGrupos();
                }
                setInterval(() => { if(this.token && this.abaAtual === 'votacao') this.fetchDados(); }, 2000);
            }
        }).mount('#app')
    </script>
</body>
</html>
    """

# --- FRONTEND DELEGADO ---
@app.get("/", response_class=HTMLResponse)
def serve_delegado():
    return """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Votação Escoteira</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #eef2f3; margin: 0; padding: 20px; text-align: center; }
        .card { background: white; max-width: 400px; margin: 40px auto; padding: 30px; border-radius: 12px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        .btn { display: block; width: 100%; padding: 18px; margin: 12px 0; border: none; border-radius: 8px; font-size: 1.1em; font-weight: bold; color: white; cursor: pointer; }
        .btn-favor { background-color: #2ecc71; }
        .btn-contra { background-color: #e74c3c; }
        .btn-abs { background-color: #95a5a6; }
        .btn-login { background-color: #3498db; }
        input { padding: 15px; width: 85%; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 1.2em; text-align: center; text-transform: uppercase; }
        .instrucao { font-size: 0.9em; color: #666; margin-bottom: 20px; background: #fff3cd; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <div id="app">
        <div v-if="!user" class="card">
            <h1>⚜️ Entrar</h1>
            <p class="instrucao">Digite sua credencial (Ex: <strong>107-1</strong>)</p>
            <input v-model="credencialInput" placeholder="EX: 107-1" @keyup.enter="login">
            <button @click="login" class="btn btn-login">ACESSAR</button>
        </div>

        <div v-else class="card">
            <h4 style="color: #3498db">{{ user.nome }}</h4>
            <hr style="border: 0; border-top: 1px solid #eee;">

            <div v-if="dados && dados.pauta">
                <p style="text-transform: uppercase; font-size: 0.8em; color: #888;">Em Votação</p>
                <h2 style="margin: 10px 0 20px 0;">{{ dados.pauta.titulo }}</h2>
                
                <div v-if="dados.pauta.status === 'ABERTA'">
                    <div v-if="!dados.ja_votou">
                        <button @click="votar('favor')" class="btn btn-favor">👍 A FAVOR</button>
                        <button @click="votar('contra')" class="btn btn-contra">👎 CONTRA</button>
                        <button @click="votar('abstencao')" class="btn btn-abs">✋ ABSTENÇÃO</button>
                    </div>
                    <div v-else style="background: #e8f8f5; padding: 20px; border-radius: 8px; color: #27ae60;">
                        <h3>✔ Voto Registrado!</h3>
                    </div>
                </div>
                <div v-else-if="dados.pauta.status === 'ENCERRADA'">
                    <h3 style="color: #c0392b">Votação Encerrada</h3>
                </div>
            </div>
            <div v-else>
                <h3>Aguardando mesa...</h3>
                <p style="color:#777">Nenhuma votação ativa.</p>
            </div>
            <button @click="sair" style="background:none; border:none; color: #999; margin-top:20px; cursor: pointer; text-decoration: underline;">Sair / Trocar Delegado</button>
        </div>
    </div>

    <script>
        const { createApp } = Vue
        createApp({
            data() { return { credencialInput: '', user: null, dados: null } },
            methods: {
                async login() {
                    if(!this.credencialInput) return;
                    try {
                        const code = this.credencialInput.trim().toUpperCase();
                        const res = await axios.post('/api/login?credencial=' + code);
                        this.user = res.data;
                        this.startPolling();
                    } catch (e) { alert(e.response.data.detail); }
                },
                async votar(opcao) {
                    if(!confirm('Confirma voto?')) return;
                    try {
                        await axios.post('/api/votar', { credencial: this.user.id, pauta_id: this.dados.pauta.id, opcao: opcao });
                        this.fetchStatus();
                    } catch (e) { alert(e.response.data.detail); }
                },
                async fetchStatus() {
                    if(!this.user) return;
                    const res = await axios.get('/api/pauta-ativa?credencial=' + this.user.id);
                    this.dados = res.data;
                },
                sair() { this.user = null; this.dados = null; },
                startPolling() {
                    this.fetchStatus();
                    setInterval(this.fetchStatus, 2000);
                }
            }
        }).mount('#app')
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)