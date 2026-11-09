import os
import smtplib
import threading
from email.message import EmailMessage
 
 
def enviar_email(destino, link):
    msg = EmailMessage()
    msg["Subject"] = "Redefinição de senha"
    msg["From"] = os.getenv("EMAIL_REMETENTE")
    msg["To"] = destino
    msg.set_content(
        f"Para redefinir sua senha, acesse (válido por 30 min):\n\n{link}\n\n"
        "Se não foi você, ignore este e-mail."
    )
 
    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as servidor:
        servidor.starttls()
        servidor.login(os.getenv("SMTP_USUARIO"), os.getenv("SMTP_SENHA"))
        servidor.send_message(msg)
 
 
def enviar_email_em_segundo_plano(destino, link):
    """Envia sem travar a resposta: o tempo não revela se o e-mail existe."""
    def tarefa():
        try:
            enviar_email(destino, link)
        except Exception as erro:
            print("Falha ao enviar e-mail:", erro)
 
    threading.Thread(target=tarefa, daemon=True).start()