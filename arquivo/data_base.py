import sqlite3
from datetime import datetime


class DataManager:

    def __init__(self, db_name="provas.db"):
        self.db_name = db_name
        self.init_db()

    # ── Conexão ─────────────────────────────────────────────
    def get_conn(self):
        conn = sqlite3.connect(
            self.db_name,
            check_same_thread=False
        )

        conn.row_factory = sqlite3.Row

        return conn

    # ── Inicialização do banco ─────────────────────────────
    def init_db(self):

        conn = self.get_conn()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prova_id TEXT,
                nome_aluno TEXT,
                evento TEXT,
                detalhe TEXT,
                timestamp TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE,
                senha TEXT,
                criado_em TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS provas (
                id TEXT PRIMARY KEY,
                usuario_id INTEGER,
                materia TEXT,
                titulo TEXT,
                questoes TEXT,
                criada_em TEXT,
                FOREIGN KEY(usuario_id)
                    REFERENCES usuarios(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS respostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prova_id TEXT,
                nome_aluno TEXT,
                respostas TEXT,
                nota REAL,
                respondida_em TEXT,
                tentativas_screenshot INTEGER DEFAULT 0,
                alertas_fraude TEXT,
                FOREIGN KEY(prova_id)
                    REFERENCES provas(id)
            )
        """)

        conn.commit()

        # ── Migrações ─────────────────────────────
        try:

            cur = conn.execute("PRAGMA table_info(provas)")

            cols = [r[1] for r in cur.fetchall()]

            if "usuario_id" not in cols:

                conn.execute("""
                    ALTER TABLE provas
                    ADD COLUMN usuario_id INTEGER DEFAULT 1
                """)

                conn.commit()

        except Exception:
            pass

        try:

            cur = conn.execute("PRAGMA table_info(respostas)")

            cols = [r[1] for r in cur.fetchall()]

            if "tentativas_screenshot" not in cols:

                conn.execute("""
                    ALTER TABLE respostas
                    ADD COLUMN tentativas_screenshot
                    INTEGER DEFAULT 0
                """)

                conn.commit()

            if "alertas_fraude" not in cols:

                conn.execute("""
                    ALTER TABLE respostas
                    ADD COLUMN alertas_fraude TEXT
                """)

                conn.commit()

        except Exception:
            pass

        conn.close()