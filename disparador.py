import asyncio
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Usuario
from app.database import Base

load_dotenv()

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")

print("--- CONFERÊNCIA DE CREDENCIAIS ---")
if not MAIL_USERNAME:
    print("❌ ERRO: MAIL_USERNAME está vazio no .env")
else:
    print(f"✅ Email carregado: {MAIL_USERNAME}")

if not MAIL_PASSWORD:
    print("❌ ERRO: MAIL_PASSWORD está vazio no .env")
else:

    escondida = MAIL_PASSWORD[:2] + "****" + MAIL_PASSWORD[-2:] if len(MAIL_PASSWORD) > 4 else "****"
    print(f"✅ Senha carregada: {escondida}")

if not DATABASE_URL:
    print("⚠️  AVISO: DATABASE_URL não encontrada. Usando SQLite local.")
    DATABASE_URL = "sqlite:///./sql_app.db"
elif "postgres" in DATABASE_URL:
    print("✅ Banco: PostgreSQL (Render)")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
print("-" * 40)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()
Base.metadata.create_all(bind=engine)

ARQUIVO_MEMORIA = "emails_ja_enviados.txt"

def carregar_enviados():
    if not os.path.exists(ARQUIVO_MEMORIA): return set()
    with open(ARQUIVO_MEMORIA, "r") as f: return set(l.strip() for l in f.readlines())

def salvar_envio(email):
    with open(ARQUIVO_MEMORIA, "a") as f: f.write(f"{email}\n")

def enviar_email_direto(destinatario, nome, token, user_id):
    html = f"""
    <div style="font-family: Arial; padding: 20px; border: 1px solid #ccc;">
        <h2 style="color: #002d62;">Assembleia Regional</h2>
        <p>Olá, <b>{nome}</b>!</p>
        <div style="background: #f0f9ff; padding: 15px; text-align: center; border: 2px dashed #002d62; margin: 20px 0;">
            <h1 style="margin:0; color:#002d62; letter-spacing:3px;">{token}</h1>
            <p>ID: <b>{user_id}</b></p>
        </div>
        <p>Apresente este código no credenciamento.</p>
    </div>
    """
    
    msg = MIMEMultipart()
    msg['From'] = f"Escoteiros PE <{MAIL_USERNAME}>"
    msg['To'] = destinatario
    msg['Subject'] = "Codigo de Votacao - Assembleia PE"
    msg.attach(MIMEText(html, 'html'))

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(MAIL_USERNAME, MAIL_PASSWORD) 
        server.sendmail(MAIL_USERNAME, destinatario, msg.as_string())

async def disparar():
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("⛔ PARANDO: Corrija o arquivo .env antes de continuar.")
        return

    print("\n--- INICIANDO DISPARADOR ---")
    try:
        usuarios = db.query(Usuario).all()
    except Exception as e:
        print(f"❌ Erro ao ler banco: {e}")
        return

    ja_enviados = carregar_enviados()
    print(f"👥 Total no Banco: {len(usuarios)}")
    print(f"📩 Já enviados: {len(ja_enviados)}")
    print("-" * 30)

    contagem = 0

    for user in usuarios:
        if not user.email or "@" not in user.email or "sem_email" in user.email:
            continue

        if user.email in ja_enviados:
            continue

        print(f"🚀 ENVIANDO PARA: {user.nome} ({user.email})...")
        
        try:
            enviar_email_direto(user.email, user.nome, user.token, user.id)
            
            print(f"✅ SUCESSO!")
            salvar_envio(user.email)
            ja_enviados.add(user.email)
            contagem += 1
            
            await asyncio.sleep(2)
            
        except smtplib.SMTPAuthenticationError:
            print("❌ ERRO CRÍTICO: Usuário ou Senha REJEITADOS pelo Google.")
            print("   Verifique se sua SENHA DE APP está correta no .env")
            break 
        except Exception as e:
            print(f"❌ ERRO: {e}")

    print("-" * 30)
    print(f"🏁 Finalizado. Enviados: {contagem}")

if __name__ == "__main__":
    asyncio.run(disparar())