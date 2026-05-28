# auth.py

import hashlib
import sqlite3

from datetime import datetime

from data_base import DataManager as dm


class Auth:

    # ─────────────────────────────────────────────────────────
    # HASH DE SENHA
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def hash_senha(senha):

        return hashlib.sha256(
            senha.encode()
        ).hexdigest()

    # ─────────────────────────────────────────────────────────
    # REGISTRO
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def registrar_professor(usuario, senha):

        conn = dm.get_conn()

        try:

            conn.execute(
                """
                INSERT INTO usuarios
                (usuario, senha, criado_em)
                VALUES (?, ?, ?)
                """,
                (
                    usuario,
                    Auth.hash_senha(senha),
                    datetime.now().strftime("%d/%m/%Y %H:%M")
                )
            )

            conn.commit()
            conn.close()

            return True, "✅ Cadastro realizado com sucesso!"

        except sqlite3.IntegrityError:

            conn.close()

            return (
                False,
                "❌ Este usuário já existe. Escolha outro nome."
            )

        except Exception as e:

            conn.close()

            return False, f"❌ Erro: {str(e)}"

    # ─────────────────────────────────────────────────────────
    # LOGIN
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def verificar_login(usuario, senha):

        conn = dm.get_conn()

        row = conn.execute(
            """
            SELECT id
            FROM usuarios
            WHERE usuario=? AND senha=?
            """,
            (
                usuario,
                Auth.hash_senha(senha)
            )
        ).fetchone()

        conn.close()

        if row:
            return True, row["id"]

        return False, None