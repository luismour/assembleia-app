import asyncio
import os
import smtplib
import ssl
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Usuario
from app.database import Base

# ==============================================================================
# 1. CARREGAMENTO ROBUSTO DO ARQUIVO .ENV
# ==============================================================================
pasta_do_script = Path(__file__).parent.resolve()
caminho_env = pasta_do_script / ".env"

print("-" * 50)
print(f"📂 PASTA DO SCRIPT: {pasta_do_script}")
print(f"🔍 PROCURANDO .ENV EM: {caminho_env}")

if not caminho_env.exists():
    print("\n❌ ERRO CRÍTICO: Arquivo .env NÃO encontrado!")
else:
    load_dotenv(dotenv_path=caminho_env)
    print("✅ ARQUIVO .ENV CARREGADO COM SUCESSO!")
print("-" * 50)

# ==============================================================================
# 2. CONFIGURAÇÕES E BANCO DE DADOS
# ==============================================================================
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("⚠️  AVISO: DATABASE_URL vazia. Usando SQLite temporário.")
    DATABASE_URL = "sqlite:///./sql_app.db"
elif "postgres" in DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()
Base.metadata.create_all(bind=engine)

ARQUIVO_MEMORIA = pasta_do_script / "emails_ja_enviados.txt"

def carregar_enviados():
    if not ARQUIVO_MEMORIA.exists(): return set()
    with open(ARQUIVO_MEMORIA, "r") as f: return set(l.strip() for l in f.readlines())

def salvar_envio(email):
    with open(ARQUIVO_MEMORIA, "a") as f: f.write(f"{email}\n")

