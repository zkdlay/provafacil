"""
# monitoramento.py + professor_monitoramento.py
"""

import pandas as pd
import time

from eventos.rastreamento import obter_eventos_prova
from prova.services import ProvaService


def agregar_eventos_por_aluno(prova_id):
    eventos = obter_eventos_prova(prova_id)
    estado = {}
    for ev in eventos:
        nome = ev["nome_aluno"]
        if nome not in estado:
            estado[nome] = {
                "nome": nome,
                "chamada": "-",
                "status": "offline",
                "vezes_saiu": 0,
                "tentativas_nova_aba": 0,
                "ultimo_evento": "-",
                "data_hora_ultima": "-",
                "eventos_raw": [],
            }
        aluno = estado[nome]
        tipo = ev["evento"]
        detalhe = ev.get("detalhe", "")
        ts = ev["timestamp"]
        aluno["eventos_raw"].append(ev)
        if tipo == "login":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Login"
            if "chamada" in detalhe.lower() and ":" in detalhe:
                aluno["chamada"] = detalhe.split(":")[-1].strip()
        elif tipo == "blur":
            aluno["status"] = "fora_da_aba"
            aluno["vezes_saiu"] += 1
            aluno["ultimo_evento"] = "Saiu da aba"
        elif tipo == "focus":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Voltou para aba"
        elif tipo == "submit":
            aluno["status"] = "finalizou"
            aluno["ultimo_evento"] = "Enviou prova"
        elif tipo == "new_tab":
            aluno["tentativas_nova_aba"] += 1
            aluno["ultimo_evento"] = "Tentou abrir nova aba"
        elif tipo == "screenshot":
            aluno["ultimo_evento"] = "Screenshot detectado"
        aluno["data_hora_ultima"] = ts
    return estado


def render_painel_monitoramento(st, prova_id, nome_prova):
    st.subheader("Monitoramento em Tempo Real")
    st.caption(f"Prova: {nome_prova}")
    estado = agregar_eventos_por_aluno(prova_id)
    dados = []
    for nome, info in estado.items():
        dados.append(
            {
                "Nome": nome,
                "Chamada": info["chamada"],
                "Status": info["status"],
                "Saidas": info["vezes_saiu"],
                "Ultimo evento": info["ultimo_evento"],
                "Ultima atividade": info["data_hora_ultima"],
            }
        )
    st.dataframe(pd.DataFrame(dados), width="stretch", hide_index=True)


def render_monitoramento(st):
    provas = ProvaService.listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova disponível.")
        st.stop()
    opcoes = {f"{p['titulo']} ({p['materia']})": p["id"] for p in provas}
    escolha = st.selectbox("Selecione a prova para monitorar", list(opcoes.keys()))
    prova_id = opcoes[escolha]
    render_painel_monitoramento(st, prova_id, escolha)
    time.sleep(5)
    st.rerun()
