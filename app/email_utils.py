import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")

conf = ConnectionConfig(
    MAIL_USERNAME = MAIL_USERNAME,
    MAIL_PASSWORD = MAIL_PASSWORD,
    MAIL_FROM = MAIL_FROM,
    MAIL_PORT = MAIL_PORT,
    MAIL_SERVER = MAIL_SERVER,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

async def enviar_token_email(destinatario: EmailStr, nome: str, token: str, user_id: str):
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; border: 1px solid #e2e8f0; max-width: 600px; border-radius: 10px; background-color: #ffffff;">
        <div style="text-align: center; border-bottom: 2px solid #002d62; padding-bottom: 10px; margin-bottom: 20px;">
            <h2 style="color: #002d62; margin: 0;">Assembleia Regional</h2>
            <p style="color: #64748b; margin: 5px 0 0 0;">Escoteiros de Pernambuco</p>
        </div>
        
        <p>Olá, <b>{nome}</b>!</p>
        <p>Seu pré-credenciamento foi realizado com sucesso. Abaixo estão seus dados de acesso para a votação.</p>
        
        <div style="background-color: #f8fafc; padding: 20px; text-align: center; margin: 25px 0; border-radius: 10px; border: 1px dashed #002d62;">
            <p style="margin: 0; font-size: 0.85em; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">Seu Código de Acesso (Token)</p>
            <h1 style="margin: 10px 0; color: #002d62; letter-spacing: 5px; font-size: 2.5em;">{token}</h1>
            <p style="margin: 0; font-size: 1em; color: #334155;">ID: <b>{user_id}</b></p>
        </div>
        
        <div style="background-color: #fff1f2; padding: 15px; border-radius: 8px; border-left: 4px solid #e11d48; margin-top: 20px;">
            <p style="color: #9f1239; margin: 0; font-weight: bold;">⚠️ Atenção:</p>
            <p style="color: #be123c; margin: 5px 0 0 0; font-size: 0.9em;">
                Este código é pessoal e intransferível. Ao chegar no local do evento, 
                dirija-se à <b>Mesa de Credenciamento</b> para confirmar sua presença e liberar seu acesso ao sistema de votação.
            </p>
        </div>
        
        <p style="margin-top: 30px; font-size: 0.8em; color: #94a3b8; text-align: center;">
            Mensagem automática do Sistema de Assembleia.
        </p>
    </div>
    """

    message = MessageSchema(
        subject="Seu Código de Votação - Assembleia Regional PE",
        recipients=[destinatario],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)