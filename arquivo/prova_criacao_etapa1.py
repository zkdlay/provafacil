# ── ABA: CRIAR PROVA ──────────────────────────────────────────────────────────
if aba == "➕ Criar Prova":
    for k, v in [("etapa_criacao",1),("modo_edicao",False),
                  ("prova_edicao_id",None),("config_prova",{}),("questoes_temp",[])]:
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.modo_edicao and st.session_state.prova_edicao_id:
        pe = buscar_prova(st.session_state.prova_edicao_id)
        if pe:
            qo = json.loads(pe["questoes"])
            st.session_state.config_prova = {
                "materia": pe["materia"], "titulo": pe["titulo"],
                "qtd_questoes": len(qo),
                "qtd_opcoes": len(qo[0]["opcoes"]) if qo else 5
            }
            st.session_state.questoes_temp  = qo
            st.session_state.etapa_criacao  = 2

    # ETAPA 1
    if st.session_state.etapa_criacao == 1:
        st.subheader("✏️ Editar prova" if st.session_state.modo_edicao else "➕ Criar nova prova")
        col1, col2 = st.columns(2)
        with col1:
            padrao = ["Matemática","Ciências","Física","Química","Biologia",
                      "Português","História","Geografia","Inglês"]
            if "materias_custom" not in st.session_state:
                st.session_state.materias_custom = []
            todas = padrao + st.session_state.materias_custom + ["Outra"]
            mat_sel = st.selectbox("📚 Matéria", todas)
            if mat_sel == "Outra":
                mc = st.text_input("Digite a matéria")
                materia = mc.strip()
            else:
                materia = mat_sel
        with col2:
            titulo = st.text_input("🏷️ Título da prova")
        col3, col4 = st.columns(2)
        with col3:
            qtd_q = st.number_input("❓ Quantas questões?", 1, 50, 5)
        with col4:
            qtd_op = st.number_input("🔘 Quantas alternativas?", 2, 5, 4)

        if st.button("➡️ Próximo", type="primary"):
            if not titulo.strip():
                st.warning("Digite um título.")
            elif not materia:
                st.warning("Digite a matéria.")
            else:
                mn = materia.strip()
                if mn not in padrao and mn not in st.session_state.materias_custom:
                    st.session_state.materias_custom.append(mn)
                st.session_state.config_prova  = {"materia": mn, "titulo": titulo,
                                                   "qtd_questoes": qtd_q, "qtd_opcoes": qtd_op}
                st.session_state.questoes_temp = [{} for _ in range(qtd_q)]
                st.session_state.etapa_criacao = 2
                st.rerun()