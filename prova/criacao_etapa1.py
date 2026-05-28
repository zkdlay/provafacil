"""
# prova_criacao_etapa1.py
"""

from core.constants import MATERIAS_PADRAO


def render_etapa1(st):
    st.subheader("Criar nova prova")
    col1, col2 = st.columns(2)
    with col1:
        if "materias_custom" not in st.session_state:
            st.session_state.materias_custom = []
        todas = MATERIAS_PADRAO + st.session_state.materias_custom + ["Outra"]
        mat_sel = st.selectbox("Matéria", todas)
        materia = st.text_input("Digite a matéria") if mat_sel == "Outra" else mat_sel
    with col2:
        titulo = st.text_input("Título da prova")

    qtd_q = st.number_input("Quantas questões?", 1, 50, 5)
    modo_questoes = st.selectbox(
        "Tipo de prova",
        ["multipla_escolha", "texto", "misto"],
        format_func=lambda x: {
            "multipla_escolha": "Somente múltipla escolha",
            "texto": "Somente resposta digitada",
            "misto": "Misto (os dois tipos)",
        }[x],
    )

    qtd_op = None
    if modo_questoes in ("multipla_escolha", "misto"):
        qtd_op = st.number_input("Quantas alternativas?", 2, 5, 4)

    if st.button("Próximo", type="primary"):
        if not titulo.strip():
            st.warning("Digite um título.")
            return
        if not materia:
            st.warning("Digite a matéria.")
            return
        mn = materia.strip()
        if mn not in MATERIAS_PADRAO and mn not in st.session_state.materias_custom:
            st.session_state.materias_custom.append(mn)
        config = {
            "materia": mn,
            "titulo": titulo,
            "qtd_questoes": qtd_q,
            "modo_questoes": modo_questoes,
        }
        if modo_questoes in ("multipla_escolha", "misto"):
            config["qtd_opcoes"] = qtd_op
        st.session_state.config_prova = config
        st.session_state.questoes_temp = [{} for _ in range(qtd_q)]
        st.session_state.mostrar_link_ultimo = False
        st.session_state.etapa_criacao = 2
        st.rerun()
