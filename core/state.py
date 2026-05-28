"""
# utilitários de reset de estado (novo)
"""


def reset_fluxo_criacao(st):
    st.session_state.etapa_criacao = 1
    st.session_state.questoes_temp = []
    st.session_state.modo_edicao = False
    st.session_state.prova_edicao_id = None
