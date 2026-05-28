


# ── ABA: VER RESULTADOS ───────────────────────────────────────────────────────
elif aba == "📊 Ver Resultados":
    st.subheader("📊 Resultados das Provas")
    provas = listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova criada ainda."); st.stop()

    op_provas = {f"{p['titulo']} ({p['materia']}) — {p['criada_em']}": p["id"] for p in provas}
    escolha   = st.selectbox("Selecione a prova", list(op_provas.keys()))
    pid       = op_provas[escolha]
    respostas = buscar_respostas(pid)
    prova     = buscar_prova(pid)
    questoes  = json.loads(prova["questoes"])

    if not respostas:
        st.warning("Nenhum aluno respondeu esta prova ainda."); st.stop()

    notas = [r["nota"] for r in respostas]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("👥 Alunos",      len(respostas))
    c2.metric("📈 Média",       f"{sum(notas)/len(notas):.1f}")
    c3.metric("🏆 Maior nota",  max(notas))
    c4.metric("📉 Menor nota",  min(notas))

    st.markdown("---"); st.markdown("### 📋 Lista de alunos")
    dados = []
    for r in respostas:
        resps   = json.loads(r["respostas"])
        acertos = sum(1 for i,q in enumerate(questoes) if resps.get(f"q{i}") == q["gabarito"])
        sit     = "✅ Aprovado" if r["nota"] >= 5 else "❌ Reprovado"
        alerta  = ""
        if r.get("tentativas_screenshot", 0) > 0:
            alerta = f"📸 {r['tentativas_screenshot']} tentativa(s)"
        if r.get("alertas_fraude"):
            alerta += f" | ⚠️ {r['alertas_fraude']}"
        dados.append({"Nome": r["nome_aluno"], "Nota": r["nota"],
                      "Acertos": f"{acertos}/{len(questoes)}",
                      "Situação": sit,
                      "Alertas": alerta or "✅ Sem alertas",
                      "Data/Hora": r["respondida_em"]})
    df = pd.DataFrame(dados)
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("🔍 Ver respostas detalhadas por aluno"):
        al = st.selectbox("Aluno", [r["nome_aluno"] for r in respostas])
        rs = next(r for r in respostas if r["nome_aluno"] == al)
        rr = json.loads(rs["respostas"])
        letras = ["A","B","C","D","E"]
        for i,q in enumerate(questoes):
            sua = rr.get(f"q{i}","—"); correta = q["gabarito"]
            ico = "✅" if sua == correta else "❌"
            st.markdown(f"{ico} **Q{i+1}:** {q['enunciado']}")
            st.caption(f"Resposta: **{sua}** | Correta: **{correta}**")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV", csv, "resultados.csv", "text/csv")