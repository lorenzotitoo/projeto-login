from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)



def conectar_banco():
    conexao = sqlite3.connect("usuarios.db")
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
            return jsonify({
                "status" : "sucesso",
                "mensagem" : f"Bem vindo(a),{usuario['nome']}!",
                "usuario": {
                "id": usuario['id'],
                "nome": usuario['nome'],
                "email": usuario['email']
                }
            }), 200

    finally:
        conexao.close()


if __name__ == "__main__":
    inicializar_banco()
    app.run(debug=True)
    

