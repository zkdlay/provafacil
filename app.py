import streamlit as st
import sqlite3
import json
import uuid
from datetime import datetime
import pandas as pd
import hashlib

st.set_page_config(
    page_title="Prova Fácil",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Limpar sessão ao mudar de prova ──────────────────────────────────────────
params = st.query_params
prova_id_atual = params.get("prova", None)

if "prova_id_anterior" not in st.session_state:
    st.session_state.prova_id_anterior = prova_id_atual

if prova_id_atual != st.session_state.prova_id_anterior:
    # Mudou de prova, limpa identificação do aluno
    st.session_state.aluno_identificado = False
    st.session_state.nome_aluno = ""
    st.session_state.chamada_aluno = ""
    st.session_state.prova_id_anterior = prova_id_atual
    st.rerun()
# ── CSS global ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Anti-cópia global */
* {
    user-select: none !important;
    -webkit-user-select: none !important;
    -moz-user-select: none !important;
}
/*Permitir digitação*/
input, textarea{
            user-select: text !important;
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
    width: 200%;
    height: 200%;
    pointer-events: none;
    z-index: 999999 !important;
    font-size: 28px;
    font-weight: bold;
    color: rgba(0, 0, 0, 0.15);
    transform: rotate(-30deg);
    line-height: 60px;
    white-space: pre-wrap;
}
</style>

<script>
function criarWatermark(nome) {
    let existente = document.querySelector('.watermark');
    if (existente) existente.remove();

    const wm = document.createElement('div');
    wm.className = 'watermark';

    let texto = '';
    for (let i = 0; i < 100; i++) {
        texto += nome + '   ';
    }

    wm.textContent = texto;
    document.body.appendChild(wm);
}

// tenta capturar QUALQUER input (mais robusto que placeholder)
setInterval(() => {
    const input = document.querySelector('input');

    if (input && input.value.trim().length > 0) {
        criarWatermark(input.value.trim());
    }
}, 1000);

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
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prova_id TEXT,
            nome_aluno TEXT,
            evento TEXT,
            detalhe TEXT,
            timestamp TEXT
        )
        """)
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
    
    # Migração: verifica se a tabela provas antiga existe sem usuario_id
    try:
        cursor = conn.execute("PRAGMA table_info(provas)")
        colunas = [row[1] for row in cursor.fetchall()]
        if 'usuario_id' not in colunas:
            # Tabela antiga detectada, migra para a nova
            conn.execute("ALTER TABLE provas ADD COLUMN usuario_id INTEGER DEFAULT 1")
            conn.commit()
    except:
        pass
    
    # Migração: verifica se a tabela respostas antiga existe sem os novos campos
    try:
        cursor = conn.execute("PRAGMA table_info(respostas)")
        colunas = [row[1] for row in cursor.fetchall()]
        if 'tentativas_screenshot' not in colunas:
            conn.execute("ALTER TABLE respostas ADD COLUMN tentativas_screenshot INTEGER DEFAULT 0")
            conn.commit()
        if 'alertas_fraude' not in colunas:
            conn.execute("ALTER TABLE respostas ADD COLUMN alertas_fraude TEXT")
            conn.commit()
    except:
        pass
    
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

def buscar_materias():
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT materia FROM provas").fetchall()
    conn.close()
    return [r["materia"] for r in rows if r["materia"]]

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

def registrar_evento(prova_id, nome_aluno, evento, detalhe=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO eventos (prova_id, nome_aluno, evento, detalhe, timestamp) VALUES (?,?,?,?,?)",
        (prova_id, nome_aluno, evento, detalhe, datetime.now().strftime("%H:%M:%S"))
    )
    conn.commit()
    conn.close()

def atualizar_prova(prova_id, materia, titulo, questoes):
    """Atualiza uma prova existente"""
    conn = get_conn()
    conn.execute(
        "UPDATE provas SET materia=?, titulo=?, questoes=? WHERE id=?",
        (materia, titulo, json.dumps(questoes, ensure_ascii=False), prova_id)
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

def aluno_ja_respondeu(prova_id, nome_aluno):
    """Verifica se o aluno já respondeu esta prova"""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM respostas WHERE prova_id=? AND nome_aluno=?",
        (prova_id, nome_aluno)
    ).fetchone()
    conn.close()
    resultado = row is not None
    # DEBUG:
    # st.write(f"🔍 DEBUG: aluno_ja_respondeu(prova={prova_id}, nome={nome_aluno}) = {resultado}")
    return resultado

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
def excluir_prova(prova_id):
    conn = get_conn()
    
    # Primeiro remove respostas associadas
    conn.execute(
        "DELETE FROM respostas WHERE prova_id = ?",
        (prova_id,)
    )
    
    # Depois remove a prova
    conn.execute(
        "DELETE FROM provas WHERE id = ?",
        (prova_id,)
    )
    
    conn.commit()
    conn.close()
# ── Roteamento por query param ────────────────────────────────────────────────
params = st.query_params
prova_id_url = params.get("prova", None)

params = st.query_params
try:
    if st.request:
        data = st.request.json
        if data:
            if data.get("acao") == "saiu_da_aba":
                registrar_evento(
                    prova_id=st.query_params.get("prova"),
                    nome_aluno=st.session_state.get("nome_aluno", "desconhecido"),
                    evento="troca_aba",
                    detalhe=data.get("motivo", "")
                )
except:
    pass
if "prova" in params:
    prova_id = params["prova"]

    # controle de acesso
    if "aluno_logado" not in st.session_state:
        st.session_state.aluno_logado = False
    
    # Inicializar estado da prova
    if "prova_enviada" not in st.session_state:
        st.session_state.prova_enviada = False
    
    if "nota" not in st.session_state:
        st.session_state.nota = None
    
    if "respostas_final" not in st.session_state:
        st.session_state.respostas_final = {}

    # ── TELA DE LOGIN DO ALUNO ──
    if not st.session_state.aluno_logado:
        st.title("📝 Acesso à Prova")

        nome = st.text_input("Nome completo")
        numero = st.text_input("Número de chamada")
        registrar_evento(prova_id, nome, "login", f"Chamada: {numero}")
        if st.button("Acessar prova", type="primary"):
            if not nome.strip() or not numero.strip():
                st.warning("Preencha todos os campos.")
            else:
                st.session_state.aluno_logado = True
                st.session_state.nome_aluno = nome
                st.session_state.numero_aluno = numero
                st.rerun()

        st.stop()
    
    # ── CARREGAR PROVA ──
    prova = buscar_prova(prova_id)

    if not prova:
        st.error("Prova não encontrada.")
        st.stop()

    questoes = json.loads(prova["questoes"])

    st.title(prova["titulo"])
    st.caption(f"{prova['materia']}")
    
    # 🔒 BLOQUEAR aluno que já respondeu (APÓS carregar a prova)
    if st.session_state.aluno_logado and hasattr(st.session_state, 'nome_aluno') and st.session_state.nome_aluno:
        if aluno_ja_respondeu(prova_id, st.session_state.nome_aluno):
            st.error("⚠️ Você já enviou esta prova. Não é possível responder novamente.")

            respostas = buscar_respostas(prova_id)
            resposta_aluno = next(
                (r for r in respostas if r["nome_aluno"] == st.session_state.nome_aluno),
                None
            )

            if resposta_aluno:
                st.write(f"**Nota:** {resposta_aluno['nota']}/10")
                st.write(f"**Data:** {resposta_aluno['respondida_em']}")
                
                # ✅ MOSTRAR GABARITO MESMO ASSIM
                st.session_state.prova_enviada = True
                st.session_state.nota = resposta_aluno['nota']
                st.session_state.respostas_final = json.loads(resposta_aluno['respostas'])


    respostas_aluno = {}

    letras = ["A", "B", "C", "D", "E"]

    # Se ainda não respondeu, renderiza em modo edição
    if not st.session_state.prova_enviada:
        for i, q in enumerate(questoes):
            st.markdown(f"### Questão {i+1}")
            st.write(q["enunciado"])

            # imagem da questão (se existir)
            if q.get("imagem"):
                st.image(f"data:image/png;base64,{q['imagem']}")

            op = st.radio(
                "Escolha:",
                options=letras[:len(q["opcoes"])],
                format_func=lambda x: f"{x}) {q['opcoes'][letras.index(x)]}",
                key=f"q_{i}",
                disabled=st.session_state.prova_enviada  # 🔒 trava depois do envio
            )

            respostas_aluno[f"q{i}"] = op if op else None

            st.divider()
        
        # Botão de envio com anti-duplicação
        if st.button("📨 Enviar prova", type="primary"):

            # 🚫 segurança extra (anti-fraude)
            if aluno_ja_respondeu(prova_id, st.session_state.nome_aluno):
                st.error("Prova já enviada anteriormente.")
                st.stop()

            nota = calcular_nota(questoes, respostas_aluno)

            salvar_resposta(
                prova_id,
                st.session_state.nome_aluno,
                respostas_aluno,
                nota
            )

            st.session_state.prova_enviada = True
            st.session_state.nota = nota
            st.session_state.respostas_final = respostas_aluno

            st.success("Prova enviada com sucesso!")
            st.rerun()

    # 📊 Modo leitura (resultado + gabarito)
    if st.session_state.prova_enviada:
        st.markdown("## 📊 Resultado")

        nota = st.session_state.nota
        respostas_final = st.session_state.respostas_final

        acertos = sum(
            1 for i, q in enumerate(questoes)
            if respostas_final.get(f"q{i}") == q["gabarito"]
        )

        st.write(f"Nota: {nota}")
        st.write(f"Acertos: {acertos}/{len(questoes)}")

        with st.expander("📋 Ver gabarito completo"):
            for i, q in enumerate(questoes):
                sua = respostas_final.get(f"q{i}", "—")
                correta = q["gabarito"]

                acertou = sua == correta
                icone = "✅" if acertou else "❌"
                
                # Pega o texto da opção correta
                idx_correta = letras.index(correta)
                texto_correta = q["opcoes"][idx_correta]
                
                st.write(f"{icone} **Q{i+1}**")
                st.write(f"📋 Enunciado: {q['enunciado']}")
                st.write(f"✓ Resposta correta: **{correta}) {texto_correta}**")
                if sua != correta:
                    st.write(f"✗ Sua resposta: {sua}")
                st.divider()
    
    # 🛑 Parar execução (evitar misturar com professor)
    st.stop()

# ── MODO PROFESSOR (login/registro) ──────────────────────────────────────────
if "usuario_id" not in st.session_state:
    st.write("🚨 TESTE NOVO CÓDIGO 🚨")

    st.markdown("## 📝 Prova Fácil")
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
st.markdown(f"## 📝 Prova Fácil")
st.caption(f"Bem-vindo, {st.session_state.usuario_nome}!")

# Botão de logout
if st.sidebar.button("🚪 Sair", type="secondary"):
    del st.session_state.usuario_id
    del st.session_state.usuario_nome
    st.rerun()

aba = st.sidebar.radio(
    "Navegação",
    ["➕ Criar Prova", "📊 Ver Resultados", "📋 Minhas Provas","🟢 Monitoramento"],
    label_visibility="collapsed"
)

# ── IMPORTANTE ──
import base64

def file_to_base64(file):
    if file is None:
        return None
    return base64.b64encode(file.read()).decode("utf-8")


# ── ABA: CRIAR PROVA ──────────────────────────────────────────────────────────
if aba == "➕ Criar Prova":

    # ── Estado inicial ──
    if "etapa_criacao" not in st.session_state:
        st.session_state.etapa_criacao = 1
    
    if "modo_edicao" not in st.session_state:
        st.session_state.modo_edicao = False
    
    if "prova_edicao_id" not in st.session_state:
        st.session_state.prova_edicao_id = None

    if "config_prova" not in st.session_state:
        st.session_state.config_prova = {}

    if "questoes_temp" not in st.session_state:
        st.session_state.questoes_temp = []
    
    # 🔄 Se entrou em modo edição, carrega a prova
    if st.session_state.modo_edicao and st.session_state.prova_edicao_id:
        prova_editar = buscar_prova(st.session_state.prova_edicao_id)
        if prova_editar:
            questoes_original = json.loads(prova_editar["questoes"])
            st.session_state.config_prova = {
                "materia": prova_editar["materia"],
                "titulo": prova_editar["titulo"],
                "qtd_questoes": len(questoes_original),
                "qtd_opcoes": len(questoes_original[0]["opcoes"]) if questoes_original else 5
            }
            st.session_state.questoes_temp = questoes_original
            st.session_state.etapa_criacao = 2

    # ─────────────────────────────────────────────────────────────────────────
    # 🧩 ETAPA 1 — CONFIGURAÇÃO
    # ─────────────────────────────────────────────────────────────────────────
    if st.session_state.etapa_criacao == 1:
        titulo_etapa = "✏️ Editar prova" if st.session_state.modo_edicao else "➕ Criar nova prova"
        st.subheader(titulo_etapa)

        col1, col2 = st.columns(2)
        with col1:
            opcoes_padrao = [
                "Matemática", "Ciências", "Física", "Química", "Biologia",
                "Português", "História", "Geografia", "Inglês"
            ]

            if "materias_custom" not in st.session_state:
                st.session_state.materias_custom = []

            todas_opcoes = opcoes_padrao + st.session_state.materias_custom + ["Outra"]

            materia_selecionada = st.selectbox("📚 Matéria", todas_opcoes)

            if materia_selecionada == "Outra":
                materia_custom = st.text_input("Digite a matéria")
                materia = materia_custom.strip() if materia_custom.strip() else ""
            else:
                materia = materia_selecionada

        with col2:
            titulo = st.text_input("🏷️ Título da prova")

        col3, col4 = st.columns(2)
        with col3:
            qtd_questoes = st.number_input("❓ Quantas questões?", min_value=1, max_value=50, value=5)
        with col4:
            qtd_opcoes = st.number_input("🔘 Quantas alternativas por questão?", min_value=2, max_value=5, value=4)
        
        if st.button("➡️ Próximo", type="primary"):
            if not titulo.strip():
                st.warning("Digite um título.")
            elif not materia:
                st.warning("Digite a matéria.")
            else:
                # evita duplicata tipo "matemática" vs "Matemática"
                materia_normalizada = materia.strip()

                if (
                    materia_normalizada not in opcoes_padrao and
                    materia_normalizada not in st.session_state.materias_custom
                ):
                    st.session_state.materias_custom.append(materia_normalizada)

                st.session_state.config_prova = {
                    "materia": materia_normalizada,
                    "titulo": titulo,
                    "qtd_questoes": qtd_questoes,
                    "qtd_opcoes": qtd_opcoes
                }

                st.session_state.questoes_temp = [{} for _ in range(qtd_questoes)]
                st.session_state.etapa_criacao = 2
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # 🧩 ETAPA 2 — CRIAR QUESTÕES
    # ─────────────────────────────────────────────────────────────────────────
    elif st.session_state.etapa_criacao == 2:
        config = st.session_state.config_prova

        st.subheader(f"📝 {config['titulo']}")
        st.caption(f"{config['materia']} • {config['qtd_questoes']} questões")

        letras = ["A", "B", "C", "D", "E"]

        for i in range(config["qtd_questoes"]):
            with st.expander(f"Questão {i+1}", expanded=(i == 0)):

                enunciado = st.text_area(f"Enunciado", key=f"enunciado_{i}")

                # 📷 imagem da questão
                img_q = st.file_uploader(
                    "Imagem da questão (opcional)",
                    type=["png", "jpg", "jpeg"],
                    key=f"img_q_{i}"
                )

                opcoes = []
                imagens_opcoes = []

                for j in range(config["qtd_opcoes"]):
                    col1, col2 = st.columns([0.7, 0.3])

                    with col1:
                        texto = st.text_input(f"{letras[j]}", key=f"op_{i}_{j}")
                        opcoes.append(texto)

                    with col2:
                        img_op = st.file_uploader(
                            f"Img {letras[j]}",
                            type=["png", "jpg", "jpeg"],
                            key=f"img_op_{i}_{j}"
                        )
                        imagens_opcoes.append(img_op)

                gabarito = st.selectbox(
                    "Resposta correta",
                    letras[:config["qtd_opcoes"]],
                    key=f"gabarito_{i}"
                )

                # ✔️ SALVA JÁ CONVERTIDO PARA BASE64
                st.session_state.questoes_temp[i] = {
                    "enunciado": enunciado,
                    "imagem": file_to_base64(img_q),
                    "opcoes": opcoes,
                    "imagens_opcoes": [file_to_base64(img) for img in imagens_opcoes],
                    "gabarito": gabarito
                }

        st.markdown("---")

        colA, colB = st.columns(2)

        # 🚀 salvar ou atualizar prova
        with colA:
            botao_texto = "💾 Atualizar Prova" if st.session_state.modo_edicao else "🚀 Gerar Prova"
            if st.button(botao_texto, type="primary", use_container_width=True):
                if st.session_state.modo_edicao:
                    # Modo edição: atualizar prova existente
                    prova_id = st.session_state.prova_edicao_id
                    atualizar_prova(
                        prova_id,
                        config["materia"],
                        config["titulo"],
                        st.session_state.questoes_temp
                    )
                    st.success(f"✅ Prova atualizada! ID: {prova_id}")
                else:
                    # Modo criação: criar nova prova
                    prova_id = salvar_prova(
                        st.session_state.usuario_id,
                        config["materia"],
                        config["titulo"],
                        st.session_state.questoes_temp
                    )
                    st.success(f"✅ Prova criada! ID: {prova_id}")
                    st.session_state.ultimo_id = prova_id

                # Limpar estado
                st.session_state.etapa_criacao = 1
                st.session_state.questoes_temp = []
                st.session_state.modo_edicao = False
                st.session_state.prova_edicao_id = None

                st.rerun()

        # 🔙 voltar
        with colB:
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state.etapa_criacao = 1
                st.session_state.modo_edicao = False
                st.session_state.prova_edicao_id = None
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # 🔗 LINK FINAL
    # ─────────────────────────────────────────────────────────────────────────
    if "ultimo_id" in st.session_state:
        pid = st.session_state.ultimo_id
        link = f"http://localhost:8501?prova={pid}"

        st.markdown("### 🔗 Link para os alunos")
        st.code(link, language=None)
        st.info("📋 Envie esse link para seus alunos.")

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

# ── ABA: MONITORAMENTO ────────────────────────────────────────────────────────
import time

time.sleep(3)
st.rerun()
elif aba == "🟢 Monitoramento":
    st.subheader("🟢 Monitoramento em Tempo Real")

    provas = listar_provas(st.session_state.usuario_id)

    if not provas:
        st.info("Nenhuma prova disponível.")
        st.stop()

    opcoes = {f"{p['titulo']} ({p['materia']})": p["id"] for p in provas}
    escolha = st.selectbox("Selecione a prova", list(opcoes.keys()))
    prova_id = opcoes[escolha]

    # 🔄 auto refresh
    st.caption("Atualiza automaticamente a cada 3 segundos")
    st.experimental_rerun if False else None
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM eventos WHERE prova_id=? ORDER BY id DESC",
        (prova_id,)
    ).fetchall()
    conn.close()
import pandas as pd

dados = []

for r in rows:
    dados.append({
        "Aluno": r["nome_aluno"],
        "Evento": r["evento"],
        "Detalhe": r["detalhe"],
        "Hora": r["timestamp"]
    })

df = pd.DataFrame(dados)

st.dataframe(df, use_container_width=True)
# ── ABA: MINHAS PROVAS ────────────────────────────────────────────────────────
elif aba == "📋 Minhas Provas":
    st.subheader("📋 Provas criadas")

    provas = listar_provas(st.session_state.usuario_id)

    if not provas:
        st.info("Nenhuma prova criada ainda. Vá em 'Criar Prova' para começar.")
        st.stop()

    # ── 🔽 FILTRO POR MATÉRIA ──
    materias = sorted(list(set([p["materia"] for p in provas])))
    materias.insert(0, "Todas")

    materia_selecionada = st.selectbox("📚 Filtrar por matéria", materias)

    # aplica filtro
    if materia_selecionada != "Todas":
        provas = [p for p in provas if p["materia"] == materia_selecionada]

    # ── LISTAGEM ──
    for p in provas:
        questoes = json.loads(p["questoes"])
        respostas = buscar_respostas(p["id"])

        with st.container():
            # Primeira linha: Informações da prova
            st.markdown(
                f"**{p['titulo']}**  \n📚 {p['materia']} • {len(questoes)} questões • {len(respostas)} resposta(s) • {p['criada_em']}"
            )
            
            # Segunda linha: ID, Botões de ação
            col1, col2= st.columns([0.5, 0.5])
            
            with col1:
                # 🔗 Botão para copiar link
                link = f"http://localhost:8501?prova={p['id']}"
                if st.button("🔗 Copiar Link", key=f"copy_{p['id']}", use_container_width=True):
                    st.code(link, language=None)
                    st.success("✅ Link copiado! Compartilhe com seus alunos.")
            
            with col2:
                # 🗑️ Botão para deletar
                if f"confirm_{p['id']}" not in st.session_state:
                    st.session_state[f"confirm_{p['id']}"] = False

                if not st.session_state[f"confirm_{p['id']}"]:
                    if st.button("🗑️ Deletar", key=f"del_{p['id']}", use_container_width=True):
                        st.session_state[f"confirm_{p['id']}"] = True
                        st.rerun()
                else:
                    st.warning("Tem certeza?")
                    
                    col_sim, col_nao = st.columns(2)
                    
                    with col_sim:
                        if st.button("✅ Deletar", key=f"yes_{p['id']}", use_container_width=True):
                            excluir_prova(p["id"])
                            st.success("Prova excluída!")
                            st.rerun()

                    with col_nao:
                        if st.button("❌ Cancelar", key=f"no_{p['id']}", use_container_width=True):
                            st.session_state[f"confirm_{p['id']}"] = False
                            st.rerun()

            st.divider()
