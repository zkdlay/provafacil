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
    criada_em TEXT
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
    criado_em TEXT
);

CREATE INDEX IF NOT EXISTS idx_provas_usuario_id ON provas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_respostas_prova_id ON respostas(prova_id);
CREATE INDEX IF NOT EXISTS idx_eventos_prova_id ON eventos(prova_id);
CREATE INDEX IF NOT EXISTS idx_acessos_prova_id ON acessos_prova(prova_id);
