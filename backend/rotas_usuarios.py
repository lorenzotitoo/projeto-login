import sqlite3
from contextlib import closing
 
from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
 
from banco import conectar_banco
from extensoes import limiter
from utils import ler_json, so_texto, email_valido, nome_valido, senha_valida
 
usuarios_bp = Blueprint("usuarios", __name__)
 
# Hash falso: o login leva o mesmo tempo com e-mail inexistente
HASH_FALSO = generate_password_hash("senha-falsa-para-igualar-o-tempo")
 
 
@usuarios_bp.route("/usuarios", methods=["POST"])
@limiter.limit("10 per hour")
def criar_usuario():
    dados = ler_json()
    if not dados:
        return jsonify({"erro": "Corpo da requisição não enviado"}), 400
 
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
 
    with closing(conectar_banco()) as conexao:
        try:
            cursor = conexao.execute(
                "INSERT INTO usuarios(nome, email, senha) VALUES(?, ?, ?)",
                (nome, email, senha_hash),
            )
            conexao.commit()
            novo_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return jsonify({"erro": "Este e-mail já está cadastrado"}), 409
 
    return jsonify({"_id": novo_id, "mensagem": "Usuário criado com sucesso"}), 201
 
 
@usuarios_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    dados = ler_json()
    if not dados:
        return jsonify({"erro": "Nenhum dado recebido"}), 400
 
    email = so_texto(dados.get("email")).strip().lower()
    senha = so_texto(dados.get("senha"))
 
    if not email or not senha:
        return jsonify({"erro": "E-mail e senha são obrigatórios"}), 400
 
    with closing(conectar_banco()) as conexao:
        usuario = conexao.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
 
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
 
 
@usuarios_bp.route("/perfil", methods=["GET"])
@jwt_required()
def perfil():
    id_usuario = get_jwt_identity()
 
    with closing(conectar_banco()) as conexao:
        usuario = conexao.execute(
            "SELECT id, nome, email FROM usuarios WHERE id = ?", (id_usuario,)
        ).fetchone()
 
    if usuario is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404
 
    return jsonify({
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
    }), 200
 
 
@usuarios_bp.route("/usuarios/<int:id_parametro>", methods=["PUT"])
@jwt_required()
def atualizar_usuario(id_parametro):
    if str(get_jwt_identity()) != str(id_parametro):
        return jsonify({"erro": "Acesso negado. Você só pode alterar sua própria conta."}), 403
 
    dados = ler_json()
    if not dados:
        return jsonify({"erro": "Nenhum dado fornecido"}), 400
 
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
 
    with closing(conectar_banco()) as conexao:
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
 
 
@usuarios_bp.route("/usuarios/<int:id_parametro>", methods=["DELETE"])
@jwt_required()
def deletar_usuario(id_parametro):
    if str(get_jwt_identity()) != str(id_parametro):
        return jsonify({"erro": "Acesso negado."}), 403
 
    with closing(conectar_banco()) as conexao:
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