"""
# professor_minhas_provas.py
"""

import json
from collections import defaultdict

from core.utils import build_prova_link, render_copy_link_widget
from prova.services import ProvaService


def render_minhas_provas(st):
    st.subheader("Provas criadas")
    provas = ProvaService.listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova criada ainda.")
        st.stop()

    provas_por_materia = defaultdict(list)
    for p in provas:
        materia = (p.get("materia") or "Sem matéria").strip() or "Sem matéria"
        provas_por_materia[materia].append(p)

    for materia in sorted(provas_por_materia.keys()):
        bloco = provas_por_materia[materia]
        with st.expander(f"{materia} ({len(bloco)} prova(s))", expanded=True):
            for p in bloco:
                questoes = json.loads(p["questoes"])
                respostas = ProvaService.buscar_respostas(p["id"])
                st.markdown(
                    f"**{p['titulo']}**  \n"
                    f"{len(questoes)} questões - "
                    f"{len(respostas)} resposta(s) - {p['criada_em']}"
                )
                c1, c2 = st.columns(2)
                with c1:
                    link = build_prova_link(p["id"])
                    render_copy_link_widget(st, link, key_suffix=f"lista_{p['id']}")
                with c2:
                    if st.button("Deletar", key=f"del_{p['id']}", width="stretch"):
                        ProvaService.excluir_prova(p["id"])
                        st.rerun()
                st.divider()
