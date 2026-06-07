"""
# data_base.py + provas.py + parte do auth.py (acesso ao banco)
"""

import json
from datetime import datetime

from core.normalization import normalizar_nome
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
                    INSERT INTO provas (
                        id, usuario_id, materia, titulo, questoes, criada_em, requer_alunos_autorizados
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
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
    def update_gabarito_e_notas(prova_id, questoes_json, notas_respostas):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE provas SET questoes=%s WHERE id=%s",
                    (questoes_json, prova_id),
                )
                for resposta_id, nota in notas_respostas:
                    cur.execute(
                        "UPDATE respostas SET nota=%s WHERE id=%s AND prova_id=%s",
                        (nota, resposta_id, prova_id),
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
                cur.execute("DELETE FROM prova_alunos_autorizados WHERE prova_id=%s", (prova_id,))
                cur.execute("DELETE FROM aluno_acessos WHERE prova_id=%s", (prova_id,))
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
        nome_normalizado = normalizar_nome(nome_aluno)
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nome_aluno FROM respostas WHERE prova_id=%s",
                    (prova_id,),
                )
                rows = cur.fetchall()
            for row in rows:
                if normalizar_nome(row["nome_aluno"]) == nome_normalizado:
                    return dict(row)
            return None
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
    def inserir_acesso_prova(token, prova_id, expira_em):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE acessos_prova SET ativo=0 WHERE prova_id=%s",
                    (prova_id,),
                )
                cur.execute(
                    """
                    INSERT INTO acessos_prova (token, prova_id, ativo, criado_em, expira_em)
                    VALUES (%s, %s, 1, %s, %s)
                    """,
                    (token, prova_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), expira_em),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_acesso_prova(prova_id, token):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT token, prova_id, ativo, criado_em, expira_em
                    FROM acessos_prova
                    WHERE prova_id=%s AND token=%s
                    """,
                    (prova_id, token),
                )
                row = cur.fetchone()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def acesso_prova_valido(prova_id, token):
        row = Queries.get_acesso_prova(prova_id, token)
        if not row:
            return False
        if int(row.get("ativo") or 0) != 1:
            return False
        expira_em = row.get("expira_em")
        if not expira_em:
            return False
        return expira_em > datetime.utcnow()

    @staticmethod
    def bloquear_acesso_prova(prova_id, token):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE acessos_prova SET ativo=0 WHERE prova_id=%s AND token=%s",
                    (prova_id, token),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_acessos_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT token, prova_id, ativo, criado_em, expira_em
                    FROM acessos_prova
                    WHERE prova_id=%s
                    ORDER BY expira_em DESC NULLS LAST, criado_em DESC
                    """,
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
    def get_acesso_ativo_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT token, prova_id, ativo, criado_em, expira_em
                    FROM acessos_prova
                    WHERE prova_id=%s AND ativo=1 AND expira_em > %s
                    ORDER BY expira_em DESC
                    LIMIT 1
                    """,
                    (prova_id, datetime.utcnow()),
                )
                row = cur.fetchone()
            return dict(row) if row else None
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

    @staticmethod
    def criar_ou_atualizar_aluno_acesso(prova_id, token, nome_aluno, device_id):
        nome_normalizado = normalizar_nome(nome_aluno)
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO aluno_acessos (
                        prova_id,
                        token,
                        nome_aluno,
                        nome_normalizado,
                        device_id,
                        status,
                        ultimo_evento_em
                    )
                    VALUES (%s, %s, %s, %s, %s, 'ativo', %s)
                    ON CONFLICT (prova_id, token, nome_normalizado, device_id)
                    DO UPDATE SET
                        nome_aluno = EXCLUDED.nome_aluno,
                        ultimo_evento_em = EXCLUDED.ultimo_evento_em
                    RETURNING *
                    """,
                    (prova_id, token, nome_aluno, nome_normalizado, device_id, datetime.utcnow()),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_aluno_acesso(prova_id, token, nome_aluno, device_id):
        nome_normalizado = normalizar_nome(nome_aluno)
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM aluno_acessos
                    WHERE prova_id=%s
                      AND token=%s
                      AND nome_normalizado=%s
                      AND device_id=%s
                    LIMIT 1
                    """,
                    (prova_id, token, nome_normalizado, device_id),
                )
                row = cur.fetchone()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_aluno_acesso_por_id(prova_id, acesso_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM aluno_acessos
                    WHERE prova_id=%s
                      AND id=%s
                    LIMIT 1
                    """,
                    (prova_id, acesso_id),
                )
                row = cur.fetchone()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def bloquear_aluno_acesso(prova_id, token, nome_aluno, device_id, motivo):
        if not nome_aluno or not device_id:
            return False

        nome_normalizado = normalizar_nome(nome_aluno)
        agora = datetime.utcnow()
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE aluno_acessos
                    SET status='bloqueado',
                        motivo_bloqueio=%s,
                        bloqueado_em=%s,
                        ultimo_evento_em=%s
                    WHERE prova_id=%s
                      AND token=%s
                      AND nome_normalizado=%s
                      AND device_id=%s
                    RETURNING *
                    """,
                    (motivo, agora, agora, prova_id, token, nome_normalizado, device_id),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def finalizar_aluno_acesso(prova_id, token, nome_aluno, device_id):
        if not nome_aluno or not device_id:
            return False

        nome_normalizado = normalizar_nome(nome_aluno)
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE aluno_acessos
                    SET status='finalizado',
                        ultimo_evento_em=%s
                    WHERE prova_id=%s
                      AND token=%s
                      AND nome_normalizado=%s
                      AND device_id=%s
                      AND status <> 'bloqueado'
                    RETURNING *
                    """,
                    (datetime.utcnow(), prova_id, token, nome_normalizado, device_id),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def desbloquear_aluno_acesso(prova_id, acesso_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE aluno_acessos
                    SET status='ativo',
                        ultimo_evento_em=%s
                    WHERE id=%s
                      AND prova_id=%s
                      AND status='bloqueado'
                    RETURNING *
                    """,
                    (datetime.utcnow(), acesso_id, prova_id),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_aluno_acessos_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM aluno_acessos
                    WHERE prova_id=%s
                    ORDER BY ultimo_evento_em DESC NULLS LAST, criado_em DESC
                    """,
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
    def criar_turma(usuario_id, nome, alunos):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO turmas (usuario_id, nome)
                    VALUES (%s, %s)
                    RETURNING id, usuario_id, nome, criada_em
                    """,
                    (usuario_id, nome),
                )
                turma = dict(cur.fetchone())

                valores_alunos = [
                    (turma["id"], aluno_nome.strip(), normalizar_nome(aluno_nome))
                    for aluno_nome in alunos
                    if aluno_nome and aluno_nome.strip()
                ]
                if valores_alunos:
                    cur.executemany(
                        """
                        INSERT INTO alunos (turma_id, nome, nome_normalizado)
                        VALUES (%s, %s, %s)
                        """,
                        valores_alunos,
                    )
            conn.commit()
            return turma
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def listar_turmas(usuario_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        t.id AS turma_id,
                        t.nome AS turma_nome,
                        t.criada_em AS turma_criada_em,
                        a.id AS aluno_id,
                        a.nome AS aluno_nome,
                        a.nome_normalizado
                    FROM turmas t
                    LEFT JOIN alunos a ON a.turma_id = t.id
                    WHERE t.usuario_id=%s
                    ORDER BY t.criada_em DESC, t.id DESC, a.nome ASC
                    """,
                    (usuario_id,),
                )
                rows = cur.fetchall()

            turmas = {}
            for row in rows:
                tid = row["turma_id"]
                if tid not in turmas:
                    turmas[tid] = {
                        "id": tid,
                        "nome": row["turma_nome"],
                        "criada_em": row["turma_criada_em"],
                        "alunos": [],
                    }
                if row["aluno_id"] is not None:
                    turmas[tid]["alunos"].append(
                        {
                            "id": row["aluno_id"],
                            "nome": row["aluno_nome"],
                            "nome_normalizado": row["nome_normalizado"],
                            "turma_id": tid,
                            "turma_nome": row["turma_nome"],
                        }
                    )
            return list(turmas.values())
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def listar_alunos_usuario(usuario_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        a.id,
                        a.turma_id,
                        a.nome,
                        a.nome_normalizado,
                        a.criado_em,
                        t.nome AS turma_nome
                    FROM alunos a
                    INNER JOIN turmas t ON t.id = a.turma_id
                    WHERE t.usuario_id=%s
                    ORDER BY t.nome ASC, a.nome ASC
                    """,
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
    def delete_turma(turma_id, usuario_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM turmas WHERE id=%s AND usuario_id=%s RETURNING id",
                    (turma_id, usuario_id),
                )
                row = cur.fetchone()
            conn.commit()
            return row is not None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def alunos_pertencem_usuario(usuario_id, aluno_ids):
        if not aluno_ids:
            return False

        ids = [int(aluno_id) for aluno_id in aluno_ids]
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM alunos a
                    INNER JOIN turmas t ON t.id = a.turma_id
                    WHERE t.usuario_id=%s AND a.id = ANY(%s)
                    """,
                    (usuario_id, ids),
                )
                row = cur.fetchone()
            return int(row["total"] or 0) == len(set(ids))
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def inserir_prova_alunos_autorizados(prova_id, aluno_ids):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM prova_alunos_autorizados WHERE prova_id=%s",
                    (prova_id,),
                )
                valores = [(prova_id, int(aluno_id)) for aluno_id in sorted(set(aluno_ids))]
                if valores:
                    cur.executemany(
                        """
                        INSERT INTO prova_alunos_autorizados (prova_id, aluno_id)
                        VALUES (%s, %s)
                        ON CONFLICT (prova_id, aluno_id) DO NOTHING
                        """,
                        valores,
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def prova_tem_alunos_autorizados(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM prova_alunos_autorizados
                        WHERE prova_id=%s
                    ) AS tem_autorizados
                    """,
                    (prova_id,),
                )
                row = cur.fetchone()
            return bool(row["tem_autorizados"]) if row else False
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_alunos_autorizados_prova(prova_id):
        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        a.id,
                        a.nome,
                        a.turma_id,
                        t.nome AS turma_nome
                    FROM prova_alunos_autorizados paa
                    INNER JOIN alunos a ON a.id = paa.aluno_id
                    INNER JOIN turmas t ON t.id = a.turma_id
                    WHERE paa.prova_id=%s
                    ORDER BY t.nome, a.nome
                    """,
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
    def aluno_autorizado_prova(prova_id, nome_aluno):
        nome_normalizado = normalizar_nome(nome_aluno)
        if not nome_normalizado:
            return False

        conn = dm.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT a.id, a.nome, a.turma_id
                    FROM prova_alunos_autorizados paa
                    INNER JOIN alunos a ON a.id = paa.aluno_id
                    WHERE paa.prova_id=%s AND a.nome_normalizado=%s
                    LIMIT 1
                    """,
                    (prova_id, nome_normalizado),
                )
                row = cur.fetchone()
            return dict(row) if row else None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
