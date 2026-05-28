


# ── MODO PROFESSOR — após login ───────────────────────────────────────────────
st.markdown("## 📝 Prova Fácil")
st.caption(f"Bem-vindo, {st.session_state.usuario_nome}!")

if st.sidebar.button("🚪 Sair", type="secondary"):
    del st.session_state.usuario_id
    del st.session_state.usuario_nome
    st.rerun()

aba = st.sidebar.radio(
    "Navegação",
    ["➕ Criar Prova", "📊 Ver Resultados", "📋 Minhas Provas", "🟢 Monitoramento"],
    label_visibility="collapsed"
)