# ==============================================================================
# 3. TEMPLATE DE E-MAIL (SEMINÁRIO REGIONAL 2026)
# ==============================================================================
def enviar_email_direto(destinatario, nome, token, user_id, grupo):
    # Cores: Azul Escoteiro (#002d62) e Fundo Cinza (#f3f4f6)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-top: 20px; margin-bottom: 20px; }}
            .header {{ background-color: #002d62; padding: 30px 20px; text-align: center; color: white; }}
            .header h1 {{ margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px; }}
            .subtitle {{ margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; font-weight: 300; }}
            
            .content {{ padding: 40px 30px; text-align: center; color: #333; }}
            .welcome-text {{ font-size: 18px; margin-bottom: 15px; }}
            
            /* Box de Informações do Evento */
            .event-info {{ background-color: #eef2f6; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: left; font-size: 14px; border-left: 4px solid #002d62; }}
            .event-row {{ margin-bottom: 8px; display: flex; align-items: flex-start; gap: 10px; }}
            .icon {{ min-width: 20px; text-align: center; }}
            
            /* Token Box */
            .token-box {{ background-color: #f0fdf4; border: 2px dashed #10b981; border-radius: 12px; padding: 25px; margin: 30px 0; }}
            .token-label {{ display: block; font-size: 12px; text-transform: uppercase; color: #15803d; font-weight: bold; letter-spacing: 1px; margin-bottom: 5px; }}
            .token-value {{ font-size: 32px; font-weight: 800; color: #002d62; letter-spacing: 3px; display: block; margin: 5px 0; }}
            
            .info-row {{ display: flex; justify-content: center; gap: 15px; margin-top: 15px; font-size: 13px; color: #555; }}
            .info-item {{ background: #ffffff; padding: 4px 12px; border-radius: 15px; font-weight: 600; border: 1px solid #e5e7eb; }}
            
            .footer {{ background-color: #eef2f6; padding: 20px; text-align: center; font-size: 12px; color: #888; border-top: 1px solid #e5e7eb; }}
            .btn {{ display: inline-block; background-color: #002d62; color: white; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: bold; margin-top: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .btn:hover {{ background-color: #1e3a8a; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Seminário Regional 2026</h1>
                <p class="subtitle">ESCOTEIROS DE PERNAMBUCO</p>
            </div>
            
            <div class="content">
                <p class="welcome-text">Olá, <strong>{nome}</strong>!</p>
                <p style="color: #666; font-size: 15px; line-height: 1.5;">Seu credenciamento para o evento foi confirmado. Confira abaixo os detalhes e sua credencial de acesso.</p>
                
                <div class="event-info">
                    <div class="event-row">
                        <span class="icon">📅</span>
                        <span><strong>Data:</strong> 14 de março de 2026 (Sábado)</span>
                    </div>
                    <div class="event-row">
                        <span class="icon">⏰</span>
                        <span><strong>Horário:</strong> Início às 08h00</span>
                    </div>
                    <div class="event-row">
                        <span class="icon">📍</span>
                        <span><strong>Local:</strong> UNIFG – Centro Universitário dos Guararapes (Campus Piedade)<br>
                        <span style="font-size: 12px; color: #666;">Rua Comendador José Didier, nº 27 – Piedade, Jaboatão dos Guararapes – PE</span></span>
                    </div>
                </div>
                
                <div class="token-box">
                    <span class="token-label">Sua Credencial de Votação</span>
                    <span class="token-value">{token}</span>
                    
                    <div class="info-row">
                        <span class="info-item">🆔 ID: {user_id}</span>
                        <span class="info-item">⚜️ GE: {grupo}</span>
                    </div>
                </div>

                <p style="font-size: 13px; color: #888; margin-top: 20px;">Apresente este código na <strong>Mesa de Credenciamento</strong> para realizar seu check-in.</p>

                <a href="https://assembleia-app.onrender.com" class="btn">Acessar Painel do Evento</a>
            </div>

            <div class="footer">
                <p>Escoteiros de Pernambuco - Região PE<br>
                Mensagem automática do Sistema de Eventos.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['From'] = f"Escoteiros PE <{MAIL_USERNAME}>"
    msg['To'] = destinatario
    msg['Subject'] = "🎟️ Credencial - Assembleia Ordinária Regional 2026"
    msg.attach(MIMEText(html, 'html'))

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(MAIL_USERNAME, MAIL_PASSWORD) 
        server.sendmail(MAIL_USERNAME, destinatario, msg.as_string())

# ==============================================================================
# 4. LOOP DE DISPARO
# ==============================================================================
async def disparar():
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("\n⛔ PAUSANDO: As credenciais de e-mail não foram carregadas do .env")
        return

    print("\n--- INICIANDO DISPARADOR (Seminário 2026) ---")
    try:
        usuarios = db.query(Usuario).all()
    except Exception as e:
        print(f"❌ Erro ao conectar no Banco de Dados: {e}")
        return

    ja_enviados = carregar_enviados()
    print(f"👥 Total no Banco: {len(usuarios)}")
    print(f"📩 Já enviados: {len(ja_enviados)}")
    print("-" * 40)

    contagem = 0

    for user in usuarios:
        if not user.email or "@" not in user.email or "sem_email" in user.email:
            continue
        if user.email in ja_enviados:
            continue

        print(f"🚀 ENVIANDO PARA: {user.nome} ({user.email})...")
        
        try:
            grupo_txt = getattr(user, 'grupo', 'ND')
            enviar_email_direto(user.email, user.nome, user.token, user.id, grupo_txt)
            
            print(f"✅ SUCESSO!")
            salvar_envio(user.email)
            ja_enviados.add(user.email)
            contagem += 1
            
            await asyncio.sleep(2) 
            
        except smtplib.SMTPAuthenticationError:
            print("❌ ERRO CRÍTICO: Login ou Senha do Gmail incorretos.")
            break 
        except Exception as e:
            print(f"❌ ERRO: {e}")

    print("-" * 40)
    print(f"🏁 Finalizado. Novos e-mails enviados: {contagem}")

if __name__ == "__main__":
    asyncio.run(disparar())