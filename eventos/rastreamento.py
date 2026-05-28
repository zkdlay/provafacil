"""
# rastreamento.py
# PROCESSAR EVENTO ENVIADO PELO JS via query params
"""

from datetime import datetime as dt

from database.queries import Queries


def registrar_evento(prova_id, nome_aluno, evento, detalhe=""):
    timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(
        f"[EVENTO] ts={timestamp} prova={prova_id} aluno={nome_aluno} "
        f"evento={evento} detalhe={detalhe}",
        flush=True,
    )
    Queries.inserir_evento(prova_id, nome_aluno, evento, detalhe, timestamp)


def obter_eventos_prova(prova_id):
    return Queries.get_eventos_prova(prova_id)


def processar_evento_query(st, prova_id, params):
    evt_tipo = params.get("evt", None)
    if not evt_tipo:
        return

    evt_det = params.get("det", "")
    evt_nome = params.get("evt_nome") or st.session_state.get("nome_aluno", "")
    aluno_logado = bool(st.session_state.get("aluno_logado"))

    print(
        f"[QUERY_EVT] prova={prova_id} evt={evt_tipo} nome={evt_nome} "
        f"logado={aluno_logado} det={evt_det}",
        flush=True,
    )

    if evt_tipo == "blur":
        st.session_state.acesso_bloqueado = True
        st.session_state.aluno_logado = False

    if evt_nome and (aluno_logado or params.get("evt_nome")):
        registrar_evento(prova_id, evt_nome, evt_tipo, evt_det)
    else:
        print(
            f"[QUERY_EVT_IGNORADO] prova={prova_id} evt={evt_tipo} nome={evt_nome}",
            flush=True,
        )

    clean = {k: v for k, v in dict(params).items() if k not in ("evt", "det", "evt_nome")}
    if evt_tipo == "blur":
        st.query_params.clear()
    else:
        st.query_params.update(clean)
    st.rerun()
