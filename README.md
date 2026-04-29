# 📝 ProvaFácil

Sistema de provas online para professores, com correção automática e proteção rigorosa contra fraude.

## ✅ Funcionalidades

- Professor cria provas com múltipla escolha e gabarito
- Gera link único para cada prova
- Alunos respondem pelo link (sem precisar de login)
- Correção automática com nota na hora
- **Proteção anti-fraude rigorosa:**
  - ❌ Copiar/colar bloqueado (substitui por `###########`)
  - ❌ Abrir outra aba = nota 0 automática
  - ❌ Alt+Tab = nota 0 automática
  - ❌ DevTools/Console = nota 0 automática
  - ❌ Clique direito bloqueado
  - ❌ Fullscreen bloqueado
- Painel de resultados com notas e estatísticas
- Download dos resultados em CSV
- Sistema de login: cada professor tem seu usuário e senha

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

1. Crie uma conta: vá em **"Criar conta"** e escolha usuário + senha
2. Faça login com suas credenciais
3. Vá em **"Criar Prova"**
4. Escolha a matéria e dê um título
5. Adicione as questões uma a uma (enunciado + opções + gabarito)
6. Clique em **"Gerar Prova e Link"**
7. Copie o link gerado e envie para os alunos
8. Vá em **"Ver Resultados"** para acompanhar as notas em tempo real

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

## 🔒 Segurança e Proteção anti-fraude

### Proteção do Professor
- **Login obrigatório:** Cada professor tem usuário e senha únicos
- **Isolamento de dados:** Cada professor só vê suas próprias provas e resultados
- **Senhas criptografadas:** Armazenadas em SHA256, nunca em texto plano

### Proteção do Aluno (contra cola)
- **Copiar/colar bloqueado:** Qualquer tentativa retorna `###########`
- **Atalhos bloqueados:** Ctrl+C, Ctrl+A, Ctrl+V, Ctrl+S, Ctrl+U não funcionam
- **DevTools/Console bloqueado:** F12 e Ctrl+Shift+I detectam e registram nota 0
- **Clique direito desativado:** Não conseguem inspecionar elementos
- **Múltiplas abas detectadas:** Se sair para outra aba, é registrado **nota 0**
- **Fullscreen bloqueado:** Não conseguem maximizar a janela
- **Arrast/soltar bloqueado:** Não conseguem trazer conteúdo de fora

### 📸 Proteção contra Screenshot (NOVO!)
- **Filigrana:** O nome do aluno aparece como marca d'água em toda a tela (rotacionada a -45°)
  - Impossível tirar screenshot sem aparecer o nome do aluno
  - Desconfortável mas não impede responder
- **Detecção de captura:** Detecta quando o aluno tira screenshot
  - Print Screen bloqueado
  - Shift+Windows+S detectado
  - Cmd+Shift+3/4 detectado (Mac)
  - Mostra alerta: "⚠️ CAPTURA DE TELA DETECTADA"
- **Registro no professor:** Cada tentativa é registrada
  - Professor vê: "📸 3 tentativa(s) de screenshot"
  - Aparece na coluna "Alertas" do relatório
  - Data/hora exata fica registrada

### Como a fraude é registrada
Quando um aluno é detectado em fraude (DevTools aberto, múltiplas abas, screenshot, etc):
- ❌ **DevTools/Console:** Recebe **nota 0** e aba fecha automaticamente
- ⚠️ **Screenshot:** Aparece alerta e é registrado no relatório do professor
- ❌ **Múltiplas abas:** Recebe **nota 0** e fica registrado
- 📸 **Filigrana:** Nome do aluno visível em qualquer screenshot tirado
