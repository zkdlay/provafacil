


# ── ABA: MONITORAMENTO ────────────────────────────────────────────────────────
elif aba == "🟢 Monitoramento":
    provas = listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova disponível."); st.stop()

    opcoes  = {f"{p['titulo']} ({p['materia']})": p["id"] for p in provas}
    escolha = st.selectbox("Selecione a prova para monitorar", list(opcoes.keys()))
    prova_id = opcoes[escolha]

    exibir_painel_monitoramento(prova_id, escolha)

    time.sleep(3)
    st.rerun()