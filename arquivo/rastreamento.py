

    # ── PROCESSAR EVENTO ENVIADO PELO JS ──
    # O JS navega para ?prova=ID&evt=blur&det=...&evt_nome=Nome
    evt_tipo = params.get("evt", None)
    if evt_tipo and st.session_state.aluno_logado:
        evt_det  = params.get("det", "")
        evt_nome = params.get("evt_nome") or st.session_state.get("nome_aluno", "")
        if evt_nome:
            registrar_evento(prova_id, evt_nome, evt_tipo, evt_det)
        # Limpa params de evento para não duplicar
        clean = {k: v for k, v in dict(params).items()
                 if k not in ("evt", "det", "evt_nome")}
        st.query_params.update(clean)
        st.rerun()