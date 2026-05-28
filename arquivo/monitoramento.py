import streamlit as st
import pandas as pd
from datetime import datetime as dt
from data_base import DataManager as dm


class Monitoramento:

    @staticmethod
    def registrar_evento(prova_id, nome_aluno, evento, detalhe=""):
        conn = dm.get_conn()

        conn.execute(
            """
            INSERT INTO eventos
            (prova_id, nome_aluno, evento, detalhe, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                prova_id,
                nome_aluno,
                evento,
                detalhe,
                dt.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            )
        )

        conn.commit()
        conn.close()

    @staticmethod
    def obter_eventos_prova(prova_id):
        conn = dm.get_conn()

        rows = conn.execute(
            """
            SELECT *
            FROM eventos
            WHERE prova_id=?
            ORDER BY timestamp ASC
            """,
            (prova_id,)
        ).fetchall()

        conn.close()

        return [dict(r) for r in rows]

    @staticmethod
    def agregar_eventos_por_aluno(prova_id):

        eventos = Monitoramento.obter_eventos_prova(prova_id)

        estado = {}

        for ev in eventos:

            nome = ev["nome_aluno"]

            if nome not in estado:
                estado[nome] = {
                    "nome": nome,
                    "chamada": "—",
                    "status": "offline",
                    "vezes_saiu": 0,
                    "ultimo_evento": "—",
                    "data_hora_ultima": "—",
                    "timestamp_ultima": 0.0,
                    "eventos_raw": []
                }

            aluno = estado[nome]

            tipo = ev["evento"]
            detalhe = ev.get("detalhe", "")
            timestamp = ev["timestamp"]

            aluno["eventos_raw"].append(ev)

            if tipo == "login":

                aluno["status"] = "online"
                aluno["ultimo_evento"] = "Login"

                detalhe_lower = detalhe.lower().strip()

                if "chamada" in detalhe_lower and ":" in detalhe:
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

            elif tipo == "screenshot":

                aluno["ultimo_evento"] = "🚨 Screenshot detectado"

            aluno["data_hora_ultima"] = timestamp

            try:
                aluno["timestamp_ultima"] = dt.strptime(
                    timestamp,
                    "%Y-%m-%d %H:%M:%S.%f"
                ).timestamp()

            except Exception:
                aluno["timestamp_ultima"] = 0.0

        return estado

    @staticmethod
    def montar_dataframe_monitoramento(estado):

        dados = []

        for nome, info in estado.items():

            status_icone = {
                "online": "🟢 Online",
                "fora_da_aba": "🟡 Fora da aba",
                "finalizou": "🟣 Finalizou",
                "offline": "⚫ Offline"
            }.get(info["status"], "⚫ Offline")

            evento_display = info["ultimo_evento"]

            if "Saiu" in evento_display and info["vezes_saiu"] > 0:
                evento_display = (
                    f"{evento_display} ({info['vezes_saiu']}x)"
                )

            dados.append({
                "👤 Nome": nome,
                "📞 Chamada": info["chamada"],
                "🟢 Status": status_icone,
                "📍 Saídas": info["vezes_saiu"],
                "📝 Último evento": evento_display,
                "⏰ Última atividade": info["data_hora_ultima"],
            })

        df = pd.DataFrame(dados)

        if not df.empty:

            ordem = {
                "🟢 Online": 0,
                "🟡 Fora da aba": 1,
                "🟣 Finalizou": 2,
                "⚫ Offline": 3
            }

            df["_s"] = df["🟢 Status"].map(ordem).fillna(99)

            df = (
                df
                .sort_values("_s")
                .drop("_s", axis=1)
            )

        return df

    @staticmethod
    def exibir_painel_monitoramento(prova_id, nome_prova):

        st.subheader("🟢 Monitoramento em Tempo Real")

        st.caption(f"📋 Prova: **{nome_prova}**")

        estado = Monitoramento.agregar_eventos_por_aluno(prova_id)

        df = Monitoramento.montar_dataframe_monitoramento(estado)

        total = len(estado)

        online = sum(
            1 for a in estado.values()
            if a["status"] == "online"
        )

        fora_aba = sum(
            1 for a in estado.values()
            if a["status"] == "fora_da_aba"
        )

        finalizados = sum(
            1 for a in estado.values()
            if a["status"] == "finalizou"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("👥 Total", total)

        c2.metric(
            "🟢 Online",
            online,
            delta=f"{online}/{total}"
        )

        c3.metric("🟡 Fora da aba", fora_aba)

        c4.metric("🟣 Finalizados", finalizados)

        st.markdown("---")

        st.markdown("### 📊 Status de cada aluno")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "👤 Nome": st.column_config.TextColumn(width="medium"),
                "📞 Chamada": st.column_config.TextColumn(width="small"),
                "🟢 Status": st.column_config.TextColumn(width="medium"),
                "📍 Saídas": st.column_config.NumberColumn(width="small"),
                "📝 Último evento": st.column_config.TextColumn(width="large"),
                "⏰ Última atividade": st.column_config.TextColumn(width="large"),
            }
        )

        st.markdown("---")

        st.markdown("### ⚠️ Comportamentos Suspeitos")

        alertas = []

        for nome, info in estado.items():

            if info["vezes_saiu"] > 2:

                alertas.append({
                    "👤 Aluno": nome,
                    "⚠️ Problema": (
                        f"Saiu da aba {info['vezes_saiu']} vezes"
                    ),
                    "🔴 Risco": "Alto",
                    "⏰ Última vez": info["data_hora_ultima"]
                })

            elif (
                info["vezes_saiu"] > 0
                and info["status"] == "fora_da_aba"
            ):

                alertas.append({
                    "👤 Aluno": nome,
                    "⚠️ Problema": (
                        f"Fora da aba (saiu {info['vezes_saiu']}x)"
                    ),
                    "🔴 Risco": "Médio",
                    "⏰ Última vez": info["data_hora_ultima"]
                })

        if alertas:

            st.dataframe(
                pd.DataFrame(alertas),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "✅ Nenhum comportamento suspeito detectado"
            )

        st.markdown("---")

        with st.expander(
            "🔍 Histórico detalhado de eventos por aluno"
        ):

            nomes = sorted(estado.keys())

            if nomes:

                aluno_selecionado = st.selectbox(
                    "Escolha um aluno",
                    nomes,
                    key="sel_aluno_det"
                )

                info = estado[aluno_selecionado]

                ci1, ci2, ci3 = st.columns(3)

                ci1.metric("Nome", info["nome"])

                ci2.metric("Chamada", info["chamada"])

                ci3.metric(
                    "Vezes saiu",
                    info["vezes_saiu"]
                )

                st.caption("**📜 Timeline**")

                for ev in info["eventos_raw"]:

                    icone = {
                        "login": "🔓",
                        "blur": "👁️",
                        "focus": "✅",
                        "submit": "📤",
                        "screenshot": "🚨"
                    }.get(ev["evento"], "📌")

                    mensagem = (
                        f"{icone} "
                        f"**{ev['evento'].upper()}** "
                        f"— {ev['timestamp']}"
                    )

                    if ev["detalhe"]:
                        mensagem += (
                            f" _(detalhe: {ev['detalhe']})_"
                        )

                    st.caption(mensagem)

        st.markdown("---")

        st.info(
            "🔄 O painel atualiza automaticamente a cada 3 segundos"
        )