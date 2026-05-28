"""
# prova_criacao_etapa2.py
"""

from core.constants import LETRAS_OPCOES
from core.state import reset_fluxo_criacao
from core.utils import file_to_base64
from prova.services import ProvaService


def render_etapa2(st):
    cfg = st.session_state.config_prova
    modo_questoes = cfg.get("modo_questoes", "multipla_escolha")
    qtd_opcoes = cfg.get("qtd_opcoes", 4)
    st.subheader(cfg["titulo"])
    st.caption(f"{cfg['materia']} - {cfg['qtd_questoes']} questões")

    for i in range(cfg["qtd_questoes"]):
        with st.expander(f"Questão {i+1}", expanded=(i == 0)):
            enunciado = st.text_area("Enunciado", key=f"en_{i}")
            if modo_questoes == "misto":
                tipo = st.selectbox(
                    "Tipo de questão",
                    ["multipla_escolha", "texto"],
                    format_func=lambda x: "Múltipla escolha" if x == "multipla_escolha" else "Resposta digitada",
                    key=f"tipo_{i}",
                )
            elif modo_questoes == "texto":
                tipo = "texto"
                st.caption("Tipo: Resposta digitada")
            else:
                tipo = "multipla_escolha"
                st.caption("Tipo: Múltipla escolha")
            img_q = st.file_uploader(
                "Imagem da questão (opcional)", type=["png", "jpg", "jpeg"], key=f"iq_{i}"
            )

            if tipo == "multipla_escolha":
                opcoes = []
                imgs_op = []
                for j in range(qtd_opcoes):
                    c1, c2 = st.columns([0.7, 0.3])
                    with c1:
                        opcoes.append(st.text_input(LETRAS_OPCOES[j], key=f"op_{i}_{j}"))
                    with c2:
                        imgs_op.append(
                            st.file_uploader(
                                f"Img {LETRAS_OPCOES[j]}",
                                type=["png", "jpg", "jpeg"],
                                key=f"iop_{i}_{j}",
                            )
                        )
                gabarito = st.selectbox(
                    "Resposta correta", LETRAS_OPCOES[: qtd_opcoes], key=f"gab_{i}"
                )
                st.session_state.questoes_temp[i] = {
                    "tipo": "multipla_escolha",
                    "enunciado": enunciado,
                    "imagem": file_to_base64(img_q),
                    "opcoes": opcoes,
                    "imagens_opcoes": [file_to_base64(f) for f in imgs_op],
                    "gabarito": gabarito,
                }
            else:
                gabarito_texto = st.text_input(
                    "Resposta correta (gabarito textual)", key=f"gab_texto_{i}"
                )
                st.session_state.questoes_temp[i] = {
                    "tipo": "texto",
                    "enunciado": enunciado,
                    "imagem": file_to_base64(img_q),
                    "opcoes": [],
                    "imagens_opcoes": [],
                    "gabarito_texto": gabarito_texto,
                }

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Gerar Prova", type="primary", width="stretch"):
            pid = ProvaService.salvar_prova(
                st.session_state.usuario_id,
                cfg["materia"],
                cfg["titulo"],
                st.session_state.questoes_temp,
            )
            st.session_state.ultimo_id = pid
            st.session_state.mostrar_link_ultimo = True
            reset_fluxo_criacao(st)
            st.rerun()
    with c2:
        if st.button("Voltar", width="stretch"):
            st.session_state.etapa_criacao = 1
            st.rerun()
