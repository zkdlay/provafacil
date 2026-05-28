"""
# auth_aluno.py
# login local do aluno na prova
"""


def render_auth_aluno(st, prova_id, registrar_evento):
    if st.session_state.get("acesso_bloqueado"):
        st.error(
            "Acesso bloqueado por saída da aba durante a prova. "
            "Peça ao professor um novo link para entrar novamente."
        )
        st.stop()

    if st.session_state.aluno_logado:
        return

    st.title("Acesso à Prova")
    nome = st.text_input("Nome completo")
    numero = st.text_input("Número de chamada")

    if st.button("Acessar prova", type="primary"):
        if not nome.strip() or not numero.strip():
            st.warning("Preencha todos os campos.")
        else:
            registrar_evento(prova_id, nome.strip(), "login", f"Chamada: {numero.strip()}")
            st.session_state.aluno_logado = True
            st.session_state.acesso_bloqueado = False
            st.session_state.nome_aluno = nome.strip()
            st.session_state.numero_aluno = numero.strip()
            st.rerun()
    st.stop()
