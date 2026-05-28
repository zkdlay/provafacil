"""
# data_base.py + provas.py + parte do auth.py (acesso ao banco)
"""

import json
from datetime import datetime

from database.connection import dm


class Queries:
    @staticmethod
    def criar_usuario(usuario, senha_hash):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO usuarios (usuario, senha, criado_em) VALUES (%s, %s, %s)",
                    (usuario, senha_hash, datetime.now().strftime("%d/%m/%Y %H:%M")),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def buscar_usuario_login(usuario, senha_hash):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM usuarios WHERE usuario=%s AND senha=%s",
                    (usuario, senha_hash),
                )
                row = cur.fetchone()
            return row
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def inserir_prova(prova_id, usuario_id, materia, titulo, questoes_json):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO provas (id, usuario_id, materia, titulo, questoes, criada_em)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        prova_id,
                        usuario_id,
                        materia,
                        titulo,
                        questoes_json,
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def update_prova(prova_id, materia, titulo, questoes_json):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE provas SET materia=%s, titulo=%s, questoes=%s WHERE id=%s",
                    (materia, titulo, questoes_json, prova_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM provas WHERE id=%s", (prova_id,))
                row = cur.fetchone()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_provas_por_usuario(usuario_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM provas WHERE usuario_id=%s ORDER BY criada_em DESC",
                    (usuario_id,),
                )
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def delete_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM eventos WHERE prova_id=%s", (prova_id,))
                cur.execute("DELETE FROM acessos_prova WHERE prova_id=%s", (prova_id,))
                cur.execute("DELETE FROM respostas WHERE prova_id=%s", (prova_id,))
                cur.execute("DELETE FROM provas WHERE id=%s", (prova_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def aluno_ja_respondeu(prova_id, nome_aluno):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM respostas WHERE prova_id=%s AND nome_aluno=%s",
                    (prova_id, nome_aluno),
                )
                row = cur.fetchone()
            return row is not None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def inserir_resposta(prova_id, nome_aluno, respostas_dict, nota):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO respostas (prova_id, nome_aluno, respostas, nota, respondida_em)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        prova_id,
                        nome_aluno,
                        json.dumps(respostas_dict, ensure_ascii=False),
                        nota,
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_respostas_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM respostas WHERE prova_id=%s ORDER BY respondida_em DESC",
                    (prova_id,),
                )
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def inserir_evento(prova_id, nome_aluno, evento, detalhe, timestamp):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO eventos (prova_id, nome_aluno, evento, detalhe, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (prova_id, nome_aluno, evento, detalhe, timestamp),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_eventos_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM eventos WHERE prova_id=%s ORDER BY timestamp ASC",
                    (prova_id,),
                )
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def inserir_acesso_prova(token, prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE acessos_prova SET ativo=0 WHERE prova_id=%s",
                    (prova_id,),
                )
                cur.execute(
                    """
                    INSERT INTO acessos_prova (token, prova_id, ativo, criado_em)
                    VALUES (%s, %s, 1, %s)
                    """,
                    (token, prova_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def acesso_prova_valido(prova_id, token):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT token
                    FROM acessos_prova
                    WHERE prova_id=%s AND token=%s AND ativo=1
                    """,
                    (prova_id, token),
                )
                row = cur.fetchone()
            return row is not None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def revogar_acesso_prova(token):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE acessos_prova SET ativo=0 WHERE token=%s",
                    (token,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
