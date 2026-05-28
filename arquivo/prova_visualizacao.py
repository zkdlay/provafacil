
    # ── CARREGAR PROVA ──
    prova = buscar_prova(prova_id)
    if not prova:
        st.error("Prova não encontrada.")
        st.stop()

    questoes = json.loads(prova["questoes"])
    st.title(prova["titulo"])
    st.caption(prova["materia"])



    # Bloquear reenvio
    nome_aluno = st.session_state.get("nome_aluno", "")
    if nome_aluno and aluno_ja_respondeu(prova_id, nome_aluno):
        st.error("⚠️ Você já enviou esta prova. Não é possível responder novamente.")
        respostas = buscar_respostas(prova_id)
        resp_aluno = next((r for r in respostas if r["nome_aluno"] == nome_aluno), None)
        if resp_aluno:
            st.write(f"**Nota:** {resp_aluno['nota']}/10")
            st.write(f"**Data:** {resp_aluno['respondida_em']}")
            st.session_state.prova_enviada   = True
            st.session_state.nota            = resp_aluno["nota"]
            st.session_state.respostas_final = json.loads(resp_aluno["respostas"])
            

    letras = ["A", "B", "C", "D", "E"]
    respostas_aluno = {}

    # Modo edição
    if not st.session_state.prova_enviada:
        for i, q in enumerate(questoes):
            st.markdown(f"### Questão {i+1}")
            st.write(q["enunciado"])
            if q.get("imagem"):
                st.image(f"data:image/png;base64,{q['imagem']}")
            op = st.radio(
                "Escolha:",
                options=letras[:len(q["opcoes"])],
                format_func=lambda x, q=q: f"{x}) {q['opcoes'][letras.index(x)]}",
                key=f"q_{i}",
                disabled=st.session_state.prova_enviada
            )
            respostas_aluno[f"q{i}"] = op
            st.divider()

        if st.button("📨 Enviar prova", type="primary"):
            if aluno_ja_respondeu(prova_id, nome_aluno):
                st.error("Prova já enviada anteriormente.")
                st.stop()
            nota = calcular_nota(questoes, respostas_aluno)
            salvar_resposta(prova_id, nome_aluno, respostas_aluno, nota)
            registrar_evento(prova_id, nome_aluno, "submit")
            st.success("Evento salvo no banco!")
            st.session_state.prova_enviada   = True
            st.session_state.nota            = nota
            st.session_state.respostas_final = respostas_aluno
            st.success("Prova enviada com sucesso!")
            st.rerun()
            

    # Modo resultado
    if st.session_state.prova_enviada:
        st.markdown("## 📊 Resultado")
        nota           = st.session_state.nota
        respostas_final = st.session_state.respostas_final
        acertos = sum(1 for i, q in enumerate(questoes)
                      if respostas_final.get(f"q{i}") == q["gabarito"])
        st.write(f"Nota: {nota}")
        st.write(f"Acertos: {acertos}/{len(questoes)}")
        with st.expander("📋 Ver gabarito completo"):
            for i, q in enumerate(questoes):
                sua     = respostas_final.get(f"q{i}", "—")
                correta = q["gabarito"]
                icone   = "✅" if sua == correta else "❌"
                texto_c = q["opcoes"][letras.index(correta)]
                st.write(f"{icone} **Q{i+1}**")
                st.write(f"📋 {q['enunciado']}")
                st.write(f"✓ Correta: **{correta}) {texto_c}**")
                if sua != correta:
                    st.write(f"✗ Sua resposta: {sua}")
                st.divider()

    st.stop()