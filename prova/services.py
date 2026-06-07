"""
# provas.py (classe Provas)
"""

import json
import random
import re
import secrets
import uuid
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime, timedelta

from core.constants import LINK_EXPIRATION_MINUTES
from database.queries import Queries


STOPWORDS_TEXTO = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "por",
    "porque",
    "que",
    "quanto",
    "se",
    "sao",
    "ser",
    "sua",
    "suas",
    "seu",
    "seus",
    "um",
    "uma",
    "uns",
    "umas",
}

VERBOS_GENERICOS_TEXTO = {
    "apresenta",
    "apresentam",
    "apresentar",
    "apresentarem",
    "classifica",
    "classificam",
    "classificar",
    "possui",
    "possuem",
    "possuir",
    "tem",
    "ter",
}

NEGACOES_TEXTO = {"nao", "nem", "nunca", "jamais", "sem"}


class ProvaService:
    @staticmethod
    def questao_id(indice, questao):
        return str((questao or {}).get("id") or f"q{indice}")

    @staticmethod
    def normalizar_questoes_para_salvar(questoes, questoes_atuais=None):
        atuais = questoes_atuais or []
        normalizadas = []
        for indice, questao in enumerate(questoes or []):
            atual = atuais[indice] if indice < len(atuais) and isinstance(atuais[indice], dict) else {}
            tipo = "texto" if questao.get("tipo") == "texto" else "multipla_escolha"
            qid = str(questao.get("id") or atual.get("id") or f"q{indice}")
            comum = {
                "id": qid,
                "tipo": tipo,
                "enunciado": str(questao.get("enunciado") or "").strip(),
                "imagem": questao.get("imagem") or None,
            }
            if tipo == "texto":
                normalizadas.append(
                    {
                        **comum,
                        "opcoes": [],
                        "imagens_opcoes": [],
                        "gabarito": "",
                        "gabarito_texto": str(questao.get("gabarito_texto") or "").strip(),
                    }
                )
                continue

            opcoes = questao.get("opcoes") if isinstance(questao.get("opcoes"), list) else []
            imagens = questao.get("imagens_opcoes") if isinstance(questao.get("imagens_opcoes"), list) else []
            opcoes = [str(opcao or "") for opcao in opcoes[:5]]
            imagens = [(imagens[i] if i < len(imagens) else None) for i in range(len(opcoes))]
            normalizadas.append(
                {
                    **comum,
                    "opcoes": opcoes,
                    "imagens_opcoes": imagens,
                    "gabarito": str(questao.get("gabarito") or "").strip().upper(),
                    "gabarito_texto": "",
                }
            )
        return normalizadas

    @staticmethod
    def resposta_da_questao(respostas_aluno, indice, questao):
        if not isinstance(respostas_aluno, dict):
            return None
        qid = questao.get("id")
        if qid and qid in respostas_aluno:
            return respostas_aluno.get(qid)
        return respostas_aluno.get(f"q{indice}")

    @staticmethod
    def ids_questoes(questoes):
        return [ProvaService.questao_id(indice, questao) for indice, questao in enumerate(questoes or [])]

    @staticmethod
    def normalizar_ordem_questoes(questoes, ordem=None):
        ids = ProvaService.ids_questoes(questoes)
        ids_validos = set(ids)
        ordem_base = []
        if isinstance(ordem, str) and ordem:
            try:
                ordem = json.loads(ordem)
            except json.JSONDecodeError:
                ordem = []
        if isinstance(ordem, list):
            ordem_base = [str(qid) for qid in ordem if str(qid) in ids_validos]
        faltantes = [qid for qid in ids if qid not in ordem_base]
        return ordem_base + faltantes

    @staticmethod
    def gerar_ordem_questoes(questoes, embaralhar=False):
        ordem = ProvaService.ids_questoes(questoes)
        if embaralhar and len(ordem) > 1:
            random.SystemRandom().shuffle(ordem)
        return ordem

    @staticmethod
    def ordenar_questoes_por_ids(questoes, ordem):
        por_id = {ProvaService.questao_id(indice, questao): questao for indice, questao in enumerate(questoes or [])}
        ordem_normalizada = ProvaService.normalizar_ordem_questoes(questoes, ordem)
        return [{**por_id[qid], "id": qid} for qid in ordem_normalizada if qid in por_id]

    @staticmethod
    def _normalizar_texto(valor):
        if valor is None:
            return ""
        texto = str(valor).strip().lower()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
        texto = re.sub(r"[^a-z0-9\s]", " ", texto)
        texto = re.sub(r"\s+", " ", texto)
        return texto

    @staticmethod
    def normalizar_texto_resposta(valor):
        return ProvaService._normalizar_texto(valor)

    @staticmethod
    def _tokens_resposta(valor):
        texto = ProvaService.normalizar_texto_resposta(valor)
        tokens = re.findall(r"[a-z0-9]+", texto)
        return [
            token
            for token in tokens
            if token not in STOPWORDS_TEXTO and token not in VERBOS_GENERICOS_TEXTO
        ]

    @staticmethod
    def _tem_negacao(valor):
        return any(token in NEGACOES_TEXTO for token in ProvaService._tokens_resposta(valor))

    @staticmethod
    def _negacao_compativel(resposta_aluno, gabarito_texto):
        return ProvaService._tem_negacao(resposta_aluno) == ProvaService._tem_negacao(gabarito_texto)

    @staticmethod
    def _similaridade(a, b):
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def _token_correspondente(token, candidatos):
        if token in candidatos:
            return True
        if len(token) <= 3:
            return False
        return any(ProvaService._similaridade(token, candidato) >= 0.84 for candidato in candidatos)

    @staticmethod
    def _cobertura_tokens(tokens_aluno, tokens_gabarito):
        if not tokens_gabarito:
            return 0
        return sum(
            1
            for token in tokens_gabarito
            if ProvaService._token_correspondente(token, tokens_aluno)
        ) / len(tokens_gabarito)

    @staticmethod
    def _termos_lista(valor):
        if valor is None:
            return []
        texto = str(valor).strip().lower()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
        partes = re.split(r"\s*(?:,|;|\n|\be\b)\s*", texto)
        termos = []
        for parte in partes:
            tokens = ProvaService._tokens_resposta(parte)
            if tokens:
                termos.append(" ".join(tokens))
        return termos

    @staticmethod
    def _termo_correspondente(termo, candidatos):
        if termo in candidatos:
            return True
        return any(ProvaService._similaridade(termo, candidato) >= 0.86 for candidato in candidatos)

    @staticmethod
    def _comparar_listas_termos(resposta_aluno, gabarito_texto):
        termos_aluno = ProvaService._termos_lista(resposta_aluno)
        termos_gabarito = ProvaService._termos_lista(gabarito_texto)
        if len(termos_gabarito) < 3 or len(termos_aluno) < 2:
            return False, 0

        cobertura = sum(
            1
            for termo in termos_gabarito
            if ProvaService._termo_correspondente(termo, termos_aluno)
        ) / len(termos_gabarito)
        return cobertura >= 0.85, cobertura

    @staticmethod
    def corrigir_resposta_texto(resposta_aluno, gabarito_texto, retornar_detalhes=False):
        normalizado_aluno = ProvaService.normalizar_texto_resposta(resposta_aluno)
        normalizado_gabarito = ProvaService.normalizar_texto_resposta(gabarito_texto)

        def finalizar(correta, motivo, similaridade=0, cobertura=0):
            detalhes = {
                "normalizado_aluno": normalizado_aluno,
                "normalizado_gabarito": normalizado_gabarito,
                "similaridade": round(similaridade, 3),
                "cobertura": round(cobertura, 3),
                "motivo": motivo,
            }
            return (correta, detalhes) if retornar_detalhes else correta

        if not normalizado_aluno or not normalizado_gabarito:
            return finalizar(False, "resposta_ou_gabarito_vazio")

        if not ProvaService._negacao_compativel(normalizado_aluno, normalizado_gabarito):
            return finalizar(False, "negacao_incompativel")

        if normalizado_aluno == normalizado_gabarito:
            return finalizar(True, "igualdade_normalizada", 1, 1)

        lista_correta, cobertura_lista = ProvaService._comparar_listas_termos(
            normalizado_aluno,
            normalizado_gabarito,
        )
        if lista_correta:
            return finalizar(True, "lista_de_termos_equivalente", 1, cobertura_lista)

        tokens_aluno = ProvaService._tokens_resposta(normalizado_aluno)
        tokens_gabarito = ProvaService._tokens_resposta(normalizado_gabarito)
        if not tokens_aluno or not tokens_gabarito:
            return finalizar(False, "sem_tokens_relevantes")

        cobertura = ProvaService._cobertura_tokens(tokens_aluno, tokens_gabarito)
        similaridade = ProvaService._similaridade(normalizado_aluno, normalizado_gabarito)

        if len(tokens_gabarito) >= 4 and len(tokens_aluno) < max(2, len(tokens_gabarito) * 0.5):
            return finalizar(False, "resposta_curta_demais", similaridade, cobertura)

        if cobertura >= 0.9:
            return finalizar(True, "cobertura_alta_de_termos", similaridade, cobertura)

        if similaridade >= 0.8 and cobertura >= 0.65:
            return finalizar(True, "similaridade_e_cobertura_suficientes", similaridade, cobertura)

        if cobertura >= 0.65 and len(tokens_gabarito) <= 3 and len(tokens_aluno) >= 2:
            return finalizar(True, "termos_essenciais_presentes", similaridade, cobertura)

        return finalizar(False, "criterios_insuficientes", similaridade, cobertura)

    @staticmethod
    def _questao_correta(questao, resposta):
        tipo = questao.get("tipo", "multipla_escolha")
        if tipo == "texto":
            return ProvaService.corrigir_resposta_texto(resposta, questao.get("gabarito_texto", ""))
        return resposta == questao.get("gabarito")

    @staticmethod
    def salvar_prova(usuario_id, materia, titulo, questoes, embaralhar_questoes=False):
        prova_id = str(uuid.uuid4())[:8]
        questoes = ProvaService.normalizar_questoes_para_salvar(questoes)
        Queries.inserir_prova(
            prova_id,
            usuario_id,
            materia,
            titulo,
            json.dumps(questoes, ensure_ascii=False),
            embaralhar_questoes,
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
    def criar_ou_atualizar_aluno_acesso(prova_id, token, nome_aluno, device_id):
        return Queries.criar_ou_atualizar_aluno_acesso(prova_id, token, nome_aluno, device_id)

    @staticmethod
    def salvar_ordem_questoes_aluno_acesso(prova_id, token, nome_aluno, device_id, questoes_ordem):
        return Queries.salvar_ordem_questoes_aluno_acesso(
            prova_id, token, nome_aluno, device_id, questoes_ordem
        )

    @staticmethod
    def buscar_aluno_acesso(prova_id, token, nome_aluno, device_id):
        return Queries.get_aluno_acesso(prova_id, token, nome_aluno, device_id)

    @staticmethod
    def buscar_aluno_acesso_por_id(prova_id, acesso_id):
        return Queries.get_aluno_acesso_por_id(prova_id, acesso_id)

    @staticmethod
    def bloquear_aluno_acesso(prova_id, token, nome_aluno, device_id, motivo):
        return Queries.bloquear_aluno_acesso(prova_id, token, nome_aluno, device_id, motivo)

    @staticmethod
    def finalizar_aluno_acesso(prova_id, token, nome_aluno, device_id):
        return Queries.finalizar_aluno_acesso(prova_id, token, nome_aluno, device_id)

    @staticmethod
    def desbloquear_aluno_acesso(prova_id, acesso_id):
        return Queries.desbloquear_aluno_acesso(prova_id, acesso_id)

    @staticmethod
    def listar_aluno_acessos_prova(prova_id):
        return Queries.get_aluno_acessos_prova(prova_id)

    @staticmethod
    def atualizar_prova(prova_id, materia, titulo, questoes):
        Queries.update_prova(prova_id, materia, titulo, json.dumps(questoes, ensure_ascii=False))

    @staticmethod
    def atualizar_gabarito_e_recalcular(prova_id, questoes):
        respostas = Queries.get_respostas_prova(prova_id)
        notas_respostas = []
        for resposta in respostas:
            respostas_aluno = json.loads(resposta["respostas"])
            notas_respostas.append((resposta["id"], ProvaService.calcular_nota(questoes, respostas_aluno)))
        Queries.update_gabarito_e_notas(
            prova_id,
            json.dumps(questoes, ensure_ascii=False),
            notas_respostas,
        )
        return len(notas_respostas)

    @staticmethod
    def alterar_prova_e_recalcular(prova_id, questoes, embaralhar_questoes=False):
        respostas = Queries.get_respostas_prova(prova_id)
        notas_respostas = []
        for resposta in respostas:
            respostas_aluno = json.loads(resposta["respostas"])
            notas_respostas.append((resposta["id"], ProvaService.calcular_nota(questoes, respostas_aluno)))
        Queries.update_prova_com_recalculo(
            prova_id,
            json.dumps(questoes, ensure_ascii=False),
            embaralhar_questoes,
            notas_respostas,
        )
        return len(notas_respostas)

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
    def listar_alunos_autorizados_prova(prova_id):
        return Queries.get_alunos_autorizados_prova(prova_id)

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
    def excluir_tentativa(prova_id, resposta_id):
        return Queries.delete_resposta_prova(prova_id, resposta_id)

    @staticmethod
    def contar_acertos(questoes, respostas_aluno):
        return sum(
            1
            for i, q in enumerate(questoes)
            if ProvaService._questao_correta(q, ProvaService.resposta_da_questao(respostas_aluno, i, q))
        )

    @staticmethod
    def calcular_nota(questoes, respostas_aluno):
        total = len(questoes)
        acertos = ProvaService.contar_acertos(questoes, respostas_aluno)
        return ProvaService.calcular_nota_por_acertos(acertos, total)

    @staticmethod
    def calcular_nota_por_acertos(acertos, total):
        if total <= 0:
            return 0
        return round((acertos / total) * 10, 2)
