"""
# Inicialização de estados espalhada em routing.py/prova_criacao_etapa1.py
"""


def init_defaults(st):
    defaults = {
        "aluno_logado": False,
        "prova_enviada": False,
        "nota": None,
        "respostas_final": {},
        "etapa_criacao": 1,
        "modo_edicao": False,
        "prova_edicao_id": None,
        "config_prova": {},
        "questoes_temp": [],
        "mostrar_link_ultimo": False,
        "acesso_bloqueado": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if isinstance(st.session_state.config_prova, dict):
        st.session_state.config_prova.setdefault("modo_questoes", "multipla_escolha")
