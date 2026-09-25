from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity


load_dotenv()

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
if not app.config['JWT_SECRET_KEY']:
    raise RuntimeError("JWT_SECRET_KEY não foi definida no .env")

jwt = JWTManager(app)

CAMINHO_BANCO = Path(__file__).parent / 'usuarios.db'

def conectar_banco():
    conexao = sqlite3.connect(str(CAMINHO_BANCO))
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
    conexao.commit()
    conexao.close()

@app.route("/")
def inicio():
    return "Backend funcionando!"

@app.route('/usuarios', methods=['GET'])
def listar_usuarios():

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        usuarios = cursor.execute('''
            SELECT id, nome,email
            FROM usuarios''').fetchall()

        return jsonify([dict(usuario) for usuario in usuarios])

    finally:
        conexao.close()


@app.route('/usuarios', methods=['POST'])
def criar_usuario():
    dados = request.get_json()

    if not dados:
        return jsonify ({
            "erro": "Corpo da requisição não enviado"
        }), 400

    email = dados.get('email')
    senha = dados.get('senha')
    nome = dados.get('nome')

    if not nome or not email or not senha:
        return jsonify({
            "erro":"Campo obrigatório vazio"
        }), 400

    if '@' not in email:
        return jsonify({"erro": "Formato de email inválido"}), 400

    if len(senha) < 6:
        return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres"}), 400

    email = email.strip().lower()
    senha_hash = generate_password_hash(senha)

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            'INSERT INTO usuarios(nome, email, senha) VALUES(?, ?, ?)',
            (nome.strip(), email, senha_hash)
        )
        conexao.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Este e-mail já está cadastrado"}), 409
    finally:
        conexao.close()

    return jsonify({"_id": novo_id, "mensagem": "Usuário criado com sucesso"}), 201


@app.route('/login', methods=['POST'])
def login():
    dados = request.get_json()

    if not dados:
        return jsonify({'erro': 'Nenhum dado recebido'}), 400
    email_recebido = dados.get('email')
    senha_recebida = dados.get('senha')

    if not email_recebido or not senha_recebida:
        return jsonify({"erro": "E-mail e senha são obrigatórios"}), 400

    email_recebido = email_recebido.strip().lower()
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute('''SELECT * FROM usuarios WHERE email = ?''', (email_recebido,))
        usuario = cursor.fetchone()

        if usuario is None:
            return jsonify({"erro": "E-mail ou senha incorretos"}), 401
        elif not check_password_hash(usuario['senha'], senha_recebida):
            return jsonify({"erro": "E-mail ou senha incorretos"}), 401
        else:
            token_acesso = create_access_token(identity=str(usuario['id']))
            return jsonify({
                "status" : "sucesso",
                "mensagem" : f"Bem vindo(a),{usuario['nome']}!",
                "token" : token_acesso,
                "usuario": {
                "id": usuario['id'],
                "nome": usuario['nome'],
                "email": usuario['email']
                }
            }), 200

    finally:
        conexao.close()

@app.route('/perfil', methods=['GET'])
@jwt_required()
def perfil():
    id_usuario = get_jwt_identity()

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute('SELECT id, nome, email FROM usuarios WHERE id = ?', (id_usuario,))
        usuario = cursor.fetchone()
    finally:
        conexao.close()

    if usuario is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    return jsonify({
        "id": usuario['id'],
        "nome": usuario['nome'],
        "email": usuario['email']
    }), 200

@app.route('/usuarios/<int:id_parametro>', methods=['PUT'])
@jwt_required()
def atualizar_usuario(id_parametro):
    id_usuario = get_jwt_identity()

    if str(id_usuario) != str(id_parametro):
        return jsonify({"erro": "Acesso negado. Você só pode alterar sua própria conta."}),403

    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "Nenhum dado fornecido"}), 400
    nome_novo = dados.get('nome')
    senha_nova = dados.get('senha')

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        if nome_novo and senha_nova:
            senha_hash = generate_password_hash(senha_nova)
            cursor.execute('UPDATE usuarios SET nome = ?, senha = ? WHERE id = ?', (nome_novo.strip(), senha_hash, id_parametro))
        elif nome_novo:
            cursor.execute('UPDATE usuarios SET nome = ? WHERE id = ?', (nome_novo.strip(), id_parametro))
        elif senha_nova:
            senha_hash = generate_password_hash(senha_nova)
            cursor.execute('UPDATE usuarios SET senha = ? WHERE id = ?', (senha_hash, id_parametro))
        else:
            return jsonify({"erro": "Envie pelo menos um nome ou uma senha para atualizar os dados"}),400

        if cursor.rowcount == 0:
            return jsonify({"erro": "usuário não encontrado"}), 404

        conexao.commit()
        return jsonify({"mensagem": "Dados atualizados com sucesso!"}), 200
        
    except Exception as e:
        return jsonify({"erro": "Erro ao atualizar no banco de dados"}), 500
    finally:
        conexao.close()


@app.route('/usuarios/<int:id_parametro>', methods=['DELETE'])
@jwt_required()
def deletar_usuario(id_parametro):
    id_usuario = get_jwt_identity()
    if str(id_usuario) != str(id_parametro):
        return jsonify({"erro": "Acesso negado."})

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute('DELETE from usuarios where ID = ?', (id_parametro,))

        if cursor.rowcount == 0:
                    return jsonify({"erro": "usuário não encontrado"}), 404

        conexao.commit()
        return jsonify({"mensagem": "Conta excluída permanentemente."}), 200
    except Exception as e:
        return jsonify({"erro": "Erro ao excluir a conta"}), 500
    finally:
        conexao.close()

    
        





if __name__ == "__main__":
    inicializar_banco()
    app.run(debug=True)
    

