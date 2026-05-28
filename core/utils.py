"""
import base64


class Utils:

    @staticmethod
    def file_to_base64(file):
"""

import base64
import html
import json


def file_to_base64(file):
    if not file:
        return None
    return base64.b64encode(file.read()).decode("utf-8")


def build_prova_link(prova_id, token=None):
    base = f"http://localhost:8501?prova={prova_id}"
    if token:
        return f"{base}&k={token}"
    return base


def render_copy_link_widget(st, link, key_suffix="default"):
    import streamlit.components.v1 as components

    safe_link = html.escape(link, quote=True)
    input_id = f"pf_link_{key_suffix}"
    msg_id = f"pf_msg_{key_suffix}"

    components.html(
        f"""
        <div style="display:flex; gap:8px; align-items:center;">
          <input
            id="{input_id}"
            value="{safe_link}"
            readonly
            style="flex:1; padding:8px; border:1px solid #ccc; border-radius:6px;"
          />
          <button
            style="padding:8px 12px; border-radius:6px; border:1px solid #999; cursor:pointer; background:#f5f5f5; color:#111;"
            onclick="
              navigator.clipboard.writeText(document.getElementById('{input_id}').value);
              const msg = document.getElementById('{msg_id}');
              msg.textContent = 'Copiado!';
              setTimeout(() => msg.textContent = '', 1500);
            "
          >
            Copiar link
          </button>
          <span id="{msg_id}" style="font-size:12px; color:green;"></span>
        </div>
        """,
        height=65,
    )


def render_student_protection(st, enabled=True):
    if enabled:
        st.markdown(
            """
            <style id="pf-no-select-inline">
              [data-testid="stAppViewContainer"] * {
                user-select: none !important;
                -webkit-user-select: none !important;
                -webkit-touch-callout: none !important;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style id="pf-no-select-inline">
              [data-testid="stAppViewContainer"] * {
                user-select: auto !important;
                -webkit-user-select: auto !important;
              }
            </style>
            """,
            unsafe_allow_html=True,
        )

    enabled_js = "true" if enabled else "false"
    script = """
        <script>
          const doc = window.parent.document;
          const enabled = __ENABLED__;

          if (!enabled) {
            if (doc.__provaFacilHandlers) {
              const h = doc.__provaFacilHandlers;
              doc.removeEventListener("copy", h.block, true);
              doc.removeEventListener("cut", h.block, true);
              doc.removeEventListener("paste", h.block, true);
              doc.removeEventListener("contextmenu", h.block, true);
              doc.removeEventListener("dragstart", h.block, true);
              doc.removeEventListener("selectstart", h.selectstart, true);
              doc.removeEventListener("keydown", h.keydown, true);
              window.removeEventListener("copy", h.block, true);
              window.removeEventListener("cut", h.block, true);
              window.removeEventListener("paste", h.block, true);
              window.removeEventListener("keydown", h.keydown, true);
              doc.__provaFacilHandlers = null;
            }
            const style = doc.getElementById("pf-no-select-style");
            if (style) style.remove();
            doc.__provaFacilLock = false;
            return;
          }

          if (!doc.__provaFacilLock) {
            doc.__provaFacilLock = true;

            const block = (e) => {
              e.preventDefault();
              e.stopPropagation();
              return false;
            };

            const onSelectStart = (e) => block(e);

            const onKeyDown = (e) => {
              const key = (e.key || "").toLowerCase();
              if ((e.ctrlKey || e.metaKey) && (key === "t" || key === "n")) {
                if (window.__pfEmitEvent) {
                  window.__pfEmitEvent("new_tab", `tentativa_bloqueada_${key}`);
                }
                block(e);
              }
              if ((e.ctrlKey || e.metaKey) && ["c", "x", "v", "a", "u", "s", "p"].includes(key)) {
                block(e);
              }
              if (key === "f12") {
                block(e);
              }
            };

            doc.addEventListener("copy", block, true);
            doc.addEventListener("cut", block, true);
            doc.addEventListener("paste", block, true);
            doc.addEventListener("contextmenu", block, true);
            doc.addEventListener("dragstart", block, true);
            doc.addEventListener("selectstart", onSelectStart, true);
            doc.addEventListener("keydown", onKeyDown, true);
            window.addEventListener("copy", block, true);
            window.addEventListener("cut", block, true);
            window.addEventListener("paste", block, true);
            window.addEventListener("keydown", onKeyDown, true);

            doc.__provaFacilHandlers = {
              block: block,
              selectstart: onSelectStart,
              keydown: onKeyDown
            };

            if (!doc.getElementById("pf-no-select-style")) {
              const style = doc.createElement("style");
              style.id = "pf-no-select-style";
              style.innerHTML = "html, body, body *{user-select:none !important;-webkit-user-select:none !important;}";
              doc.head.appendChild(style);
            }
          }
        </script>
        """
    st.html(
        script.replace("__ENABLED__", enabled_js),
        unsafe_allow_javascript=True,
    )


