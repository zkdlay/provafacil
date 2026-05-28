


# ── ABA: MINHAS PROVAS ────────────────────────────────────────────────────────
elif aba == "📋 Minhas Provas":
    st.subheader("📋 Provas criadas")
    provas = listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova criada ainda."); st.stop()

    materias = sorted(set(p["materia"] for p in provas))
    materias.insert(0, "Todas")
    mf = st.selectbox("📚 Filtrar por matéria", materias)
    if mf != "Todas":
        provas = [p for p in provas if p["materia"] == mf]

    for p in provas:
        questoes  = json.loads(p["questoes"])
        respostas = buscar_respostas(p["id"])
        with st.container():
            st.markdown(
                f"**{p['titulo']}**  \n"
                f"📚 {p['materia']} • {len(questoes)} questões • "
                f"{len(respostas)} resposta(s) • {p['criada_em']}"
            )
            c1, c2 = st.columns([0.5, 0.5])
            with c1:
                link = f"http://localhost:8501?prova={p['id']}"
                if st.button("🔗 Copiar Link", key=f"copy_{p['id']}", use_container_width=True):
                    st.code(link, language=None)
                    st.success("✅ Compartilhe com seus alunos.")
            with c2:
                if f"confirm_{p['id']}" not in st.session_state:
                    st.session_state[f"confirm_{p['id']}"] = False
                if not st.session_state[f"confirm_{p['id']}"]:
                    if st.button("🗑️ Deletar", key=f"del_{p['id']}", use_container_width=True):
                        st.session_state[f"confirm_{p['id']}"] = True
                        st.rerun()
                else:
                    st.warning("Tem certeza?")
                    cs, cn = st.columns(2)
                    with cs:
                        if st.button("✅ Deletar", key=f"yes_{p['id']}", use_container_width=True):
                            excluir_prova(p["id"]); st.success("Prova excluída!"); st.rerun()
                    with cn:
                        if st.button("❌ Cancelar", key=f"no_{p['id']}", use_container_width=True):
                            st.session_state[f"confirm_{p['id']}"] = False; st.rerun()
            st.divider()