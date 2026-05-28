"""
# prova_visualizacao.py
"""

import json

from core.constants import LETRAS_OPCOES
from core.utils import render_student_protection, render_tab_exit_lock


def render_visualizacao_prova(st, prova_id, prova_service, registrar_evento):
    prova = prova_service.buscar_prova(prova_id)
    if not prova:
        st.error(f"Prova não encontrada. ID recebido: {prova_id}")
        st.stop()

    questoes = json.loads(prova["questoes"])
    st.title(prova["titulo"])
    st.caption(prova["materia"])
    render_student_protection(st)
    render_tab_exit_lock(st, prova_id, st.session_state.get("nome_aluno", ""))

    nome_aluno = st.session_state.get("nome_aluno", "")
    if nome_aluno and prova_service.aluno_ja_respondeu(prova_id, nome_aluno):
        st.error("Você já enviou esta prova.")
        respostas = prova_service.buscar_respostas(prova_id)
        resp_aluno = next((r for r in respostas if r["nome_aluno"] == nome_aluno), None)
        if resp_aluno:
            st.session_state.prova_enviada = True
            st.session_state.nota = resp_aluno["nota"]
            st.session_state.respostas_final = json.loads(resp_aluno["respostas"])

    respostas_aluno = {}
    if not st.session_state.prova_enviada:
        for i, q in enumerate(questoes):
            st.markdown(f"### Questão {i+1}")
            st.write(q["enunciado"])
            if q.get("imagem"):
                st.image(f"data:image/png;base64,{q['imagem']}")
            tipo = q.get("tipo", "multipla_escolha")
            if tipo == "texto":
                resposta = st.text_input("Digite sua resposta:", key=f"q_{i}")
                respostas_aluno[f"q{i}"] = resposta
            else:
                opcoes = q.get("opcoes", [])
                op = st.radio(
                    "Escolha:",
                    options=LETRAS_OPCOES[: len(opcoes)],
                    format_func=lambda x, q=q: f"{x}) {q['opcoes'][LETRAS_OPCOES.index(x)]}",
                    key=f"q_{i}",
                )
                respostas_aluno[f"q{i}"] = op
            st.divider()

        if st.button("Enviar prova", type="primary"):
            nota = prova_service.calcular_nota(questoes, respostas_aluno)
            prova_service.salvar_resposta(prova_id, nome_aluno, respostas_aluno, nota)
            registrar_evento(prova_id, nome_aluno, "submit")
            st.session_state.prova_enviada = True
            st.session_state.nota = nota
            st.session_state.respostas_final = respostas_aluno
            st.rerun()

    if st.session_state.prova_enviada:
        st.markdown("## Resultado")
        st.write(f"Nota: {st.session_state.nota}")
        acertos = prova_service.contar_acertos(questoes, st.session_state.respostas_final)
        st.write(f"Acertos: {acertos}/{len(questoes)}")
