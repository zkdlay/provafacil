"""
# professor_resultados.py
"""

import json
import pandas as pd

from prova.services import ProvaService


def render_resultados(st):
    st.subheader("Resultados das Provas")
    provas = ProvaService.listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova criada ainda.")
        st.stop()

    op_provas = {f"{p['titulo']} ({p['materia']}) - {p['criada_em']}": p["id"] for p in provas}
    escolha = st.selectbox("Selecione a prova", list(op_provas.keys()))
    pid = op_provas[escolha]
    respostas = ProvaService.buscar_respostas(pid)
    prova = ProvaService.buscar_prova(pid)
    questoes = json.loads(prova["questoes"])

    if not respostas:
        st.warning("Nenhum aluno respondeu esta prova ainda.")
        st.stop()

    notas = [r["nota"] for r in respostas]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alunos", len(respostas))
    c2.metric("Média", f"{sum(notas)/len(notas):.1f}")
    c3.metric("Maior nota", max(notas))
    c4.metric("Menor nota", min(notas))

    dados = []
    for r in respostas:
        resps = json.loads(r["respostas"])
        acertos = ProvaService.contar_acertos(questoes, resps)
        dados.append(
            {
                "Nome": r["nome_aluno"],
                "Nota": r["nota"],
                "Acertos": f"{acertos}/{len(questoes)}",
                "Data/Hora": r["respondida_em"],
            }
        )
    df = pd.DataFrame(dados)
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button(
        "Baixar CSV", df.to_csv(index=False).encode("utf-8"), "resultados.csv", "text/csv"
    )
