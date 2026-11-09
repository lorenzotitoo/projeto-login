import re
 
from flask import request
 
REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
 
 
def ler_json():
    """Lê o corpo JSON sem derrubar a rota se vier algo inválido."""
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}
 
 
def so_texto(valor):
    """Garante string: números, listas e null viram texto vazio."""
    return valor if isinstance(valor, str) else ""
 
 
def email_valido(email):
    return len(email) <= 254 and bool(REGEX_EMAIL.match(email))
 
 
def nome_valido(nome):
    return 3 <= len(nome) <= 30
 
 
def senha_valida(senha):
    return 6 <= len(senha) <= 128