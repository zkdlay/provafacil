

    # ETAPA 2
    elif st.session_state.etapa_criacao == 2:
        cfg = st.session_state.config_prova
        st.subheader(f"📝 {cfg['titulo']}")
        st.caption(f"{cfg['materia']} • {cfg['qtd_questoes']} questões")
        letras = ["A","B","C","D","E"]

        for i in range(cfg["qtd_questoes"]):
            with st.expander(f"Questão {i+1}", expanded=(i==0)):
                enunciado = st.text_area("Enunciado", key=f"en_{i}")
                img_q     = st.file_uploader("Imagem da questão (opcional)",
                                              type=["png","jpg","jpeg"], key=f"iq_{i}")
                opcoes, imgs_op = [], []
                for j in range(cfg["qtd_opcoes"]):
                    c1, c2 = st.columns([0.7, 0.3])
                    with c1: opcoes.append(st.text_input(letras[j], key=f"op_{i}_{j}"))
                    with c2: imgs_op.append(st.file_uploader(f"Img {letras[j]}",
                                                              type=["png","jpg","jpeg"],
                                                              key=f"iop_{i}_{j}"))
                gabarito = st.selectbox("Resposta correta",
                                         letras[:cfg["qtd_opcoes"]], key=f"gab_{i}")
                st.session_state.questoes_temp[i] = {
                    "enunciado": enunciado,
                    "imagem":    file_to_base64(img_q),
                    "opcoes":    opcoes,
                    "imagens_opcoes": [file_to_base64(f) for f in imgs_op],
                    "gabarito":  gabarito
                }

        st.markdown("---")
        cA, cB = st.columns(2)
        with cA:
            label = "💾 Atualizar Prova" if st.session_state.modo_edicao else "🚀 Gerar Prova"
            if st.button(label, type="primary", use_container_width=True):
                if st.session_state.modo_edicao:
                    pid = st.session_state.prova_edicao_id
                    atualizar_prova(pid, cfg["materia"], cfg["titulo"],
                                    st.session_state.questoes_temp)
                    st.success(f"✅ Prova atualizada! ID: {pid}")
                else:
                    pid = salvar_prova(st.session_state.usuario_id, cfg["materia"],
                                       cfg["titulo"], st.session_state.questoes_temp)
                    st.success(f"✅ Prova criada! ID: {pid}")
                    st.session_state.ultimo_id = pid
                st.session_state.etapa_criacao  = 1
                st.session_state.questoes_temp  = []
                st.session_state.modo_edicao    = False
                st.session_state.prova_edicao_id = None
                st.rerun()
        with cB:
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state.etapa_criacao  = 1
                st.session_state.modo_edicao    = False
                st.session_state.prova_edicao_id = None
                st.rerun()

    if "ultimo_id" in st.session_state:
        pid  = st.session_state.ultimo_id
        link = f"http://localhost:8501?prova={pid}"
        st.markdown("### 🔗 Link para os alunos")
        st.code(link, language=None)
        st.info("📋 Envie esse link para seus alunos.")