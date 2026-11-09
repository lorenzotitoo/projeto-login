import os
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import timedelta
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

from banco import inicializar_banco
from extensoes import limiter
from rotas_senha import senha_bp
from rotas_usuarios import usuarios_bp

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
limiter.init_app(app)

app.register_blueprint(usuarios_bp)
app.register_blueprint(senha_bp)

@app.after_request
def cabecalhos_de_seguranca(resposta):
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["Cache-Control"] = "no-store"
    return resposta

@app.errorhandler(429)
def limite_excedido(_erro):
    return jsonify({"erro": "Muitas tentativas. Aguarde um pouco e tente novamente."}), 429

@app.route("/")
def inicio():
    return "Backend funcionando!"
     

inicializar_banco()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
    

