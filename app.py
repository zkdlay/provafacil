import streamlit as st
import sqlite3
import json
import uuid
from datetime import datetime
import pandas as pd
import hashlib

st.set_page_config(
    page_title="ProvaFácil",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS global ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Anti-cópia nas questões */
.questao-texto {
    user-select: none !important;
    -webkit-user-select: none !important;
    -moz-user-select: none !important;
}
.stApp { background-color: #f8f9fa; }
.bloco-questao {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid #e0e0e0;
    border-left: 5px solid #7C3AED;
}
.header-prova {
    background: linear-gradient(135deg, #7C3AED, #9F67FA);
    color: white;
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
}
.badge-materia {
    background: rgba(255,255,255,0.25);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 13px;
    display: inline-block;
    margin-bottom: 8px;
}
.login-container {
    max-width: 400px;
    margin: 50px auto;
    padding: 2rem;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Filigrana (watermark) */
.watermark {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 9998;
    font-size: 24px;
    font-weight: bold;
    color: rgba(200, 50, 50, 0.08);
    transform: rotate(-45deg);
    line-height: 40px;
    overflow: hidden;
    word-wrap: break-word;
    white-space: pre-wrap;
}
</style>

<script>
// ── ANTI-FRAUDE RIGOROSO ──
// 0. Adiciona filigrana (watermark) com nome do aluno
function adicionarFicha(nomeAluno) {
    var watermark = document.createElement('div');
    watermark.className = 'watermark';
    var texto = '';
    for (var i = 0; i < 20; i++) {
        texto += nomeAluno + ' - ';
    }
    watermark.textContent = texto;
    document.body.appendChild(watermark);
}

// Aguarda o nome ser digitado e aplica a filigrana
var observer = new MutationObserver(function(mutations) {
    var inputs = document.querySelectorAll('input[placeholder*="nome"]');
    if (inputs.length > 0) {
        inputs[0].addEventListener('input', function(e) {
            if (e.target.value.trim().length > 0) {
                var old = document.querySelector('.watermark');
                if (old) old.remove();
                adicionarFicha(e.target.value.trim());
            }
        });
    }
});
observer.observe(document.body, { childList: true, subtree: true });

// 1. Bloqueia copiar/colar/clicar direito
document.addEventListener('copy', function(e) {
    var sel = window.getSelection();
    if (sel && sel.toString().length > 0) {
        var masked = '#'.repeat(sel.toString().length);
        e.clipboardData.setData('text/plain', masked);
        e.clipboardData.setData('text/html', masked);
        e.preventDefault();
    }
});
document.addEventListener('contextmenu', function(e){ e.preventDefault(); });

// 2. Bloqueia atalhos perigosos (Ctrl+C, Ctrl+A, Ctrl+U, F12, DevTools, etc)
document.addEventListener('keydown', function(e){
    // Ctrl/Cmd + C, A, U, S, V, X (cópia, seleção, source, save, paste, cut)
    if ((e.ctrlKey||e.metaKey) && ['c','a','u','s','v','x'].includes(e.key.toLowerCase())) {
        e.preventDefault();
    }
    // F12 (DevTools)
    if (e.key === 'F12') {
        e.preventDefault();
    }
    // Ctrl+Shift+I, J, C (DevTools)
    if ((e.ctrlKey||e.metaKey) && e.shiftKey && ['i','j','c'].includes(e.key.toLowerCase())) {
        e.preventDefault();
    }
    // Print Screen
    if (e.key === 'PrintScreen') {
        e.preventDefault();
        detectarScreenshot('PrintScreen');
    }
});

// 2.5 Detecta Shift+Windows+S (Windows 11 screenshot tool)
document.addEventListener('keydown', function(e){
    if ((e.shiftKey && e.key === 'S') || (e.shiftKey && e.code === 'KeyS')) {
        // Pode ser screenshot no Windows
        setTimeout(function() {
            detectarScreenshot('Windows Screenshot Tool');
        }, 100);
    }
});

// 3. Detecta se a aba perdeu o foco (alt-tab, clique em outra aba, etc)
var focoPerdido = false;
var tentativasSaida = 0;
var maxTentativas = 2;

window.addEventListener('blur', function() {
    focoPerdido = true;
    tentativasSaida++;
    console.warn('Atenção: Você saiu da janela da prova!');
    
    if (tentativasSaida > maxTentativas) {
        // Tenta fechar a aba
        window.close();
        // Se não conseguir (maioria dos navegadores), avisa
        alert('⚠️ FRAUDE DETECTADA: Você tentou sair da prova múltiplas vezes. Sua prova será zerada!');
        // Marca no sessionStorage para o servidor saber
        sessionStorage.setItem('prova_fraudada', 'true');
    }
});

window.addEventListener('focus', function() {
    if (focoPerdido) {
        alert('⚠️ Aviso: Você só pode responder a prova nesta aba. Acessar outras abas resultará em nota 0.');
        focoPerdido = false;
    }
});

// 4. Tira fullscreen se o aluno tentar entrar
document.addEventListener('fullscreenchange', function() {
    if (document.fullscreenElement) {
        document.exitFullscreen();
    }
});

// 5. Detecta abertura de DevTools (monitor de resize)
var devtoolsOpen = false;
var threshold = 160;
var checkDevTools = setInterval(function() {
    if (window.outerHeight - window.innerHeight > threshold ||
        window.outerWidth - window.innerWidth > threshold) {
        if (!devtoolsOpen) {
            devtoolsOpen = true;
            alert('❌ DevTools detectado! A prova será encerrada.');
            sessionStorage.setItem('prova_fraudada', 'true');
            window.close();
        }
    }
});

// 6. Bloqueia arrastar/soltar
document.addEventListener('dragstart', function(e) { e.preventDefault(); });
document.addEventListener('drop', function(e) { e.preventDefault(); });

// 7. Bloqueia seleção de texto (duplo clique)
document.addEventListener('selectstart', function(e) { e.preventDefault(); });

// 8. Previne que saiam sem confirmação
window.addEventListener('beforeunload', function(e) {
    if (!sessionStorage.getItem('prova_enviada')) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});

// 9. DETECÇÃO DE SCREENSHOT
function detectarScreenshot(metodo) {
    alert('⚠️ CAPTURA DE TELA DETECTADA!\n\nMétodo: ' + metodo + '\n\nEsta tentativa foi registrada e seu professor será notificado.');
    // Envia para o servidor via fetch
    fetch(window.location.href, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            acao: 'screenshot_detectado',
            metodo: metodo,
            timestamp: new Date().toISOString()
        })
    }).catch(function(e) {
        console.log('Screenshot detectado:', metodo);
    });
}

// Tenta detectar via API moderna (Chrome/Edge)
if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
    document.addEventListener('visibilitychange', function() {
        if (document.hidden === false && document.wasHidden === true) {
            detectarScreenshot('Display Capture API');
        }
        document.wasHidden = document.hidden;
    });
}
</script>
""", unsafe_allow_html=True)

# ── Banco de dados ───────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect("provas.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    
    # Tabela de usuários (professores)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT,
            criado_em TEXT
        )
    """)
    
    # Tabela de provas (agora com usuario_id)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS provas (
            id TEXT PRIMARY KEY,
            usuario_id INTEGER,
            materia TEXT,
            titulo TEXT,
            questoes TEXT,
            criada_em TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)
    
    # Tabela de respostas dos alunos
    conn.execute("""
        CREATE TABLE IF NOT EXISTS respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prova_id TEXT,
            nome_aluno TEXT,
            respostas TEXT,
            nota REAL,
            respondida_em TEXT,
            tentativas_screenshot INTEGER DEFAULT 0,
            alertas_fraude TEXT,
            FOREIGN KEY(prova_id) REFERENCES provas(id)
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# ── Funções de autenticação ──────────────────────────────────────────────────
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def registrar_professor(usuario, senha):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO usuarios (usuario, senha, criado_em) VALUES (?,?,?)",
            (usuario, hash_senha(senha), datetime.now().strftime("%d/%m/%Y %H:%M"))
        )
        conn.commit()
        conn.close()
        return True, "✅ Cadastro realizado com sucesso!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "❌ Este usuário já existe. Escolha outro nome."
    except Exception as e:
        conn.close()
        return False, f"❌ Erro: {str(e)}"

def verificar_login(usuario, senha):
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM usuarios WHERE usuario=? AND senha=?",
        (usuario, hash_senha(senha))
    ).fetchone()
    conn.close()
    if row:
        return True, row["id"]
    return False, None

# ── Helpers de prova ─────────────────────────────────────────────────────────
def salvar_prova(usuario_id, materia, titulo, questoes):
    prova_id = str(uuid.uuid4())[:8]
    conn = get_conn()
    conn.execute(
        "INSERT INTO provas (id, usuario_id, materia, titulo, questoes, criada_em) VALUES (?,?,?,?,?,?)",
        (prova_id, usuario_id, materia, titulo, json.dumps(questoes, ensure_ascii=False),
         datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()
    return prova_id

def buscar_prova(prova_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM provas WHERE id=?", (prova_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def listar_provas(usuario_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM provas WHERE usuario_id=? ORDER BY criada_em DESC",
        (usuario_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def salvar_resposta(prova_id, nome_aluno, respostas_aluno, nota):
    conn = get_conn()
    conn.execute(
        "INSERT INTO respostas (prova_id, nome_aluno, respostas, nota, respondida_em) VALUES (?,?,?,?,?)",
        (prova_id, nome_aluno, json.dumps(respostas_aluno, ensure_ascii=False),
         nota, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()

def buscar_respostas(prova_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM respostas WHERE prova_id=? ORDER BY respondida_em DESC",
        (prova_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def calcular_nota(questoes, respostas_aluno):
    total = len(questoes)
    acertos = 0
    for i, q in enumerate(questoes):
        chave = f"q{i}"
        if respostas_aluno.get(chave) == q["gabarito"]:
            acertos += 1
    return round((acertos / total) * 10, 1) if total > 0 else 0

def salvar_resposta_fraude(prova_id, nome_aluno):
    """Registra nota 0 para aluno que tentou fraude"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO respostas (prova_id, nome_aluno, respostas, nota, respondida_em) VALUES (?,?,?,?,?)",
        (prova_id, nome_aluno, json.dumps({"fraude": "múltiplas abas detectadas"}), 
         0.0, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()
    conn.close()

# ── Roteamento por query param ────────────────────────────────────────────────
params = st.query_params
prova_id_url = params.get("prova", None)

# ── MODO ALUNO (respondendo prova) ────────────────────────────────────────────
if prova_id_url:
    prova = buscar_prova(prova_id_url)

    if not prova:
        st.error("❌ Prova não encontrada. Verifique o link com seu professor.")
        st.stop()

    questoes = json.loads(prova["questoes"])

    st.markdown(f"""
    <div class="header-prova">
        <div class="badge-materia">📚 {prova['materia']}</div>
        <h1 style="margin:0;font-size:1.8rem">{prova['titulo']}</h1>
        <p style="margin:4px 0 0;opacity:0.85">{len(questoes)} questão(ões) • Múltipla escolha</p>
    </div>
    """, unsafe_allow_html=True)

    st.error("""
    🛡️ **PROTEÇÃO ANTI-FRAUDE ATIVA**
    
    ❌ **PROIBIDO:**
    - Abrir outra aba do navegador = **Nota 0**
    - Usar Alt+Tab = **Nota 0**
    - Copiar e colar = **Bloqueado** (retorna `###########`)
    - Acessar Console/DevTools = **Nota 0**
    - Clicar com botão direito = **Bloqueado**
    - Maximizar tela (fullscreen) = **Bloqueado**
    - **Tirar screenshot = Registrado e notificado ao professor**
    
    📸 **FILIGRANA ATIVA:** Seu nome aparecerá em qualquer screenshot tirado
    
    ✅ Responda apenas nesta aba!
    """)

    nome_aluno = st.text_input("👤 Seu nome completo", placeholder="Digite seu nome antes de começar...")

    respostas_aluno = {}
    todas_respondidas = True

    for i, q in enumerate(questoes):
        st.markdown(f"""
        <div class="bloco-questao">
            <p style="font-size:12px;color:#7C3AED;font-weight:600;margin:0 0 6px">QUESTÃO {i+1}</p>
            <p class="questao-texto" style="font-size:16px;font-weight:500;color:#1a1a1a;margin:0">
                {q['enunciado']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        opcoes = q["opcoes"]
        letras = ["A", "B", "C", "D", "E"]
        opcoes_exibicao = [f"{letras[j]}) {opcoes[j]}" for j in range(len(opcoes))]

        escolha = st.radio(
            f"Resposta da questão {i+1}",
            options=opcoes_exibicao,
            index=None,
            key=f"radio_{i}",
            label_visibility="collapsed"
        )

        if escolha:
            letra_escolhida = escolha[0]
            respostas_aluno[f"q{i}"] = letra_escolhida
        else:
            todas_respondidas = False

    st.markdown("---")

    if st.button("📨 Enviar Prova", type="primary", use_container_width=True):
        if not nome_aluno.strip():
            st.warning("Por favor, insira seu nome antes de enviar.")
        elif not todas_respondidas:
            st.warning("Responda todas as questões antes de enviar.")
        else:
            nota = calcular_nota(questoes, respostas_aluno)
            salvar_resposta(prova_id_url, nome_aluno.strip(), respostas_aluno, nota)

            st.balloons()
            cor = "#16a34a" if nota >= 7 else "#d97706" if nota >= 5 else "#dc2626"
            emoji = "🏆" if nota >= 7 else "📖" if nota >= 5 else "💪"

            acertos = sum(
                1 for i, q in enumerate(questoes)
                if respostas_aluno.get(f"q{i}") == q["gabarito"]
            )

            st.markdown(f"""
            <div style="background:white;border-radius:16px;padding:2.5rem;text-align:center;
                        border:2px solid {cor};margin-top:1rem">
                <div style="font-size:3rem">{emoji}</div>
                <h2 style="color:{cor};font-size:2.5rem;margin:0.5rem 0">{nota}</h2>
                <p style="color:#555;font-size:1.1rem">
                    Você acertou <strong>{acertos} de {len(questoes)}</strong> questões
                </p>
                <p style="color:#888;font-size:14px">Prova enviada com sucesso, {nome_aluno}!</p>
            </div>
            """, unsafe_allow_html=True)

            # Mostrar gabarito
            with st.expander("📋 Ver gabarito"):
                letras = ["A", "B", "C", "D", "E"]
                for i, q in enumerate(questoes):
                    sua = respostas_aluno.get(f"q{i}", "—")
                    correta = q["gabarito"]
                    acertou = sua == correta
                    icone = "✅" if acertou else "❌"
                    st.markdown(f"""
                    **{icone} Questão {i+1}:** {q['enunciado']}
                    - Sua resposta: **{sua}**  |  Correta: **{correta}**
                    """)

    st.stop()

# ── MODO PROFESSOR (login/registro) ──────────────────────────────────────────
if "usuario_id" not in st.session_state:
    st.markdown("## 📝 ProvaFácil")
    st.caption("Sistema de provas online com correção automática")
    
    tab_login, tab_registro = st.tabs(["🔓 Login", "📝 Criar conta"])
    
    with tab_login:
        st.markdown("### Fazer Login")
        usuario = st.text_input("Nome de usuário", placeholder="seu_usuario", key="login_user")
        senha = st.text_input("Senha", type="password", placeholder="sua_senha", key="login_pass")
        
        if st.button("🔓 Entrar", type="primary", use_container_width=True):
            if not usuario or not senha:
                st.warning("Preencha usuário e senha.")
            else:
                sucesso, usuario_id = verificar_login(usuario, senha)
                if sucesso:
                    st.session_state.usuario_id = usuario_id
                    st.session_state.usuario_nome = usuario
                    st.success("✅ Login realizado!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
    
    with tab_registro:
        st.markdown("### Criar nova conta")
        novo_usuario = st.text_input("Nome de usuário", placeholder="escolha_um_nome", key="reg_user")
        nova_senha = st.text_input("Senha", type="password", placeholder="crie_uma_senha", key="reg_pass")
        nova_senha_conf = st.text_input("Confirmar senha", type="password", placeholder="repita_a_senha", key="reg_pass_conf")
        
        if st.button("📝 Criar conta", type="primary", use_container_width=True):
            if not novo_usuario or not nova_senha:
                st.warning("Preencha todos os campos.")
            elif len(nova_senha) < 4:
                st.warning("A senha deve ter pelo menos 4 caracteres.")
            elif nova_senha != nova_senha_conf:
                st.warning("As senhas não conferem.")
            else:
                sucesso, msg = registrar_professor(novo_usuario, nova_senha)
                if sucesso:
                    st.success(msg)
                    st.info("Agora você pode fazer login com suas credenciais!")
                else:
                    st.error(msg)
    
    st.stop()

# ── MODO PROFESSOR (após login) ──────────────────────────────────────────────
st.markdown(f"## 📝 ProvaFácil")
st.caption(f"Bem-vindo, {st.session_state.usuario_nome}!")

# Botão de logout
if st.sidebar.button("🚪 Sair", type="secondary"):
    del st.session_state.usuario_id
    del st.session_state.usuario_nome
    st.rerun()

aba = st.sidebar.radio(
    "Navegação",
    ["➕ Criar Prova", "📊 Ver Resultados", "📋 Minhas Provas"],
    label_visibility="collapsed"
)

# ── ABA: CRIAR PROVA ──────────────────────────────────────────────────────────
if aba == "➕ Criar Prova":
    st.subheader("➕ Criar nova prova")

    col1, col2 = st.columns(2)
    with col1:
        materia = st.selectbox("📚 Matéria", [
            "Matemática", "Ciências", "Física", "Química", "Biologia",
            "Português", "História", "Geografia", "Inglês", "Outra"
        ])
    with col2:
        titulo = st.text_input("🏷️ Título da prova", placeholder="Ex: Prova Bimestral - Funções")

    st.markdown("---")
    st.markdown("### 📝 Questões")

    if "questoes_temp" not in st.session_state:
        st.session_state.questoes_temp = []

    # Adicionar questão
    with st.expander("➕ Adicionar questão", expanded=len(st.session_state.questoes_temp) == 0):
        enunciado = st.text_area("Enunciado da questão", placeholder="Digite o enunciado...", key="novo_enunciado")

        st.markdown("**Opções de resposta:**")
        letras = ["A", "B", "C", "D", "E"]
        opcoes_novas = []
        cols = st.columns(2)
        for j, letra in enumerate(letras):
            with cols[j % 2]:
                op = st.text_input(f"Opção {letra}", key=f"op_{j}", placeholder=f"Texto da opção {letra}")
                opcoes_novas.append(op)

        opcoes_validas = [o for o in opcoes_novas if o.strip()]
        letras_validas = letras[:len(opcoes_validas)]

        gabarito = st.selectbox(
            "✅ Resposta correta",
            letras_validas if opcoes_validas else ["—"],
            key="gabarito_sel"
        )

        if st.button("Adicionar questão ✚", type="secondary"):
            if not enunciado.strip():
                st.warning("Digite o enunciado da questão.")
            elif len(opcoes_validas) < 2:
                st.warning("Adicione pelo menos 2 opções.")
            elif gabarito == "—":
                st.warning("Selecione a resposta correta.")
            else:
                st.session_state.questoes_temp.append({
                    "enunciado": enunciado.strip(),
                    "opcoes": opcoes_validas,
                    "gabarito": gabarito
                })
                st.success(f"✅ Questão {len(st.session_state.questoes_temp)} adicionada!")
                st.rerun()

    # Listar questões adicionadas
    if st.session_state.questoes_temp:
        st.markdown(f"**{len(st.session_state.questoes_temp)} questão(ões) adicionada(s):**")
        for i, q in enumerate(st.session_state.questoes_temp):
            with st.container():
                cols = st.columns([0.85, 0.15])
                with cols[0]:
                    letras = ["A", "B", "C", "D", "E"]
                    opcoes_str = " | ".join([
                        f"**{letras[j]}✓**" if letras[j] == q["gabarito"] else letras[j]
                        for j in range(len(q["opcoes"]))
                    ])
                    st.markdown(f"**Q{i+1}.** {q['enunciado']}  \n{opcoes_str}")
                with cols[1]:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.questoes_temp.pop(i)
                        st.rerun()
                st.divider()

        st.markdown("---")
        colA, colB = st.columns(2)
        with colA:
            if st.button("🚀 Gerar Prova e Link", type="primary", use_container_width=True):
                if not titulo.strip():
                    st.warning("Dê um título para a prova.")
                else:
                    prova_id = salvar_prova(st.session_state.usuario_id, materia, titulo.strip(), st.session_state.questoes_temp)
                    st.session_state.questoes_temp = []
                    st.session_state.ultimo_id = prova_id
                    st.success(f"✅ Prova criada com sucesso! ID: `{prova_id}`")
                    st.rerun()
        with colB:
            if st.button("🗑️ Limpar tudo", use_container_width=True):
                st.session_state.questoes_temp = []
                st.rerun()

    if "ultimo_id" in st.session_state:
        pid = st.session_state.ultimo_id
        link = f"https://provafacil.streamlit.app/?prova={pid}"
        st.markdown("### 🔗 Link para os alunos")
        st.code(link, language=None)
        st.info("📋 Copie esse link e envie para seus alunos pelo WhatsApp, e-mail ou grupo da turma.")

# ── ABA: VER RESULTADOS ───────────────────────────────────────────────────────
elif aba == "📊 Ver Resultados":
    st.subheader("📊 Resultados das Provas")

    provas = listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova criada ainda.")
        st.stop()

    opcoes_provas = {f"{p['titulo']} ({p['materia']}) — {p['criada_em']}": p["id"] for p in provas}
    escolha = st.selectbox("Selecione a prova", list(opcoes_provas.keys()))
    pid = opcoes_provas[escolha]

    respostas = buscar_respostas(pid)
    prova = buscar_prova(pid)
    questoes = json.loads(prova["questoes"])

    if not respostas:
        st.warning("Nenhum aluno respondeu esta prova ainda.")
        st.stop()

    # Métricas
    notas = [r["nota"] for r in respostas]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Alunos", len(respostas))
    col2.metric("📈 Média", f"{sum(notas)/len(notas):.1f}")
    col3.metric("🏆 Maior nota", max(notas))
    col4.metric("📉 Menor nota", min(notas))

    st.markdown("---")
    st.markdown("### 📋 Lista de alunos")

    dados = []
    for r in respostas:
        resps = json.loads(r["respostas"])
        acertos = sum(1 for i, q in enumerate(questoes) if resps.get(f"q{i}") == q["gabarito"])
        situacao = "✅ Aprovado" if r["nota"] >= 5 else "❌ Reprovado"
        
        # Verifica se teve tentativas de screenshot
        alerta = ""
        if r.get("tentativas_screenshot", 0) > 0:
            alerta = f"📸 {r['tentativas_screenshot']} tentativa(s) de screenshot"
        if r.get("alertas_fraude"):
            alerta += f" | ⚠️ {r['alertas_fraude']}"
        
        dados.append({
            "Nome": r["nome_aluno"],
            "Nota": r["nota"],
            "Acertos": f"{acertos}/{len(questoes)}",
            "Situação": situacao,
            "Alertas": alerta if alerta else "✅ Sem alertas",
            "Data/Hora": r["respondida_em"]
        })

    df = pd.DataFrame(dados)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detalhes por aluno
    with st.expander("🔍 Ver respostas detalhadas por aluno"):
        aluno_sel = st.selectbox("Aluno", [r["nome_aluno"] for r in respostas])
        resp_sel = next(r for r in respostas if r["nome_aluno"] == aluno_sel)
        resps = json.loads(resp_sel["respostas"])
        letras = ["A", "B", "C", "D", "E"]
        for i, q in enumerate(questoes):
            sua = resps.get(f"q{i}", "—")
            correta = q["gabarito"]
            acertou = sua == correta
            icone = "✅" if acertou else "❌"
            st.markdown(f"{icone} **Q{i+1}:** {q['enunciado']}")
            st.caption(f"Resposta: **{sua}** | Correta: **{correta}**")

    # Download CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar resultados em CSV", csv, "resultados.csv", "text/csv")

# ── ABA: MINHAS PROVAS ────────────────────────────────────────────────────────
elif aba == "📋 Minhas Provas":
    st.subheader("📋 Provas criadas")

    provas = listar_provas(st.session_state.usuario_id)
    if not provas:
        st.info("Nenhuma prova criada ainda. Vá em 'Criar Prova' para começar.")
        st.stop()

    for p in provas:
        questoes = json.loads(p["questoes"])
        respostas = buscar_respostas(p["id"])
        with st.container():
            col1, col2 = st.columns([0.75, 0.25])
            with col1:
                st.markdown(f"**{p['titulo']}**  \n📚 {p['materia']} • {len(questoes)} questões • {len(respostas)} resposta(s) • {p['criada_em']}")
            with col2:
                st.code(p["id"], language=None)
            st.divider()
