import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

# --- CONFIGURAÇÃO DO EMAIL ---
# Usa strings vazias como padrão para evitar erros de importação se as variáveis não existirem
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")

# Força a porta 587 (padrão TLS) se não estiver definida no Render
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))

conf = ConnectionConfig(
    MAIL_USERNAME = MAIL_USERNAME,
    MAIL_PASSWORD = MAIL_PASSWORD,
    MAIL_FROM = MAIL_FROM,
    MAIL_PORT = MAIL_PORT,
    MAIL_SERVER = MAIL_SERVER,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    
    USE_CREDENTIALS = True,
    
    VALIDATE_CERTS = False,
    
    TIMEOUT = 60
)

async def enviar_token_email(destinatario: EmailStr, nome: str, token: str, user_id: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e2e8f0; max-width: 600px; background-color: #ffffff;">
        <h2 style="color: #002d62;">Assembleia Regional</h2>
        <p>Olá, <b>{nome}</b>!</p>
        <p>Seu código de acesso para a votação:</p>
        
        <div style="background-color: #f0f9ff; padding: 20px; text-align: center; margin: 20px 0; border: 2px dashed #002d62;">
            <h1 style="margin: 0; color: #002d62; letter-spacing: 5px; font-size: 2.5em;">{token}</h1>
            <p style="margin: 5px 0 0 0;">ID: <b>{user_id}</b></p>
        </div>
        
        <p style="color: #be123c; font-size: 0.9em;">
            ⚠️ Apresente-se ao credenciamento para liberar seu voto.
        </p>
    </div>
    """

    message = MessageSchema(
        subject="Codigo de Votacao - Assembleia PE",
        recipients=[destinatario],
        body=html,
        subtype=MessageType.html
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        print(f"EMAIL SUCESSO: Enviado para {destinatario}")
    except Exception as e:
        print(f"EMAIL ERRO (IGNORADO): Falha ao enviar para {destinatario}. Motivo: {str(e)}")