def render_exam_activity_tracker(st, prova_id, nome_aluno):
    payload = json.dumps({"prova_id": str(prova_id), "nome_aluno": str(nome_aluno or "")})
    st.html(
        f"""
        <script>
          (() => {{
            const cfg = {payload};
            if (!cfg.nome_aluno) return;

            const win = window.parent;
            const doc = win.document;
            const trackerKey = `pf_tracker_${{cfg.prova_id}}_${{cfg.nome_aluno}}`;
            const lastKey = `${{trackerKey}}_last`;
            const hiddenKey = `${{trackerKey}}_hidden`;
            const queueKey = `${{trackerKey}}_queue`;
            const flushingKey = `${{trackerKey}}_flushing`;
            let flushTimer = null;
            win[flushingKey] = false;

            if (!win.__pfTrackers) win.__pfTrackers = {{}};
            if (win.__pfTrackers[trackerKey]) {{
              const old = win.__pfTrackers[trackerKey];
              win.removeEventListener("blur", old.onBlur, true);
              win.removeEventListener("focus", old.onFocus, true);
              doc.removeEventListener("visibilitychange", old.onVisibilityChange, true);
              doc.removeEventListener("keydown", old.onKeyDown, true);
            }}

            const nowMs = () => Date.now();

            const canEmit = (evt) => {{
              try {{
                const raw = win.sessionStorage.getItem(lastKey);
                const last = raw ? JSON.parse(raw) : {{}};
                const now = nowMs();
                if (last.evt === evt && now - (last.ts || 0) < 900) return false;
                win.sessionStorage.setItem(lastKey, JSON.stringify({{ evt, ts: now }}));
                return true;
              }} catch (_) {{
                return true;
              }}
            }};

            const emitEvt = (evt, detalhe) => {{
              enqueueEvt(evt, detalhe);
              scheduleFlush(200);
            }};

            win.__pfEmitEvent = (evt, detalhe) => {{
              enqueueEvt(evt, detalhe || "manual");
              scheduleFlush(200);
            }};

            const readQueue = () => {{
              try {{
                const raw = win.sessionStorage.getItem(queueKey);
                return raw ? JSON.parse(raw) : [];
              }} catch (_) {{
                return [];
              }}
            }};

            const writeQueue = (q) => {{
              try {{
                win.sessionStorage.setItem(queueKey, JSON.stringify(q));
              }} catch (_) {{}}
            }};

            const enqueueEvt = (evt, detalhe) => {{
              if (!canEmit(evt)) return;
              const q = readQueue();
              q.push({{ evt, detalhe: `${{detalhe}}|${{nowMs()}}` }});
              writeQueue(q);
            }};

            const flushQueue = () => {{
              if (doc.visibilityState !== "visible") return;
              if (win[flushingKey]) return;
              const urlNow = new URL(win.location.href);
              if (urlNow.searchParams.get("evt")) return;
              const q = readQueue();
              if (!q.length) return;
              const next = q.shift();
              writeQueue(q);
              const url = new URL(win.location.href);
              url.searchParams.set("evt", next.evt);
              url.searchParams.set("det", next.detalhe);
              url.searchParams.set("evt_nome", cfg.nome_aluno);
              win[flushingKey] = true;
              win.location.replace(url.toString());
            }};

            const scheduleFlush = (ms = 250) => {{
              if (flushTimer) clearTimeout(flushTimer);
              flushTimer = setTimeout(() => {{
                flushQueue();
              }}, ms);
            }};

            const setHidden = (v) => {{
              try {{
                win.sessionStorage.setItem(hiddenKey, v ? "1" : "0");
              }} catch (_) {{}}
            }};

            const wasHidden = () => {{
              try {{
                return win.sessionStorage.getItem(hiddenKey) === "1";
              }} catch (_) {{
                return false;
              }}
            }};

            const onBlur = () => {{
              setHidden(true);
            }};

            const onFocus = () => {{
              if (!wasHidden()) return;
              setHidden(false);
              enqueueEvt("focus", "retornou_para_a_prova");
              scheduleFlush(100);
            }};

            const onVisibilityChange = () => {{
              if (doc.visibilityState === "hidden") {{
                setHidden(true);
                enqueueEvt("blur", "aba_oculta");
              }} else if (doc.visibilityState === "visible" && wasHidden()) {{
                setHidden(false);
                enqueueEvt("focus", "aba_visivel");
                scheduleFlush(100);
              }}
            }};

            const onKeyDown = (e) => {{
              const key = (e.key || "").toLowerCase();
              if ((e.ctrlKey || e.metaKey) && (key === "t" || key === "n")) {{
                e.preventDefault();
                e.stopPropagation();
                console.log("[PF_TRACK] tentativa nova aba por atalho", key);
                emitEvt("new_tab", `tentativa_atalho_${{key}}`);
              }}
            }};

            win.addEventListener("blur", onBlur, true);
            win.addEventListener("focus", onFocus, true);
            doc.addEventListener("visibilitychange", onVisibilityChange, true);
            doc.addEventListener("keydown", onKeyDown, true);

            win.__pfTrackers[trackerKey] = {{
              onBlur,
              onFocus,
              onVisibilityChange,
              onKeyDown,
            }};
            console.log("[PF_TRACK] tracker ativo", trackerKey);
          }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def render_tab_exit_lock(st, prova_id, nome_aluno):
    payload = json.dumps(
        {
            "prova_id": str(prova_id),
            "nome_aluno": str(nome_aluno or ""),
        }
    )
    st.html(
        f"""
        <script>
          (() => {{
            const cfg = {payload};
            const win = window.parent;
            const doc = win.document;
            const lockKey = `pf_lock_sent_${{cfg.prova_id}}_${{cfg.nome_aluno}}`;

            const sendLock = () => {{
              if (win.sessionStorage.getItem(lockKey) === "1") return;
              win.sessionStorage.setItem(lockKey, "1");
              const url = new URL(win.location.href);
              url.searchParams.set("evt", "blur");
              url.searchParams.set("det", "saiu_da_aba_bloqueio");
              url.searchParams.set("evt_nome", cfg.nome_aluno || "");
              win.location.replace(url.toString());
            }};

            const onVisibilityChange = () => {{
              if (doc.visibilityState === "hidden") {{
                sendLock();
              }}
            }};

            if (!win.__pfLockHandler) {{
              win.__pfLockHandler = onVisibilityChange;
              doc.addEventListener("visibilitychange", onVisibilityChange, true);
            }}
          }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
