"""
# Conteúdo legado de routing.py (antes da reorganização):
# params = st.query_params
# if "prova" in params:
#     prova_id = params["prova"]
#     inicialização de estados...
"""

from auth.aluno import render_auth_aluno
from auth.professor import render_auth_professor
from core.session import init_defaults
from core.utils import build_prova_link, render_copy_link_widget, render_student_protection
from eventos.rastreamento import processar_evento_query, registrar_evento
from professor.minhas_provas import render_minhas_provas
from professor.monitoramento import render_monitoramento
from professor.resultados import render_resultados
from prova.criacao_etapa1 import render_etapa1
from prova.criacao_etapa2 import render_etapa2
from prova.services import ProvaService
from prova.visualizacao import render_visualizacao_prova


def route_app(st):
    params = st.query_params

    if "prova" in params:
        prova_param = params["prova"]
        prova_id = prova_param[0] if isinstance(prova_param, list) else prova_param
        prova_id = str(prova_id).strip()
        init_defaults(st)
        if "evt" not in params:
            st.session_state.acesso_bloqueado = False
        processar_evento_query(st, prova_id, params)
        render_auth_aluno(st, prova_id, registrar_evento)
        render_visualizacao_prova(st, prova_id, ProvaService, registrar_evento)
        st.stop()

    if st.session_state.get("acesso_bloqueado"):
        st.error(
            "Acesso bloqueado: você saiu da aba da prova. "
            "Abra o mesmo link da prova novamente para entrar."
        )
        st.stop()

    render_student_protection(st, enabled=False)
    render_auth_professor(st)
    st.markdown("## Prova Fácil")
    st.caption(f"Bem-vindo, {st.session_state.usuario_nome}!")

    if st.sidebar.button("Sair", type="secondary"):
        del st.session_state.usuario_id
        del st.session_state.usuario_nome
        st.rerun()

    aba = st.sidebar.radio(
        "Navegação",
        ["Criar Prova", "Ver Resultados", "Minhas Provas", "Monitoramento"],
        key="aba_principal",
        label_visibility="collapsed",
    )

    init_defaults(st)
    if aba != "Criar Prova":
        st.session_state.mostrar_link_ultimo = False

    if aba == "Criar Prova":
        if st.session_state.etapa_criacao == 1:
            render_etapa1(st)
        else:
            render_etapa2(st)
        if st.session_state.get("mostrar_link_ultimo") and st.session_state.get("ultimo_id"):
            st.markdown("### Link da prova criada")
            link = build_prova_link(st.session_state.ultimo_id)
            render_copy_link_widget(st, link, key_suffix=f"novo_{st.session_state.ultimo_id}")
    elif aba == "Ver Resultados":
        render_resultados(st)
    elif aba == "Minhas Provas":
        render_minhas_provas(st)
    elif aba == "Monitoramento":
        render_monitoramento(st)
