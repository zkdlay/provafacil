CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    usuario TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    criado_em TEXT
);

CREATE TABLE IF NOT EXISTS provas (
    id TEXT PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
    materia TEXT,
    titulo TEXT,
    questoes TEXT,
    criada_em TEXT,
    requer_alunos_autorizados INTEGER DEFAULT 0
);

ALTER TABLE provas ADD COLUMN IF NOT EXISTS requer_alunos_autorizados INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS turmas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alunos (
    id SERIAL PRIMARY KEY,
    turma_id INTEGER NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    nome_normalizado TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prova_alunos_autorizados (
    id SERIAL PRIMARY KEY,
    prova_id TEXT NOT NULL REFERENCES provas(id) ON DELETE CASCADE,
    aluno_id INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    UNIQUE(prova_id, aluno_id)
);

CREATE TABLE IF NOT EXISTS respostas (
    id SERIAL PRIMARY KEY,
    prova_id TEXT REFERENCES provas(id) ON DELETE CASCADE,
    nome_aluno TEXT,
    respostas TEXT,
    nota DOUBLE PRECISION,
    respondida_em TEXT,
    tentativas_screenshot INTEGER DEFAULT 0,
    alertas_fraude TEXT
);

CREATE TABLE IF NOT EXISTS eventos (
    id SERIAL PRIMARY KEY,
    prova_id TEXT REFERENCES provas(id) ON DELETE CASCADE,
    nome_aluno TEXT,
    evento TEXT,
    detalhe TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS acessos_prova (
    token TEXT PRIMARY KEY,
    prova_id TEXT REFERENCES provas(id) ON DELETE CASCADE,
    ativo INTEGER DEFAULT 1,
    criado_em TEXT,
    expira_em TIMESTAMP
);

ALTER TABLE acessos_prova ADD COLUMN IF NOT EXISTS expira_em TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_provas_usuario_id ON provas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_turmas_usuario_id ON turmas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_alunos_turma_id ON alunos(turma_id);
CREATE INDEX IF NOT EXISTS idx_alunos_nome_normalizado ON alunos(nome_normalizado);
CREATE INDEX IF NOT EXISTS idx_prova_alunos_prova_id ON prova_alunos_autorizados(prova_id);
CREATE INDEX IF NOT EXISTS idx_prova_alunos_aluno_id ON prova_alunos_autorizados(aluno_id);
CREATE INDEX IF NOT EXISTS idx_respostas_prova_id ON respostas(prova_id);
CREATE INDEX IF NOT EXISTS idx_eventos_prova_id ON eventos(prova_id);
CREATE INDEX IF NOT EXISTS idx_acessos_prova_id ON acessos_prova(prova_id);
