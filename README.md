# 📝 ProvaFácil

Sistema de provas online para professores, com correção automática e proteção anti-cópia.

## ✅ Funcionalidades

- Professor cria provas com múltipla escolha e gabarito
- Gera link único para cada prova
- Alunos respondem pelo link (sem precisar de login)
- Correção automática com nota na hora
- Proteção contra copiar/colar nas questões
- Painel de resultados com notas e estatísticas
- Download dos resultados em CSV

## 🚀 Como rodar

### 1. Instale as dependências
```bash
pip install -r requirements.txt
```

### 2. Execute o app
```bash
streamlit run app.py
```

### 3. Acesse no navegador
```
http://localhost:8501
```

## 👩‍🏫 Como usar (Professor)

1. Vá em **"Criar Prova"**
2. Escolha a matéria e dê um título
3. Adicione as questões uma a uma (enunciado + opções + gabarito)
4. Clique em **"Gerar Prova e Link"**
5. Copie o link gerado e envie para os alunos

## 🎓 Como usar (Aluno)

1. Abra o link recebido do professor
2. Digite seu nome completo
3. Responda todas as questões
4. Clique em **"Enviar Prova"**
5. Veja sua nota na hora!

## 🌐 Hospedagem gratuita (para acessar de qualquer lugar)

Para que os alunos acessem de casa ou do celular, hospede gratuitamente no:

**Streamlit Community Cloud:** https://streamlit.io/cloud
1. Coloque os arquivos no GitHub
2. Conecte ao Streamlit Cloud
3. O link gerado funcionará de qualquer dispositivo

## 📁 Arquivos

- `app.py` — código principal do app
- `requirements.txt` — dependências
- `provas.db` — banco de dados SQLite (criado automaticamente)

## 🔒 Proteção anti-cópia

As questões usam `user-select: none` (CSS) e bloqueiam o evento `copy` via JavaScript,
substituindo qualquer texto copiado por `###########`.
