

    # ── LOGIN DO ALUNO ──
    if not st.session_state.aluno_logado:
        st.title("📝 Acesso à Prova")
        nome   = st.text_input("Nome completo")
        numero = st.text_input("Número de chamada")

        if st.button("Acessar prova", type="primary"):
            if not nome.strip() or not numero.strip():
                st.warning("Preencha todos os campos.")
            else:
                registrar_evento(prova_id, nome.strip(), "login",
                                 f"Chamada: {numero.strip()}")
                st.session_state.aluno_logado   = True
                st.session_state.nome_aluno     = nome.strip()
                st.session_state.numero_aluno   = numero.strip()
                # Salva nome no sessionStorage do browser para o JS usar
                nome_js = nome.strip().replace("'", "\\'")
                numero_js = numero.strip()
                st.markdown(
                    f"<script>sessionStorage.setItem('aluno_nome','{nome_js}');"
                    f"sessionStorage.setItem('aluno_chamada','{numero_js}');</script>",
                    unsafe_allow_html=True
                )
                st.rerun()
        st.stop()