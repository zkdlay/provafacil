# provas.py

import json
import uuid

from datetime import datetime

from data_base import DataManager as dm


class Provas:

    # ─────────────────────────────────────────────────────────
    # CRUD DE PROVAS
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def salvar_prova(usuario_id, materia, titulo, questoes):

        prova_id = str(uuid.uuid4())[:8]

        conn = dm.get_conn()

        conn.execute(
            """
            INSERT INTO provas
            (id, usuario_id, materia, titulo, questoes, criada_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                prova_id,
                usuario_id,
                materia,
                titulo,
                json.dumps(questoes, ensure_ascii=False),
                datetime.now().strftime("%d/%m/%Y %H:%M")
            )
        )

        conn.commit()
        conn.close()

        return prova_id

    @staticmethod
    def atualizar_prova(prova_id, materia, titulo, questoes):

        conn = dm.get_conn()

        conn.execute(
            """
            UPDATE provas
            SET materia=?, titulo=?, questoes=?
            WHERE id=?
            """,
            (
                materia,
                titulo,
                json.dumps(questoes, ensure_ascii=False),
                prova_id
            )
        )

        conn.commit()
        conn.close()

    @staticmethod
    def buscar_prova(prova_id):

        conn = dm.get_conn()

        row = conn.execute(
            "SELECT * FROM provas WHERE id=?",
            (prova_id,)
        ).fetchone()

        conn.close()

        return dict(row) if row else None

    @staticmethod
    def listar_provas(usuario_id):

        conn = dm.get_conn()

        rows = conn.execute(
            """
            SELECT *
            FROM provas
            WHERE usuario_id=?
            ORDER BY criada_em DESC
            """,
            (usuario_id,)
        ).fetchall()

        conn.close()

        return [dict(r) for r in rows]

    @staticmethod
    def excluir_prova(prova_id):

        conn = dm.get_conn()

        conn.execute(
            "DELETE FROM respostas WHERE prova_id=?",
            (prova_id,)
        )

        conn.execute(
            "DELETE FROM provas WHERE id=?",
            (prova_id,)
        )

        conn.commit()
        conn.close()

    # ─────────────────────────────────────────────────────────
    # CRUD DE RESPOSTAS
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def aluno_ja_respondeu(prova_id, nome_aluno):

        conn = dm.get_conn()

        row = conn.execute(
            """
            SELECT id
            FROM respostas
            WHERE prova_id=? AND nome_aluno=?
            """,
            (prova_id, nome_aluno)
        ).fetchone()

        conn.close()

        return row is not None

    @staticmethod
    def salvar_resposta(
        prova_id,
        nome_aluno,
        respostas_aluno,
        nota
    ):

        conn = dm.get_conn()

        conn.execute(
            """
            INSERT INTO respostas
            (prova_id, nome_aluno, respostas, nota, respondida_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                prova_id,
                nome_aluno,
                json.dumps(respostas_aluno, ensure_ascii=False),
                nota,
                datetime.now().strftime("%d/%m/%Y %H:%M")
            )
        )

        conn.commit()
        conn.close()

    @staticmethod
    def buscar_respostas(prova_id):

        conn = dm.get_conn()

        rows = conn.execute(
            """
            SELECT *
            FROM respostas
            WHERE prova_id=?
            ORDER BY respondida_em DESC
            """,
            (prova_id,)
        ).fetchall()

        conn.close()

        return [dict(r) for r in rows]

    @staticmethod
    def calcular_nota(questoes, respostas_aluno):

        total = len(questoes)

        acertos = sum(
            1
            for i, q in enumerate(questoes)
            if respostas_aluno.get(f"q{i}") == q["gabarito"]
        )

        if total <= 0:
            return 0

        return round((acertos / total) * 10, 1)

    @staticmethod
    def salvar_resposta_fraude(prova_id, nome_aluno):

        conn = dm.get_conn()

        conn.execute(
            """
            INSERT INTO respostas
            (prova_id, nome_aluno, respostas, nota, respondida_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                prova_id,
                nome_aluno,
                json.dumps(
                    {
                        "fraude": "múltiplas abas detectadas"
                    }
                ),
                0.0,
                datetime.now().strftime("%d/%m/%Y %H:%M")
            )
        )

        conn.commit()
        conn.close()