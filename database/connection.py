import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


load_dotenv()


class DataManager:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL nao configurada. Crie um arquivo .env na raiz do projeto "
                "ou configure a variavel de ambiente no servidor."
            )
        self.init_db()

    def get_conn(self):
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def init_db(self):
        schema_path = Path(__file__).resolve().parent / "schema_postgres.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")

        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


dm = DataManager()
