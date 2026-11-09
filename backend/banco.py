import sqlite3
from contextlib import closing
from pathlib import Path
 
CAMINHO_BANCO = Path(__file__).parent / "usuarios.db"
 
 
def conectar_banco():
    conexao = sqlite3.connect(str(CAMINHO_BANCO), timeout=10)
    conexao.row_factory = sqlite3.Row
    return conexao
 
 
def inicializar_banco():
    with closing(conectar_banco()) as conexao:
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL
            )
        ''')
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                expira_em TEXT NOT NULL,
                usado INTEGER DEFAULT 0
            )
        ''')
        conexao.commit()