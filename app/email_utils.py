import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import EmailStr

MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))

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
            ⚠️ Apresente-se à mesa para liberar seu voto.
        </p>
    </div>
    """

    msg = MIMEMultipart()
    msg['From'] = f"Escoteiros PE <{MAIL_USERNAME}>"
    msg['To'] = destinatario
    msg['Subject'] = "Codigo de Votacao - Assembleia PE"
    msg.attach(MIMEText(html, 'html'))

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=30) as server:
            server.ehlo()
            
            server.starttls(context=context)
            
            server.ehlo()
            
            # Login
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            
            # Envia
            server.sendmail(MAIL_USERNAME, destinatario, msg.as_string())
            
        print(f"EMAIL SUCESSO: Enviado para {destinatario}")

    except Exception as e:
        print(f"EMAIL ERRO (IGNORADO): Falha ao enviar para {destinatario}. Erro: {e}")