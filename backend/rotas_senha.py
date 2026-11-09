import hashlib
import os
import secrets
from contextlib import closing
from datetime import datetime, timedelta, timezone
 
from flask import Blueprint, jsonify
from werkzeug.security import generate_password_hash
 
from banco import conectar_banco
from email_utils import enviar_email_em_segundo_plano
from extensoes import limiter
from utils import ler_json, so_texto, senha_valida
 
senha_bp = Blueprint("senha", __name__)
 
 
def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()
 
 
@senha_bp.route("/esqueci-senha", methods=["POST"])
@limiter.limit("3 per minute; 10 per hour")
def esqueci_senha():
    dados = ler_json()
    email = so_texto(dados.get("email")).strip().lower()
 
    if not email:
        return jsonify({"erro": "Informe o e-mail"}), 400
 
    agora = datetime.now(timezone.utc)
    frontend = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500").rstrip("/")
    link = None
 
    with closing(conectar_banco()) as conexao:
        # limpeza: tokens já expirados não servem para nada
        conexao.execute("DELETE FROM reset_tokens WHERE expira_em < ?", (agora.isoformat(),))
 
        usuario = conexao.execute(
            "SELECT id FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
 
        if usuario:
            # invalida pedidos anteriores desse usuário
            conexao.execute(
                "UPDATE reset_tokens SET usado = 1 WHERE usuario_id = ? AND usado = 0",
                (usuario["id"],),
            )
 
            token = secrets.token_urlsafe(32)
            expira_em = (agora + timedelta(minutes=30)).isoformat()
            conexao.execute(
                "INSERT INTO reset_tokens (usuario_id, token_hash, expira_em) VALUES (?, ?, ?)",
                (usuario["id"], hash_token(token), expira_em),
            )
            link = f"{frontend}/frontredefinir/redefinir.html?token={token}"
 
        conexao.commit()
 
    if link:
        enviar_email_em_segundo_plano(email, link)
 
    # mesma resposta existindo o e-mail ou não
    return jsonify({"mensagem": "Se esse e-mail estiver cadastrado, enviaremos as instruções."}), 200
 
 
@senha_bp.route("/redefinir-senha", methods=["POST"])
@limiter.limit("10 per hour")
def redefinir_senha():
    dados = ler_json()
    token = so_texto(dados.get("token"))
    senha_nova = so_texto(dados.get("senha"))
 
    if not token or not senha_nova:
        return jsonify({"erro": "Dados incompletos"}), 400
 
    if not senha_valida(senha_nova):
        return jsonify({"erro": "A senha deve ter entre 6 e 128 caracteres"}), 400
 
    with closing(conectar_banco()) as conexao:
        registro = conexao.execute(
            "SELECT id, usuario_id, expira_em FROM reset_tokens WHERE token_hash = ? AND usado = 0",
            (hash_token(token),),
        ).fetchone()
 
        if registro is None or datetime.fromisoformat(registro["expira_em"]) < datetime.now(timezone.utc):
            return jsonify({"erro": "Link inválido ou expirado"}), 400
 
        # marca como usado de forma atômica: dois cliques simultâneos não passam os dois
        marcado = conexao.execute(
            "UPDATE reset_tokens SET usado = 1 WHERE id = ? AND usado = 0", (registro["id"],)
        )
        if marcado.rowcount == 0:
            return jsonify({"erro": "Link inválido ou expirado"}), 400
 
        conexao.execute(
            "UPDATE usuarios SET senha = ? WHERE id = ?",
            (generate_password_hash(senha_nova), registro["usuario_id"]),
        )
        conexao.commit()
 
    return jsonify({"mensagem": "Senha redefinida com sucesso!"}), 200