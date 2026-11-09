from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import smtplib
from email.message import EmailMessage
import threading


load_dotenv()

app = Flask(__name__)

ORIGENS_PERMITIDAS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")
    if o.strip()
]
CORS(app, resources={r"/*": {"origins": ORIGENS_PERMITIDAS}})

chave_jwt = os.getenv("JWT_SECRET_KEY")
if not chave_jwt or len(chave_jwt) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY ausente ou curta demais (mínimo 32 caracteres). "
        "Gere uma com: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.config["JWT_SECRET_KEY"] = chave_jwt

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=int(os.getenv("JWT_EXPIRA_MINUTOS", "30")))

jwt = JWTManager(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["300 per hour"],
    storage_uri="memory://",
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500").rstrip("/")

CAMINHO_BANCO = Path(__file__).parent / 'usuarios.db'

HASH_FALSO = generate_password_hash("senha-falsa-para-igualar-o-tempo")

REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def conectar_banco():
    conexao = sqlite3.connect(str(CAMINHO_BANCO), timeout=10)
    conexao.row_factory = sqlite3.Row
    return conexao

def inicializar_banco():
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL,
        expira_em TEXT NOT NULL,
        usado INTEGER DEFAULT 0
        )
    ''')
    conexao.commit()
    conexao.close()

def ler_json():
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}
 
 
def so_texto(valor):
    return valor if isinstance(valor, str) else ""
 
 
def email_valido(email):
    return len(email) <= 254 and bool(REGEX_EMAIL.match(email))
 
 
def nome_valido(nome):
    return 3 <= len(nome) <= 30
 
 
def senha_valida(senha):
    return 6 <= len(senha) <= 128

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def enviar_email(destino, link):
    msg = EmailMessage()
    msg["Subject"] = "Redefinição de senha"
    msg["From"] = os.getenv("EMAIL_REMETENTE")
    msg["To"] = destino
    msg.set_content(f"Para redefinir sua senha, acesse (válido por 30 min):\n\n{link}\n\nSe não foi você, ignore este e-mail.")

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

@app.errorhandler(429)
def limite_excedido(_erro):
    return jsonify({"erro": "Muitas tentativas. Aguarde um pouco e tente novamente."}), 429

@app.route("/")
def inicio():
    return "Backend funcionando!"


@app.route('/usuarios', methods=['POST'])
@limiter.limit("10 per hour")
def criar_usuario():
    dados = ler_json()

    if not dados:
        return jsonify ({
            "erro": "Corpo da requisição não enviado"
        }), 400
    
    nome = so_texto(dados.get("nome")).strip()
    email = so_texto(dados.get("email")).strip().lower()
    senha = so_texto(dados.get("senha"))
 
    if not nome or not email or not senha:
        return jsonify({"erro": "Campo obrigatório vazio"}), 400
 
    if not email_valido(email):
        return jsonify({"erro": "Formato de email inválido"}), 400
 
    if not nome_valido(nome):
        return jsonify({"erro": "O nome deve ter entre 3 e 30 caracteres"}), 400
 
    if not senha_valida(senha):
        return jsonify({"erro": "A senha deve ter entre 6 e 128 caracteres"}), 400
    
    senha_hash = generate_password_hash(senha)
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "INSERT INTO usuarios(nome, email, senha) VALUES(?, ?, ?)",
            (nome, email, senha_hash),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Este e-mail já está cadastrado"}), 409
    finally:
        conexao.close()
 
    return jsonify({"_id": novo_id, "mensagem": "Usuário criado com sucesso"}), 201


@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    dados = ler_json()
    if not dados:
            return jsonify ({
                "erro": "Corpo da requisição não enviado"
            }), 400
    
    email = so_texto(dados.get("email")).strip().lower()
    senha = so_texto(dados.get("senha"))
 
    if not email or not senha:
        return jsonify({"erro": "E-mail e senha são obrigatórios"}), 400
 
    conexao = conectar_banco()
    try:
        usuario = conexao.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    finally:
        conexao.close()
 
    if usuario is None:
        check_password_hash(HASH_FALSO, senha)  # gasta o mesmo tempo
        return jsonify({"erro": "E-mail ou senha incorretos"}), 401
 
    if not check_password_hash(usuario["senha"], senha):
        return jsonify({"erro": "E-mail ou senha incorretos"}), 401
 
    token_acesso = create_access_token(identity=str(usuario["id"]))
    return jsonify({
        "status": "sucesso",
        "mensagem": f"Bem vindo(a), {usuario['nome']}!",
        "token": token_acesso,
        "usuario": {
            "id": usuario["id"],
            "nome": usuario["nome"],
            "email": usuario["email"],
        },
    }), 200

@app.route('/perfil', methods=['GET'])
@jwt_required()
def perfil():
    id_usuario = get_jwt_identity()
    conexao = conectar_banco()
    try:
        usuario = conexao.execute(
            "SELECT id, nome, email FROM usuarios WHERE id = ?", (id_usuario,)
        ).fetchone()
    finally:
        conexao.close()
 
    if usuario is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404
 
    return jsonify({
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
    }), 200

@app.route("/usuarios/<int:id_parametro>", methods=["PUT"])
@jwt_required()
def atualizar_usuario(id_parametro):
    if str(get_jwt_identity()) != str(id_parametro):
        return jsonify({"erro": "Acesso negado. Você só pode alterar sua própria conta."}), 403
 
    dados = ler_json()
    nome_novo = so_texto(dados.get("nome")).strip()
    senha_nova = so_texto(dados.get("senha"))
 
    if not nome_novo and not senha_nova:
        return jsonify({"erro": "Envie pelo menos um nome ou uma senha para atualizar os dados"}), 400
 
    if nome_novo and not nome_valido(nome_novo):
        return jsonify({"erro": "O nome deve ter entre 3 e 30 caracteres"}), 400
 
    if senha_nova and not senha_valida(senha_nova):
        return jsonify({"erro": "A senha deve ter entre 6 e 128 caracteres"}), 400
 
    campos = []
    valores = []
    if nome_novo:
        campos.append("nome = ?")
        valores.append(nome_novo)
    if senha_nova:
        campos.append("senha = ?")
        valores.append(generate_password_hash(senha_nova))
 
    conexao = conectar_banco()
    try:
        # os nomes das colunas vêm só do código acima, nunca do usuário
        cursor = conexao.execute(
            f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?",
            (*valores, id_parametro),
        )
        if cursor.rowcount == 0:
            return jsonify({"erro": "Usuário não encontrado"}), 404
 
        conexao.commit()
        return jsonify({"mensagem": "Dados atualizados com sucesso!"}), 200
    except Exception:
        return jsonify({"erro": "Erro ao atualizar no banco de dados"}), 500
    finally:
        conexao.close()


@app.route("/usuarios/<int:id_parametro>", methods=["DELETE"])
@jwt_required()
def deletar_usuario(id_parametro):
    if str(get_jwt_identity()) != str(id_parametro):
        return jsonify({"erro": "Acesso negado."}), 403
 
    conexao = conectar_banco()
    try:
        # apaga também os tokens de redefinição do usuário
        conexao.execute("DELETE FROM reset_tokens WHERE usuario_id = ?", (id_parametro,))
        cursor = conexao.execute("DELETE FROM usuarios WHERE id = ?", (id_parametro,))
 
        if cursor.rowcount == 0:
            return jsonify({"erro": "Usuário não encontrado"}), 404
 
        conexao.commit()
        return jsonify({"mensagem": "Conta excluída permanentemente."}), 200
    except Exception:
        return jsonify({"erro": "Erro ao excluir a conta"}), 500
    finally:
        conexao.close()

@app.route("/esqueci-senha", methods=["POST"])
@limiter.limit("3 per minute; 10 per hour")
def esqueci_senha():
    dados = ler_json()
    email = so_texto(dados.get("email")).strip().lower()
 
    if not email:
        return jsonify({"erro": "Informe o e-mail"}), 400
 
    agora = datetime.now(timezone.utc)
    link = None
 
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
 
        # limpeza: tokens já expirados não servem para nada
        cursor.execute("DELETE FROM reset_tokens WHERE expira_em < ?", (agora.isoformat(),))
 
        usuario = cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()
 
        if usuario:
            # invalida pedidos anteriores desse usuário
            cursor.execute(
                "UPDATE reset_tokens SET usado = 1 WHERE usuario_id = ? AND usado = 0",
                (usuario["id"],),
            )
 
            token = secrets.token_urlsafe(32)
            expira_em = (agora + timedelta(minutes=30)).isoformat()
            cursor.execute(
                "INSERT INTO reset_tokens (usuario_id, token_hash, expira_em) VALUES (?, ?, ?)",
                (usuario["id"], hash_token(token), expira_em),
            )
            link = f"{FRONTEND_URL}/frontredefinir/redefinir.html?token={token}"
 
        conexao.commit()
    finally:
        conexao.close()
 
    if link:
        enviar_email_em_segundo_plano(email, link)
 
    # mesma resposta existindo o e-mail ou não
    return jsonify({"mensagem": "Se esse e-mail estiver cadastrado, enviaremos as instruções."}), 200

@app.route("/redefinir-senha", methods=["POST"])
@limiter.limit("10 per hour")
def redefinir_senha():
    dados = ler_json()
    token = so_texto(dados.get("token"))
    senha_nova = so_texto(dados.get("senha"))
 
    if not token or not senha_nova:
        return jsonify({"erro": "Dados incompletos"}), 400
 
    if not senha_valida(senha_nova):
        return jsonify({"erro": "A senha deve ter entre 6 e 128 caracteres"}), 400
 
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        registro = cursor.execute(
            "SELECT id, usuario_id, expira_em FROM reset_tokens WHERE token_hash = ? AND usado = 0",
            (hash_token(token),),
        ).fetchone()
 
        if registro is None or datetime.fromisoformat(registro["expira_em"]) < datetime.now(timezone.utc):
            return jsonify({"erro": "Link inválido ou expirado"}), 400
 
        # marca como usado de forma atômica: dois cliques simultâneos não passam os dois
        marcado = cursor.execute(
            "UPDATE reset_tokens SET usado = 1 WHERE id = ? AND usado = 0", (registro["id"],)
        )
        if marcado.rowcount == 0:
            return jsonify({"erro": "Link inválido ou expirado"}), 400
 
        cursor.execute(
            "UPDATE usuarios SET senha = ? WHERE id = ?",
            (generate_password_hash(senha_nova), registro["usuario_id"]),
        )
        conexao.commit()
 
        return jsonify({"mensagem": "Senha redefinida com sucesso!"}), 200
    finally:
        conexao.close()
        

inicializar_banco()

if __name__ == "__main__":
    # debug só liga se FLASK_DEBUG=1 no .env (nunca em produção)
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
    

