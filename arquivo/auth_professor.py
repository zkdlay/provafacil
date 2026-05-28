


# ── MODO PROFESSOR — login / registro ─────────────────────────────────────────
if "usuario_id" not in st.session_state:
    st.markdown("## 📝 Prova Fácil")
    st.caption("Sistema de provas online com correção automática")

    tab_login, tab_reg = st.tabs(["🔓 Login", "📝 Criar conta"])

    with tab_login:
        st.markdown("### Fazer Login")
        usuario = st.text_input("Nome de usuário", key="login_user")
        senha   = st.text_input("Senha", type="password", key="login_pass")
        if st.button("🔓 Entrar", type="primary", use_container_width=True):
            if not usuario or not senha:
                st.warning("Preencha usuário e senha.")
            else:
                ok, uid = verificar_login(usuario, senha)
                if ok:
                    st.session_state.usuario_id   = uid
                    st.session_state.usuario_nome = usuario
                    st.success("✅ Login realizado!"); st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")

    with tab_reg:
        st.markdown("### Criar nova conta")
        nu  = st.text_input("Nome de usuário", key="reg_user")
        ns  = st.text_input("Senha",           type="password", key="reg_pass")
        nc  = st.text_input("Confirmar senha", type="password", key="reg_pass_conf")
        if st.button("📝 Criar conta", type="primary", use_container_width=True):
            if not nu or not ns:
                st.warning("Preencha todos os campos.")
            elif len(ns) < 4:
                st.warning("Senha mínima de 4 caracteres.")
            elif ns != nc:
                st.warning("As senhas não conferem.")
            else:
                ok, msg = registrar_professor(nu, ns)
                (st.success if ok else st.error)(msg)
    st.stop()