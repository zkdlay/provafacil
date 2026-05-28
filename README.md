# ProvaFacil

Sistema de provas online com frontend React, backend FastAPI e banco PostgreSQL.

## Stack
- Backend API: FastAPI
- Frontend: React + Vite
- Banco: PostgreSQL/Supabase
- Streamlit legado: mantido no repo para referencia/rollback

## Configuracao

Crie um arquivo `.env` na raiz do projeto com a URL do banco PostgreSQL:

```bash
DATABASE_URL=postgresql://usuario:senha@host:5432/banco
```

No Supabase, use a connection string do banco PostgreSQL. Se o provedor exigir SSL, inclua `?sslmode=require` no fim da URL.

## Como rodar localmente

### Backend
```bash
pip install -r requirements.txt
uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
```

Ao iniciar, o backend cria automaticamente as tabelas em PostgreSQL usando `database/schema_postgres.sql`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`.

## Funcionalidades
- Login e cadastro de professor
- Criacao de prova em 2 etapas
- Questoes de multipla escolha, texto e mistas
- Upload de imagem por questao e por opcao
- Listagem e exclusao de provas
- Link copiavel para aluno
- Resposta da prova com correcao automatica
- Resultados com estatisticas e CSV
- Monitoramento com atualizacao periodica
- Eventos do aluno: login, saida de aba e envio

## Rotas React
- `/`: painel do professor
- `/aluno/:provaId`: interface do aluno

## Endpoints principais
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/config`
- `GET /api/provas`
- `GET /api/provas/{prova_id}`
- `POST /api/provas`
- `PUT /api/provas/{prova_id}`
- `DELETE /api/provas/{prova_id}`
- `GET /api/provas/{prova_id}/resultados`
- `GET /api/provas/{prova_id}/monitoramento`
- `GET /api/aluno/provas/{prova_id}`
- `POST /api/aluno/provas/{prova_id}/login`
- `POST /api/aluno/provas/{prova_id}/eventos`
- `POST /api/aluno/provas/{prova_id}/responder`

## Migrar dados do SQLite antigo

Se existir um arquivo `provas.db`, configure o `.env` com `DATABASE_URL` apontando para o Supabase/PostgreSQL e rode:

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite provas.db
```

O script:
- cria o schema PostgreSQL se necessario
- importa `usuarios`, `provas`, `respostas`, `eventos` e `acessos_prova`
- preserva IDs existentes
- ajusta as sequences das tabelas com `SERIAL`
- nao sobrescreve registros que ja existam no PostgreSQL

## Deploy

### Banco: Supabase
1. Crie um projeto no Supabase.
2. Copie a connection string PostgreSQL.
3. Opcionalmente rode o SQL de `database/schema_postgres.sql` no SQL Editor do Supabase.
4. Use a mesma URL em `DATABASE_URL`.

### Backend: Render
1. Crie um Web Service apontando para este repositório.
2. Configure `DATABASE_URL` em Environment Variables.
3. Use o comando de start:
```bash
uvicorn backend.api:app --host 0.0.0.0 --port $PORT
```

### Frontend: Vercel
1. Importe a pasta `frontend`.
2. Build command: `npm run build`.
3. Output directory: `dist`.
4. Ajuste a URL da API em `frontend/src/api.js` para apontar para o backend em producao.
