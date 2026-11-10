import os
from contextlib import closing
import psycopg
from psycopg.rows import dict_row
 
 
 
def conectar_banco():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não definida (veja o .env)")
 
    
    return psycopg.connect(
        url,
        row_factory=dict_row,
        prepare_threshold=None,
        connect_timeout=15,
    )
 
 
def inicializar_banco():
    with closing(conectar_banco()) as conexao:
        
        conexao.execute("SELECT pg_advisory_xact_lock(727001)")
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL
            )
        ''')
        conexao.execute('''
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL,
                expira_em TIMESTAMPTZ NOT NULL,
                usado BOOLEAN NOT NULL DEFAULT FALSE
            )
        ''')
        conexao.execute(
            "CREATE INDEX IF NOT EXISTS idx_reset_tokens_hash ON reset_tokens (token_hash)"
        )
        conexao.commit()