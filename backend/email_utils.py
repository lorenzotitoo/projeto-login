import os
import smtplib
import threading
from email.message import EmailMessage
import requests
 
ASSUNTO = "Redefinição de senha"
 
 
def montar_texto(link):
    return (
        f"Para redefinir sua senha, acesse (válido por 30 min):\n\n{link}\n\n"
        "Se não foi você, ignore este e-mail."
    )
 
 
def enviar_via_brevo(destino, link):
    """Envio por API HTTPS (porta 443). Funciona na Render grátis, que bloqueia SMTP."""
    resposta = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "api-key": os.getenv("BREVO_API_KEY"),
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={
            "sender": {
                "name": os.getenv("EMAIL_NOME", "Meu Projeto"),
                "email": os.getenv("EMAIL_REMETENTE"),
            },
            "to": [{"email": destino}],
            "subject": ASSUNTO,
            "textContent": montar_texto(link),
        },
        timeout=15,
    )
    if not resposta.ok:
        raise RuntimeError(f"Brevo respondeu {resposta.status_code}: {resposta.text}")
 
 
def enviar_via_smtp(destino, link):
    """Envio por SMTP (Mailtrap, em desenvolvimento)."""
    msg = EmailMessage()
    msg["Subject"] = ASSUNTO
    msg["From"] = os.getenv("EMAIL_REMETENTE")
    msg["To"] = destino
    msg.set_content(montar_texto(link))
 
    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as servidor:
        servidor.starttls()
        servidor.login(os.getenv("SMTP_USUARIO"), os.getenv("SMTP_SENHA"))
        servidor.send_message(msg)
 
 
def enviar_email(destino, link):
    # com BREVO_API_KEY definida (produção) usa a API; senão usa o SMTP do Mailtrap
    if os.getenv("BREVO_API_KEY"):
        enviar_via_brevo(destino, link)
    else:
        enviar_via_smtp(destino, link)
 
 
def enviar_email_em_segundo_plano(destino, link):
    """Envia sem travar a resposta: o tempo não revela se o e-mail existe."""
    def tarefa():
        try:
            enviar_email(destino, link)
        except Exception as erro:
            print("Falha ao enviar e-mail:", erro)
 
    threading.Thread(target=tarefa, daemon=True).start()