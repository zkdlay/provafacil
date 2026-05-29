"""
# provas.py (classe Provas)
"""

import json
import re
import secrets
import uuid
import unicodedata
from datetime import datetime, timedelta

from core.constants import LINK_EXPIRATION_MINUTES
from database.queries import Queries


class ProvaService:
    @staticmethod
    def _normalizar_texto(valor):
        if valor is None:
            return ""
        texto = str(valor).strip().lower()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
        texto = re.sub(r"\s+", " ", texto)
        return texto

    @staticmethod
    def _questao_correta(questao, resposta):
        tipo = questao.get("tipo", "multipla_escolha")
        if tipo == "texto":
            return ProvaService._normalizar_texto(resposta) == ProvaService._normalizar_texto(
                questao.get("gabarito_texto", "")
            )
        return resposta == questao.get("gabarito")

    @staticmethod
    def salvar_prova(usuario_id, materia, titulo, questoes):
        prova_id = str(uuid.uuid4())[:8]
        Queries.inserir_prova(
            prova_id, usuario_id, materia, titulo, json.dumps(questoes, ensure_ascii=False)
        )
        return prova_id

    @staticmethod
    def gerar_token_acesso(prova_id):
        token = secrets.token_urlsafe(12)
        expira_em = datetime.utcnow() + timedelta(minutes=LINK_EXPIRATION_MINUTES)
        Queries.inserir_acesso_prova(token, prova_id, expira_em)
        return {"token": token, "expira_em": expira_em}

    @staticmethod
    def validar_token_acesso(prova_id, token):
        return Queries.acesso_prova_valido(prova_id, token)

    @staticmethod
    def buscar_acesso_prova(prova_id, token):
        return Queries.get_acesso_prova(prova_id, token)

    @staticmethod
    def buscar_acesso_ativo(prova_id):
        return Queries.get_acesso_ativo_prova(prova_id)

    @staticmethod
    def revogar_token_acesso(token):
        Queries.revogar_acesso_prova(token)

    @staticmethod
    def bloquear_token_acesso(prova_id, token):
        Queries.bloquear_acesso_prova(prova_id, token)

    @staticmethod
    def atualizar_prova(prova_id, materia, titulo, questoes):
        Queries.update_prova(prova_id, materia, titulo, json.dumps(questoes, ensure_ascii=False))

    @staticmethod
    def buscar_prova(prova_id):
        return Queries.get_prova(prova_id)

    @staticmethod
    def listar_provas(usuario_id):
        return Queries.get_provas_por_usuario(usuario_id)

    @staticmethod
    def excluir_prova(prova_id):
        Queries.delete_prova(prova_id)

    @staticmethod
    def criar_turma(usuario_id, nome, alunos):
        return Queries.criar_turma(usuario_id, nome, alunos)

    @staticmethod
    def listar_turmas(usuario_id):
        return Queries.listar_turmas(usuario_id)

    @staticmethod
    def listar_alunos(usuario_id):
        return Queries.listar_alunos_usuario(usuario_id)

    @staticmethod
    def excluir_turma(turma_id, usuario_id):
        return Queries.delete_turma(turma_id, usuario_id)

    @staticmethod
    def alunos_pertencem_usuario(usuario_id, aluno_ids):
        return Queries.alunos_pertencem_usuario(usuario_id, aluno_ids)

    @staticmethod
    def salvar_alunos_autorizados(prova_id, aluno_ids):
        Queries.inserir_prova_alunos_autorizados(prova_id, aluno_ids)

    @staticmethod
    def prova_tem_alunos_autorizados(prova_id):
        return Queries.prova_tem_alunos_autorizados(prova_id)

    @staticmethod
    def aluno_autorizado_prova(prova_id, nome_aluno):
        return Queries.aluno_autorizado_prova(prova_id, nome_aluno)

    @staticmethod
    def aluno_ja_respondeu(prova_id, nome_aluno):
        return Queries.aluno_ja_respondeu(prova_id, nome_aluno)

    @staticmethod
    def salvar_resposta(prova_id, nome_aluno, respostas_aluno, nota):
        Queries.inserir_resposta(prova_id, nome_aluno, respostas_aluno, nota)

    @staticmethod
    def buscar_respostas(prova_id):
        return Queries.get_respostas_prova(prova_id)

    @staticmethod
    def contar_acertos(questoes, respostas_aluno):
        return sum(
            1
            for i, q in enumerate(questoes)
            if ProvaService._questao_correta(q, respostas_aluno.get(f"q{i}"))
        )

    @staticmethod
    def calcular_nota(questoes, respostas_aluno):
        total = len(questoes)
        acertos = ProvaService.contar_acertos(questoes, respostas_aluno)
        if total <= 0:
            return 0
        return round((acertos / total) * 10, 1)
