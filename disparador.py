import requests
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ================= CONFIGURAÇÕES =================
# URL do seu site no Render (SEM A BARRA NO FINAL)
SITE_URL = "https://assembleia-app.onrender.com"

# Suas credenciais de ADMIN do site
ADMIN_USER = "admin"
ADMIN_PASS = "nrpesaps"

# Suas credenciais do GMAIL (Para enviar)
GMAIL_USER = "luis.moura@escoteiros.org.br"     
GMAIL_PASS = "makb mfwe tuel auqq"   
# =================================================

def pegar_lista_usuarios(token):
    print("📥 Baixando lista de usuários...")
    headers = {"x-admin-token": token}
    try:
        response = requests.get(f"{SITE_URL}/api/admin/lista-para-email", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro ao baixar lista: {response.text}")
            return []
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return []

def enviar_email(destinatario, nome, token_acesso, id_usuario):
    # HTML do E-mail
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e2e8f0; max-width: 600px;">
        <h2 style="color: #002d62;">Assembleia Regional - Token Oficial</h2>
        <p>Olá, <b>{nome}</b>!</p>
        <p>Segue abaixo seu token definitivo para a votação:</p>
        
        <div style="background-color: #f0f9ff; padding: 20px; text-align: center; margin: 20px 0; border: 2px dashed #002d62;">
            <h1 style="margin: 0; color: #002d62; letter-spacing: 5px; font-size: 2.5em;">{token_acesso}</h1>
            <p style="margin: 5px 0 0 0;">ID: <b>{id_usuario}</b></p>
        </div>
        
        <p style="color: #be123c; font-size: 0.9em;">
            ⚠️ Apresente este código na mesa de credenciamento.
        </p>
    </div>
    """

    msg = MIMEMultipart()
    msg['From'] = f"Escoteiros PE <{GMAIL_USER}>"
    msg['To'] = destinatario
    msg['Subject'] = "Seu Token de Votação - Assembleia PE"
    msg.attach(MIMEText(html, 'html'))

    # Contexto SSL (Mais seguro rodando local)
    context = ssl.create_default_context()

    try:
        # Tenta porta 465 (SSL) primeiro, que é melhor para PC local
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar para {destinatario}: {e}")
        return False

def main():
    print("=== DISPARADOR DE EMAILS - ASSEMBLEIA ===")
    
    # 1. Login no Site
    print("🔑 Autenticando no painel admin...")
    try:
        resp = requests.post(f"{SITE_URL}/api/admin/login", json={"usuario": ADMIN_USER, "senha": ADMIN_PASS})
        if resp.status_code != 200:
            print("❌ Falha no login! Verifique senha do admin.")
            return
        token_site = resp.json()["token"]
    except Exception as e:
        print(f"❌ Erro ao conectar no site: {e}")
        return

    # 2. Pega Lista
    lista = pegar_lista_usuarios(token_site)
    total = len(lista)
    print(f"📋 Encontrados {total} usuários com e-mail cadastrado.")
    
    if total == 0:
        return

    confirmacao = input("Deseja iniciar o envio em massa? (s/n): ")
    if confirmacao.lower() != 's':
        return

    # 3. Loop de Envio
    sucessos = 0
    erros = 0

    print("\n🚀 Iniciando disparos...")
    
    for i, usuario in enumerate(lista, 1):
        email = usuario['email']
        nome = usuario['nome']
        token = usuario['token']
        uid = usuario['id']

        if "@" not in email:
            print(f"⚠️ [{i}/{total}] Email inválido ignorado: {email}")
            continue

        print(f"📨 [{i}/{total}] Enviando para {nome} ({email})... ", end="")
        
        # Envia
        ok = enviar_email(email, nome, token, uid)
        
        if ok:
            print("✅ OK!")
            sucessos += 1
        else:
            erros += 1

        # Pausa de segurança para o Gmail não bloquear (1 segundo)
        time.sleep(1)

    print("\n" + "="*30)
    print(f"RELATÓRIO FINAL:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Erros: {erros}")
    print("="*30)

if __name__ == "__main__":
    main()