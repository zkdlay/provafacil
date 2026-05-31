import { useEffect, useRef, useState } from "react";
import { Route, Routes, useLocation, useParams } from "react-router-dom";
import {
  api,
  atualizarAlunosAutorizadosProva,
  criarTurma,
  excluirTurma,
  getErrorMessage,
  listarAlunos,
  listarAlunosAutorizadosProva,
  listarTurmas,
} from "./api";

const LETRAS = ["A", "B", "C", "D", "E"];
const LINK_EXPIRATION_LABEL = "1 hora e 10 minutos";

function toBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const payload = result.includes(",") ? result.split(",")[1] : result;
      resolve(payload);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function dataUri(base64) {
  if (!base64) return "";
  return `data:image/png;base64,${base64}`;
}

function getOrCreateDeviceId() {
  const storageKey = "provafacil_device_id";
  try {
    const existing = window.localStorage.getItem(storageKey);
    if (existing) return existing;
    const generated =
      window.crypto?.randomUUID?.() ||
      `device_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    window.localStorage.setItem(storageKey, generated);
    return generated;
  } catch {
    return `device_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  }
}

function toCsv(rows) {
  const header = [
    "Aluno",
    "Numero",
    "Nota",
    "Acertos",
    "Acessos",
    "Saidas aba",
    "Data/Hora",
  ];
  const escapeCell = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
  const body = rows.map((r) =>
    [
      r.nome_aluno,
      r.numero_aluno,
      r.nota,
      `${r.acertos}/${r.total}`,
      r.acessos,
      r.saidas_aba,
      r.respondida_em,
    ]
      .map(escapeCell)
      .join(",")
  );
  return [header.map(escapeCell).join(","), ...body].join("\n");
}

function AuthProfessor({ onLogin }) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [authAction, setAuthAction] = useState("");

  async function entrar() {
    if (authAction) return;
    if (!usuario.trim() || !senha.trim()) {
      setErro("Preencha todos os campos obrigatórios.");
      return;
    }
    let completed = false;
    setErro("");
    setAuthAction("login");
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ usuario, senha })
      });
      setUsuario("");
      setSenha("");
      onLogin(data);
      completed = true;
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      if (!completed) setAuthAction("");
    }
  }

  async function registrar() {
    if (authAction) return;
    if (!usuario.trim() || !senha.trim()) {
      setErro("Preencha todos os campos obrigatórios.");
      return;
    }
    let completed = false;
    setErro("");
    setAuthAction("register");
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ usuario, senha })
      });
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ usuario, senha })
      });
      setUsuario("");
      setSenha("");
      onLogin(data);
      completed = true;
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      if (!completed) setAuthAction("");
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-side-note">
        <h3>Plataforma de provas online</h3>
        <p>Crie avaliações, compartilhe links com alunos e acompanhe resultados em tempo real.</p>
      </section>
      <section className="card auth-card">
        <p className="auth-kicker">Prova Facil</p>
        <h2>Login do Professor</h2>
        <p className="auth-subtitle">Acesse sua conta para criar e acompanhar provas.</p>
        <form
          autoComplete="off"
          onSubmit={(e) => {
            e.preventDefault();
            entrar();
          }}
        >
          <input
            placeholder="Usuario"
            name="pf_usuario"
            value={usuario}
            disabled={Boolean(authAction)}
            autoComplete="off"
            onChange={(e) => setUsuario(e.target.value)}
          />
          <input
            placeholder="Senha"
            type="password"
            name="pf_senha"
            value={senha}
            disabled={Boolean(authAction)}
            autoComplete="new-password"
            onChange={(e) => setSenha(e.target.value)}
          />
          <div className="actions auth-actions">
            <button type="submit" disabled={Boolean(authAction)}>
              {authAction === "login" ? "Entrando..." : "Entrar"}
            </button>
            <button type="button" className="secondary" onClick={registrar} disabled={Boolean(authAction)}>
              {authAction === "register" ? "Criando..." : "Criar conta"}
            </button>
          </div>
        </form>
        {erro ? <p className="erro">{erro}</p> : null}
      </section>
    </main>
  );
}

function CriacaoProva({ token, turmas, carregandoTurmas, onCreated }) {
  const configInicial = { materia: "", titulo: "", qtd: 5, modo: "multipla_escolha", qtdOp: 4 };
  const [config, setConfig] = useState(configInicial);
  const [etapaCriacao, setEtapaCriacao] = useState(1);
  const [questoes, setQuestoes] = useState([]);
  const [materias, setMaterias] = useState([]);
  const [alunosSelecionados, setAlunosSelecionados] = useState([]);
  const [erro, setErro] = useState("");
  const [provaCriadaId, setProvaCriadaId] = useState("");
  const [linkGerado, setLinkGerado] = useState("");
  const [linkExpiraEm, setLinkExpiraEm] = useState("");
  const [copiado, setCopiado] = useState(false);
  const [loadingGerarLink, setLoadingGerarLink] = useState(false);
  const [loadingCopiarLink, setLoadingCopiarLink] = useState(false);
  const gerarLinkLockRef = useRef(false);
  const copiarLinkLockRef = useRef(false);

  useEffect(() => {
    api("/api/config").then((d) => setMaterias(d.materias_padrao || [])).catch(() => {});
  }, []);

  const alunosSelecionadosSet = new Set(alunosSelecionados.map(Number));
  const totalQuestoes = Number(config.qtd) || 0;
  const totalOpcoes = Number(config.qtdOp) || 0;

  function resetarCriacaoProva() {
    gerarLinkLockRef.current = false;
    copiarLinkLockRef.current = false;
    setConfig(configInicial);
    setEtapaCriacao(1);
    setQuestoes([]);
    setAlunosSelecionados([]);
    setErro("");
    setProvaCriadaId("");
    setLinkGerado("");
    setLinkExpiraEm("");
    setCopiado(false);
    setLoadingGerarLink(false);
    setLoadingCopiarLink(false);
  }

  function toggleAlunoAutorizado(alunoId, marcado) {
    const id = Number(alunoId);
    setAlunosSelecionados((prev) => {
      const atual = new Set(prev.map(Number));
      if (marcado) atual.add(id);
      else atual.delete(id);
      return Array.from(atual);
    });
  }

  function toggleTurmaAutorizada(turma, marcado) {
    const ids = (turma.alunos || []).map((aluno) => Number(aluno.id));
    setAlunosSelecionados((prev) => {
      const atual = new Set(prev.map(Number));
      ids.forEach((id) => {
        if (marcado) atual.add(id);
        else atual.delete(id);
      });
      return Array.from(atual);
    });
  }

  function turmaInteiraSelecionada(turma) {
    const ids = (turma.alunos || []).map((aluno) => Number(aluno.id));
    return ids.length > 0 && ids.every((id) => alunosSelecionadosSet.has(id));
  }

  function validarDadosBasicos() {
    if (!config.materia.trim() || !config.titulo.trim()) {
      setErro("Preencha materia e titulo.");
      return false;
    }
    if (!Number.isInteger(totalQuestoes) || totalQuestoes < 1 || totalQuestoes > 50) {
      setErro("Informe uma quantidade de questoes entre 1 e 50.");
      return false;
    }
    if (config.modo !== "texto" && (!Number.isInteger(totalOpcoes) || totalOpcoes < 2 || totalOpcoes > 5)) {
      setErro("Informe uma quantidade de alternativas entre 2 e 5.");
      return false;
    }
    setErro("");
    return true;
  }

  function prepararQuestaoExistente(q = {}) {
    const tipoBase = config.modo === "texto" ? "texto" : "multipla_escolha";
    const tipo = config.modo === "misto" ? q.tipo || "multipla_escolha" : tipoBase;
    const opcoes = Array.from({ length: totalOpcoes }).map((_, i) => q.opcoes?.[i] || "");
    const imagensOpcoes = Array.from({ length: totalOpcoes }).map((_, i) => q.imagens_opcoes?.[i] || null);
    return {
      tipo,
      enunciado: q.enunciado || "",
      imagem: q.imagem || null,
      opcoes: tipo === "texto" ? [] : opcoes,
      imagens_opcoes: tipo === "texto" ? [] : imagensOpcoes,
      gabarito: LETRAS.slice(0, totalOpcoes).includes(q.gabarito) ? q.gabarito : "A",
      gabarito_texto: q.gabarito_texto || "",
    };
  }

  function irParaQuestoes() {
    if (!validarDadosBasicos()) return;
    setQuestoes((prev) =>
      Array.from({ length: totalQuestoes }).map((_, i) => prepararQuestaoExistente(prev[i]))
    );
    setEtapaCriacao(2);
  }

  function atualizarQuestao(idx, patch) {
    setQuestoes((prev) => prev.map((q, i) => (i === idx ? { ...q, ...patch } : q)));
  }

  function atualizarTipoQuestao(idx, tipo) {
    setQuestoes((prev) =>
      prev.map((q, i) => {
        if (i !== idx) return q;
        if (tipo === "texto") {
          return { ...q, tipo, opcoes: [], imagens_opcoes: [] };
        }
        const opcoes = Array.from({ length: totalOpcoes }).map((_, j) => q.opcoes?.[j] || "");
        const imagensOpcoes = Array.from({ length: totalOpcoes }).map((_, j) => q.imagens_opcoes?.[j] || null);
        return { ...q, tipo, opcoes, imagens_opcoes, gabarito: q.gabarito || "A" };
      })
    );
  }

  function atualizarOpcao(qIdx, opIdx, val) {
    setQuestoes((prev) =>
      prev.map((q, i) => {
        if (i !== qIdx) return q;
        const op = [...q.opcoes];
        op[opIdx] = val;
        return { ...q, opcoes: op };
      })
    );
  }

  function atualizarImagemOpcao(qIdx, opIdx, base64) {
    setQuestoes((prev) =>
      prev.map((q, i) => {
        if (i !== qIdx) return q;
        const imgs = [...q.imagens_opcoes];
        imgs[opIdx] = base64;
        return { ...q, imagens_opcoes: imgs };
      })
    );
  }

  function validarQuestoes() {
    if (!questoes.length) {
      setErro("Preencha as questoes antes de continuar.");
      return false;
    }
    for (let i = 0; i < questoes.length; i += 1) {
      const q = questoes[i];
      if (!q.enunciado.trim()) {
        setErro(`Preencha o enunciado da questao ${i + 1}.`);
        return false;
      }
      if (q.tipo === "texto") {
        if (!String(q.gabarito_texto || "").trim()) {
          setErro(`Preencha o gabarito textual da questao ${i + 1}.`);
          return false;
        }
      } else if ((q.opcoes || []).slice(0, totalOpcoes).some((op) => !String(op || "").trim())) {
        setErro(`Preencha todas as alternativas da questao ${i + 1}.`);
        return false;
      }
    }
    setErro("");
    return true;
  }

  function irParaAlunos() {
    if (!validarQuestoes()) return;
    setEtapaCriacao(3);
  }

  function irParaResumo() {
    if (!alunosSelecionados.length) {
      setErro("Selecione pelo menos um aluno autorizado para esta prova.");
      return;
    }
    setErro("");
    setEtapaCriacao(4);
  }

  function montarQuestoesPayload() {
    return questoes.map((q) => {
      if (q.tipo === "texto") {
        return {
          tipo: "texto",
          enunciado: q.enunciado,
          imagem: q.imagem,
          opcoes: [],
          imagens_opcoes: [],
          gabarito_texto: q.gabarito_texto || "",
        };
      }
      return {
        tipo: "multipla_escolha",
        enunciado: q.enunciado,
        imagem: q.imagem,
        opcoes: q.opcoes,
        imagens_opcoes: q.imagens_opcoes,
        gabarito: q.gabarito,
      };
    });
  }

  async function gerarLink() {
    if (gerarLinkLockRef.current || provaCriadaId) return;
    if (!validarDadosBasicos() || !validarQuestoes()) return;
    if (!alunosSelecionados.length) {
      setErro("Selecione pelo menos um aluno autorizado para esta prova.");
      return;
    }

    gerarLinkLockRef.current = true;
    setErro("");
    setLoadingGerarLink(true);
    try {
      const created = await api(
        "/api/provas",
        {
          method: "POST",
          body: JSON.stringify({
            materia: config.materia,
            titulo: config.titulo,
            questoes: montarQuestoesPayload(),
            alunos_autorizados: alunosSelecionados,
          }),
        },
        token
      );
      setProvaCriadaId(created.id);
      setLinkGerado(`${window.location.origin}/aluno/${created.id}?token=${created.token}`);
      setLinkExpiraEm(created.expira_em || "");
      setCopiado(false);
      await onCreated();
    } catch (e) {
      gerarLinkLockRef.current = false;
      setErro(getErrorMessage(e));
    } finally {
      setLoadingGerarLink(false);
    }
  }

  async function copiarLink(link) {
    if (copiarLinkLockRef.current || !link) return;
    copiarLinkLockRef.current = true;
    setLoadingCopiarLink(true);
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1200);
    } catch {
      setErro("Nao foi possivel copiar o link.");
    } finally {
      copiarLinkLockRef.current = false;
      setLoadingCopiarLink(false);
    }
  }

  const etapas = ["Dados", "Questoes", "Alunos", "Link"];

  return (
    <section className="card wizard-card">
      <div className="section-title-row">
        <div>
          <h2>Criar Prova</h2>
          <p>Monte a avaliacao em etapas para evitar salvar algo incompleto.</p>
        </div>
        <span className="wizard-counter">Etapa {etapaCriacao} de 4</span>
      </div>

      <div className="wizard-steps">
        {etapas.map((label, i) => {
          const numero = i + 1;
          return (
            <div key={label} className={`wizard-step ${etapaCriacao === numero ? "active" : ""} ${etapaCriacao > numero ? "done" : ""}`}>
              <span>{numero}</span>
              <strong>{label}</strong>
            </div>
          );
        })}
      </div>

      {etapaCriacao === 1 ? (
        <div className="wizard-panel">
          <h3>Dados da prova</h3>
          <input list="materias" placeholder="Materia" value={config.materia} onChange={(e) => setConfig((c) => ({ ...c, materia: e.target.value }))} />
          <datalist id="materias">{materias.map((m) => <option key={m} value={m} />)}</datalist>
          <input placeholder="Titulo" value={config.titulo} onChange={(e) => setConfig((c) => ({ ...c, titulo: e.target.value }))} />
          <label>Quantidade de questoes</label>
          <input type="number" min="1" max="50" value={config.qtd} onChange={(e) => setConfig((c) => ({ ...c, qtd: e.target.value }))} />
          <select value={config.modo} onChange={(e) => setConfig((c) => ({ ...c, modo: e.target.value }))}>
            <option value="multipla_escolha">Somente multipla escolha</option>
            <option value="texto">Somente texto</option>
            <option value="misto">Misto</option>
          </select>
          {config.modo !== "texto" ? (
            <>
              <label>Quantidade de alternativas</label>
              <input type="number" min="2" max="5" value={config.qtdOp} onChange={(e) => setConfig((c) => ({ ...c, qtdOp: e.target.value }))} />
            </>
          ) : null}
          <div className="actions wizard-actions">
            <button onClick={irParaQuestoes}>Proximo</button>
          </div>
        </div>
      ) : null}

      {etapaCriacao === 2 ? (
        <div className="wizard-panel">
          <h3>Questoes</h3>
          {questoes.map((q, i) => (
            <article key={i} className="list-item question-card">
              <strong>Questao {i + 1}</strong>
              <textarea rows={2} placeholder="Enunciado" value={q.enunciado} onChange={(e) => atualizarQuestao(i, { enunciado: e.target.value })} />
              <label>Imagem da questao (opcional)</label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const base64 = await toBase64(file);
                  atualizarQuestao(i, { imagem: base64 });
                }}
              />
              {q.imagem ? <img className="preview" src={dataUri(q.imagem)} alt="Questao" /> : null}
              {config.modo === "misto" ? (
                <select value={q.tipo} onChange={(e) => atualizarTipoQuestao(i, e.target.value)}>
                  <option value="multipla_escolha">Multipla escolha</option>
                  <option value="texto">Texto</option>
                </select>
              ) : null}
              {q.tipo === "texto" ? (
                <input placeholder="Gabarito textual" value={q.gabarito_texto || ""} onChange={(e) => atualizarQuestao(i, { gabarito_texto: e.target.value, opcoes: [], imagens_opcoes: [] })} />
              ) : (
                <>
                  {q.opcoes.map((op, j) => (
                    <div key={j} className="opcao-box">
                      <input placeholder={`Opcao ${LETRAS[j]}`} value={op} onChange={(e) => atualizarOpcao(i, j, e.target.value)} />
                      <label>Imagem opcao {LETRAS[j]} (opcional)</label>
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/jpg"
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (!file) return;
                          const base64 = await toBase64(file);
                          atualizarImagemOpcao(i, j, base64);
                        }}
                      />
                      {q.imagens_opcoes?.[j] ? <img className="preview" src={dataUri(q.imagens_opcoes[j])} alt={`Opcao ${LETRAS[j]}`} /> : null}
                    </div>
                  ))}
                  <select value={q.gabarito} onChange={(e) => atualizarQuestao(i, { gabarito: e.target.value })}>
                    {LETRAS.slice(0, totalOpcoes).map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                </>
              )}
            </article>
          ))}
          <div className="actions wizard-actions">
            <button className="secondary" onClick={() => setEtapaCriacao(1)}>Voltar</button>
            <button onClick={irParaAlunos}>Proximo</button>
          </div>
        </div>
      ) : null}

      {etapaCriacao === 3 ? (
        <div className="wizard-panel">
          <h3>Alunos autorizados</h3>
          <div className="student-picker">
            {carregandoTurmas ? <p>Carregando turmas...</p> : null}
            {!carregandoTurmas && !(turmas || []).length ? (
              <p className="empty-note">Cadastre uma turma na aba Alunos antes de criar uma prova.</p>
            ) : null}
            {(turmas || []).map((turma) => (
              <div className="turma-picker" key={turma.id}>
                <label className="check-row turma-check">
                  <input
                    type="checkbox"
                    checked={turmaInteiraSelecionada(turma)}
                    onChange={(e) => toggleTurmaAutorizada(turma, e.target.checked)}
                  />
                  <span>{turma.nome} - selecionar turma inteira</span>
                </label>
                <div className="student-checks">
                  {(turma.alunos || []).map((aluno) => (
                    <label className="check-row" key={aluno.id}>
                      <input
                        type="checkbox"
                        checked={alunosSelecionadosSet.has(Number(aluno.id))}
                        onChange={(e) => toggleAlunoAutorizado(aluno.id, e.target.checked)}
                      />
                      <span>{aluno.nome}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <p className="selection-count">{alunosSelecionados.length} aluno(s) selecionado(s).</p>
          </div>
          <div className="actions wizard-actions">
            <button className="secondary" onClick={() => setEtapaCriacao(2)}>Voltar</button>
            <button onClick={irParaResumo}>Proximo</button>
          </div>
        </div>
      ) : null}

      {etapaCriacao === 4 ? (
        <div className="wizard-panel">
          <h3>Gerar link</h3>
          <div className="summary-grid">
            <div className="stat-card"><strong>Titulo</strong><span>{config.titulo || "-"}</span></div>
            <div className="stat-card"><strong>Materia</strong><span>{config.materia || "-"}</span></div>
            <div className="stat-card"><strong>Questoes</strong><span>{questoes.length}</span></div>
            <div className="stat-card"><strong>Alunos autorizados</strong><span>{alunosSelecionados.length}</span></div>
          </div>
          {!linkGerado ? (
            <div className="actions wizard-actions">
              <button className="secondary" onClick={() => setEtapaCriacao(3)} disabled={loadingGerarLink}>Voltar</button>
              <button onClick={gerarLink} disabled={loadingGerarLink || Boolean(provaCriadaId)}>
                {loadingGerarLink ? "Gerando..." : "Gerar link"}
              </button>
            </div>
          ) : (
            <div className="link-box">
              <p>Link da prova criada:</p>
              <input readOnly value={linkGerado} />
              <p>Link valido por {LINK_EXPIRATION_LABEL}.</p>
              {linkExpiraEm ? <p>Expira em {new Date(linkExpiraEm).toLocaleString()}.</p> : null}
              <div className="actions">
                <button onClick={() => copiarLink(linkGerado)} disabled={loadingCopiarLink}>
                  {loadingCopiarLink ? "Copiando..." : copiado ? "Copiado" : "Copiar link"}
                </button>
                <button className="secondary" onClick={resetarCriacaoProva}>
                  OK / Concluir
                </button>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {erro ? <p className="erro">{erro}</p> : null}
    </section>
  );
}
function TurmasAlunos({ token, turmas, totalAlunos, carregando, onRefresh }) {
  const [mostrarForm, setMostrarForm] = useState(false);
  const [nomeTurma, setNomeTurma] = useState("");
  const [qtdAlunos, setQtdAlunos] = useState(1);
  const [nomesAlunos, setNomesAlunos] = useState([]);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [excluindoTurmaId, setExcluindoTurmaId] = useState("");

  function gerarLista() {
    const total = Number(qtdAlunos);
    if (!Number.isInteger(total) || total < 1) {
      setErro("Informe uma quantidade valida de alunos.");
      return;
    }
    if (total > 120) {
      setErro("Crie turmas com ate 120 alunos por vez.");
      return;
    }
    setErro("");
    setMensagem("");
    setNomesAlunos((prev) => Array.from({ length: total }).map((_, i) => prev[i] || ""));
  }

  function atualizarNomeAluno(index, valor) {
    setNomesAlunos((prev) => prev.map((nome, i) => (i === index ? valor : nome)));
  }

  async function salvarTurma() {
    if (salvando) return;
    const alunos = nomesAlunos.map((nome) => nome.trim());
    if (!nomeTurma.trim()) {
      setErro("Informe o nome da turma.");
      return;
    }
    if (!alunos.length) {
      setErro("Clique em Gerar lista antes de salvar a turma.");
      return;
    }
    if (alunos.some((nome) => !nome)) {
      setErro("Preencha o nome de todos os alunos gerados.");
      return;
    }
    setErro("");
    setMensagem("");
    setSalvando(true);
    try {
      await criarTurma({ nome: nomeTurma, alunos }, token);
      setMensagem("Turma salva com sucesso.");
      setNomeTurma("");
      setQtdAlunos(1);
      setNomesAlunos([]);
      setMostrarForm(false);
      await onRefresh();
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      setSalvando(false);
    }
  }

  async function removerTurma(turmaId) {
    if (excluindoTurmaId) return;
    const confirmar = window.confirm("Excluir esta turma tambem remove os alunos dela das provas autorizadas. Deseja continuar?");
    if (!confirmar) return;
    setErro("");
    setMensagem("");
    setExcluindoTurmaId(turmaId);
    try {
      await excluirTurma(turmaId, token);
      setMensagem("Turma excluida com sucesso.");
      await onRefresh();
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      setExcluindoTurmaId("");
    }
  }

  return (
    <section className="card">
      <div className="section-title-row">
        <div>
          <h2>Alunos</h2>
          <p>Cadastre turmas e escolha depois quem pode acessar cada prova. Total: {totalAlunos} aluno(s).</p>
        </div>
        <button onClick={() => setMostrarForm((v) => !v)} disabled={salvando}>
          {mostrarForm ? "Fechar" : "Inserir turma"}
        </button>
      </div>

      {mostrarForm ? (
        <div className="turma-form">
          <input
            placeholder="Nome da turma"
            value={nomeTurma}
            disabled={salvando}
            onChange={(e) => setNomeTurma(e.target.value)}
          />
          <label>Quantidade de alunos</label>
          <input
            type="number"
            min="1"
            max="120"
            value={qtdAlunos}
            disabled={salvando}
            onChange={(e) => setQtdAlunos(e.target.value)}
          />
          <div className="actions">
            <button type="button" onClick={gerarLista} disabled={salvando}>
              Gerar lista
            </button>
            <button type="button" onClick={salvarTurma} disabled={salvando || !nomesAlunos.length}>
              {salvando ? "Salvando..." : "Salvar turma"}
            </button>
          </div>

          {nomesAlunos.length ? (
            <div className="student-name-grid">
              {nomesAlunos.map((nomeAluno, i) => (
                <label key={i}>
                  Aluno {i + 1}
                  <input
                    placeholder="Nome completo"
                    value={nomeAluno}
                    disabled={salvando}
                    onChange={(e) => atualizarNomeAluno(i, e.target.value)}
                  />
                </label>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {erro ? <p className="erro">{erro}</p> : null}
      {mensagem ? <p className="ok">{mensagem}</p> : null}
      {carregando ? <p>Carregando turmas...</p> : null}

      <div className="turmas-list">
        {(turmas || []).length ? (
          turmas.map((turma) => (
            <article className="list-item turma-card" key={turma.id}>
              <div className="section-title-row compact">
                <div>
                  <strong>{turma.nome}</strong>
                  <span>{(turma.alunos || []).length} aluno(s)</span>
                </div>
                <button
                  className="danger"
                  onClick={() => removerTurma(turma.id)}
                  disabled={Boolean(excluindoTurmaId)}
                >
                  {excluindoTurmaId === turma.id ? "Excluindo..." : "Excluir turma"}
                </button>
              </div>
              <div className="student-chips">
                {(turma.alunos || []).map((aluno) => (
                  <span key={aluno.id}>{aluno.nome}</span>
                ))}
              </div>
            </article>
          ))
        ) : (
          !carregando && <p className="empty-note">Nenhuma turma cadastrada ainda.</p>
        )}
      </div>
    </section>
  );
}

function DashboardProfessor() {
  const [auth, setAuth] = useState(null);
  const [aba, setAba] = useState("criar");
  const [provas, setProvas] = useState([]);
  const [turmas, setTurmas] = useState([]);
  const [alunos, setAlunos] = useState([]);
  const [provaSelecionada, setProvaSelecionada] = useState("");
  const [resultados, setResultados] = useState([]);
  const [estatisticasResultados, setEstatisticasResultados] = useState(null);
  const [monitor, setMonitor] = useState([]);
  const [erro, setErro] = useState("");
  const [carregandoResultados, setCarregandoResultados] = useState(false);
  const [carregandoMonitoramento, setCarregandoMonitoramento] = useState(false);
  const [excluindoId, setExcluindoId] = useState("");
  const [copiandoLinkId, setCopiandoLinkId] = useState("");
  const [linkCopiadoId, setLinkCopiadoId] = useState("");
  const [renovandoLinkId, setRenovandoLinkId] = useState("");
  const [baixandoCsv, setBaixandoCsv] = useState(false);
  const [carregandoTurmas, setCarregandoTurmas] = useState(false);
  const [desbloqueandoAcessos, setDesbloqueandoAcessos] = useState([]);
  const [editandoAlunosProvaId, setEditandoAlunosProvaId] = useState("");
  const [alunosAutorizadosEdicao, setAlunosAutorizadosEdicao] = useState([]);
  const [carregandoAutorizadosId, setCarregandoAutorizadosId] = useState("");
  const [salvandoAutorizadosId, setSalvandoAutorizadosId] = useState("");
  const [mensagemProvas, setMensagemProvas] = useState("");
  const deleteLockRef = useRef("");
  const resultadosRequestRef = useRef(0);
  const monitoramentoRequestRef = useRef(0);

  async function carregarProvas(token = auth?.token, preferredSelectedId = provaSelecionada) {
    if (!token) return;
    try {
      const data = await api("/api/provas", {}, token);
      setProvas(data);
      if (!data.length) {
        setProvaSelecionada("");
        return data;
      }
      const selectedStillExists = data.some((p) => p.id === preferredSelectedId);
      setProvaSelecionada(selectedStillExists ? preferredSelectedId : data[0].id);
      return data;
    } catch (e) {
      setErro(getErrorMessage(e));
      return [];
    }
  }

  async function carregarTurmas(token = auth?.token) {
    if (!token) return [];
    setCarregandoTurmas(true);
    try {
      const [turmasData, alunosData] = await Promise.all([
        listarTurmas(token),
        listarAlunos(token),
      ]);
      setTurmas(turmasData || []);
      setAlunos(alunosData || []);
      return turmasData || [];
    } catch (e) {
      setErro(getErrorMessage(e));
      return [];
    } finally {
      setCarregandoTurmas(false);
    }
  }

  useEffect(() => {
    if (auth?.token) {
      carregarProvas(auth.token);
      carregarTurmas(auth.token);
    }
  }, [auth]);

  useEffect(() => {
    if (!auth?.token || !provaSelecionada) return;
    if (aba === "resultados") {
      const requestId = resultadosRequestRef.current + 1;
      resultadosRequestRef.current = requestId;
      const currentProvaId = provaSelecionada;
      setCarregandoResultados(true);
      api(`/api/provas/${currentProvaId}/resultados`, {}, auth.token)
        .then((d) => {
          if (resultadosRequestRef.current !== requestId || provaSelecionada !== currentProvaId) return;
          setResultados(d.resultados || []);
          setEstatisticasResultados(d.estatisticas || null);
        })
        .catch((e) => {
          if (resultadosRequestRef.current !== requestId) return;
          setErro(getErrorMessage(e));
        })
        .finally(() => {
          if (resultadosRequestRef.current === requestId) setCarregandoResultados(false);
        });
      return () => {
        if (resultadosRequestRef.current === requestId) {
          resultadosRequestRef.current += 1;
        }
      };
    }
    if (aba === "monitoramento") {
      const currentProvaId = provaSelecionada;
      setCarregandoMonitoramento(true);
      const tick = () => {
        const requestId = monitoramentoRequestRef.current + 1;
        monitoramentoRequestRef.current = requestId;
        return api(`/api/provas/${currentProvaId}/monitoramento`, {}, auth.token)
          .then((d) => {
            if (monitoramentoRequestRef.current !== requestId || provaSelecionada !== currentProvaId) return;
            setMonitor(d.alunos || []);
          })
          .catch((e) => {
            if (monitoramentoRequestRef.current !== requestId) return;
            setErro(getErrorMessage(e));
          })
          .finally(() => {
            if (monitoramentoRequestRef.current === requestId) setCarregandoMonitoramento(false);
          });
      };
      tick();
      const id = setInterval(tick, 5000);
      return () => {
        clearInterval(id);
        monitoramentoRequestRef.current += 1;
      };
    }
    return undefined;
  }, [aba, provaSelecionada, auth]);

  async function excluir(id) {
    if (deleteLockRef.current) return;
    deleteLockRef.current = id;
    setErro("");
    setMensagemProvas("");
    setExcluindoId(id);
    try {
      await api(`/api/provas/${id}`, { method: "DELETE" }, auth.token);
      resultadosRequestRef.current += 1;
      monitoramentoRequestRef.current += 1;
      const wasSelected = id === provaSelecionada;
      const updated = await carregarProvas(auth.token, wasSelected ? "" : provaSelecionada);
      if (wasSelected) {
        setResultados([]);
        setEstatisticasResultados(null);
        setMonitor([]);
        if (!updated?.length) setProvaSelecionada("");
      }
      if (editandoAlunosProvaId === id) {
        cancelarEditorAlunos();
      }
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      deleteLockRef.current = "";
      setExcluindoId("");
    }
  }

  async function copiarLink(link, id) {
    if (copiandoLinkId) return;
    setErro("");
    setCopiandoLinkId(id);
    try {
      await navigator.clipboard.writeText(link);
      setLinkCopiadoId(id);
      setTimeout(() => setLinkCopiadoId(""), 1200);
    } catch {
      setErro("Nao foi possivel copiar o link.");
    } finally {
      setCopiandoLinkId("");
    }
  }

  async function renovarLink(id) {
    if (renovandoLinkId) return;
    setErro("");
    setMensagemProvas("");
    setRenovandoLinkId(id);
    try {
      const data = await api(`/api/provas/${id}/link`, { method: "POST" }, auth.token);
      const novoLink = `${window.location.origin}/aluno/${id}?token=${data.token}`;
      setProvas((prev) =>
        prev.map((p) =>
          p.id === id ? { ...p, token_acesso: data.token, expira_em: data.expira_em } : p
        )
      );
      try {
        await navigator.clipboard.writeText(novoLink);
        setLinkCopiadoId(id);
        setTimeout(() => setLinkCopiadoId(""), 1400);
      } catch {
        setErro("Novo link gerado, mas nao foi possivel copiar automaticamente.");
      }
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      setRenovandoLinkId("");
    }
  }

  function toggleAlunoEdicao(alunoId, marcado) {
    const id = Number(alunoId);
    setAlunosAutorizadosEdicao((prev) => {
      const selecionados = new Set(prev.map(Number));
      if (marcado) {
        selecionados.add(id);
      } else {
        selecionados.delete(id);
      }
      return Array.from(selecionados);
    });
  }

  function toggleTurmaEdicao(turma, marcado) {
    const idsTurma = (turma.alunos || []).map((aluno) => Number(aluno.id));
    setAlunosAutorizadosEdicao((prev) => {
      const selecionados = new Set(prev.map(Number));
      idsTurma.forEach((id) => {
        if (marcado) {
          selecionados.add(id);
        } else {
          selecionados.delete(id);
        }
      });
      return Array.from(selecionados);
    });
  }

  function turmaTodaSelecionada(turma) {
    const selecionados = new Set(alunosAutorizadosEdicao.map(Number));
    const idsTurma = (turma.alunos || []).map((aluno) => Number(aluno.id));
    return idsTurma.length > 0 && idsTurma.every((id) => selecionados.has(id));
  }

  async function abrirEditorAlunos(provaId) {
    if (carregandoAutorizadosId || salvandoAutorizadosId) return;
    setErro("");
    setMensagemProvas("");
    setEditandoAlunosProvaId(provaId);
    setCarregandoAutorizadosId(provaId);
    try {
      if (!turmas.length) {
        await carregarTurmas(auth.token);
      }
      const data = await listarAlunosAutorizadosProva(provaId, auth.token);
      setAlunosAutorizadosEdicao((data.alunos_autorizados || []).map(Number));
    } catch (e) {
      setErro(getErrorMessage(e));
      setEditandoAlunosProvaId("");
      setAlunosAutorizadosEdicao([]);
    } finally {
      setCarregandoAutorizadosId("");
    }
  }

  function cancelarEditorAlunos() {
    if (salvandoAutorizadosId) return;
    setEditandoAlunosProvaId("");
    setAlunosAutorizadosEdicao([]);
    setMensagemProvas("");
  }

  async function salvarEditorAlunos(provaId) {
    if (salvandoAutorizadosId || carregandoAutorizadosId) return;
    if (!alunosAutorizadosEdicao.length) {
      setErro("Selecione pelo menos um aluno autorizado para esta prova.");
      return;
    }
    setErro("");
    setMensagemProvas("");
    setSalvandoAutorizadosId(provaId);
    try {
      await atualizarAlunosAutorizadosProva(provaId, alunosAutorizadosEdicao, auth.token);
      setMensagemProvas("Alunos autorizados atualizados com sucesso. O link da prova nao foi alterado.");
      setEditandoAlunosProvaId("");
      setAlunosAutorizadosEdicao([]);
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      setSalvandoAutorizadosId("");
    }
  }

  async function desbloquearAluno(acessoId) {
    if (!acessoId || desbloqueandoAcessos.includes(acessoId)) return;
    setErro("");
    setDesbloqueandoAcessos((prev) => [...prev, acessoId]);
    try {
      const data = await api(
        `/api/provas/${provaSelecionada}/aluno-acessos/${acessoId}/desbloquear`,
        { method: "POST" },
        auth.token
      );
      setMonitor((prev) =>
        prev.map((m) =>
          m.aluno_acesso_id === acessoId
            ? {
                ...m,
                status: "ativo",
                pode_desbloquear: false,
                ultimo_evento: "Aluno desbloqueado",
                detalhe_ultimo: data?.acesso?.motivo_bloqueio || m.detalhe_ultimo,
              }
            : m
        )
      );
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      setDesbloqueandoAcessos((prev) => prev.filter((id) => id !== acessoId));
    }
  }

  function baixarCsvResultados() {
    if (baixandoCsv || !resultados.length) return;
    setBaixandoCsv(true);
    try {
      const csv = toCsv(resultados);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resultados_${provaSelecionada || "prova"}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setErro("Nao foi possivel baixar o CSV.");
    } finally {
      setBaixandoCsv(false);
    }
  }

  if (!auth) return <AuthProfessor onLogin={setAuth} />;

  return (
    <main className="page">
      <h1>Prova Facil</h1>
      <p>Bem-vindo, {auth.usuario_nome}</p>
      <div className="actions">
        <button onClick={() => setAba("criar")} className={aba === "criar" ? "" : "secondary"}>Criar Prova</button>
        <button onClick={() => setAba("alunos")} className={aba === "alunos" ? "" : "secondary"}>Alunos</button>
        <button onClick={() => setAba("provas")} className={aba === "provas" ? "" : "secondary"}>Minhas Provas</button>
        <button onClick={() => setAba("resultados")} className={aba === "resultados" ? "" : "secondary"}>Resultados</button>
        <button onClick={() => setAba("monitoramento")} className={aba === "monitoramento" ? "" : "secondary"}>Monitoramento</button>
      </div>
      {erro ? <p className="erro">{erro}</p> : null}

      {aba === "criar" ? (
        <CriacaoProva
          token={auth.token}
          turmas={turmas}
          carregandoTurmas={carregandoTurmas}
          onCreated={() => carregarProvas()}
        />
      ) : null}

      {aba === "alunos" ? (
        <TurmasAlunos
          token={auth.token}
          turmas={turmas}
          totalAlunos={alunos.length}
          carregando={carregandoTurmas}
          onRefresh={() => carregarTurmas(auth.token)}
        />
      ) : null}

      {aba === "provas" ? (
        <section className="card">
          <h2>Minhas Provas</h2>
          {mensagemProvas ? <p className="ok">{mensagemProvas}</p> : null}
          {provas.map((p) => {
            const link = p.token_acesso ? `${window.location.origin}/aluno/${p.id}?token=${p.token_acesso}` : "";
            const editandoAlunos = editandoAlunosProvaId === p.id;
            const selecionadosEdicao = new Set(alunosAutorizadosEdicao.map(Number));
            return (
              <article className="list-item" key={p.id}>
                <strong>{p.titulo}</strong>
                <span>{p.materia} - {p.quantidade_questoes} questoes</span>
                {link ? <input readOnly value={link} /> : <span>Nenhum link ativo. Gere um novo link para enviar aos alunos.</span>}
                {p.expira_em ? <span>Válido até {new Date(p.expira_em).toLocaleString()}.</span> : null}
                <div className="actions">
                  <button onClick={() => renovarLink(p.id)} disabled={Boolean(renovandoLinkId)}>
                    {renovandoLinkId === p.id ? "Renovando..." : "Renovar link"}
                  </button>
                  <button onClick={() => copiarLink(link, p.id)} disabled={Boolean(copiandoLinkId) || !link}>
                    {copiandoLinkId === p.id ? "Copiando..." : linkCopiadoId === p.id ? "Copiado" : "Copiar link"}
                  </button>
                  <button
                    className="secondary"
                    onClick={() => abrirEditorAlunos(p.id)}
                    disabled={Boolean(carregandoAutorizadosId) || Boolean(salvandoAutorizadosId)}
                  >
                    {carregandoAutorizadosId === p.id ? "Carregando..." : "Editar alunos autorizados"}
                  </button>
                  <button className="danger" onClick={() => excluir(p.id)} disabled={Boolean(excluindoId)}>
                    {excluindoId === p.id ? "Excluindo..." : "Excluir"}
                  </button>
                </div>
                {editandoAlunos ? (
                  <div className="authorized-editor">
                    <div className="section-title-row compact">
                      <div>
                        <strong>Editar alunos autorizados</strong>
                        <span>{alunosAutorizadosEdicao.length} aluno(s) selecionado(s)</span>
                      </div>
                    </div>
                    {carregandoAutorizadosId === p.id ? (
                      <p>Carregando alunos autorizados...</p>
                    ) : turmas.length ? (
                      <div className="student-picker compact-picker">
                        {turmas.map((turma) => (
                          <div className="turma-picker" key={turma.id}>
                            <label className="check-row turma-check">
                              <input
                                type="checkbox"
                                checked={turmaTodaSelecionada(turma)}
                                disabled={salvandoAutorizadosId === p.id}
                                onChange={(e) => toggleTurmaEdicao(turma, e.target.checked)}
                              />
                              Selecionar turma: {turma.nome}
                            </label>
                            <div className="student-checks">
                              {(turma.alunos || []).map((aluno) => (
                                <label className="check-row" key={aluno.id}>
                                  <input
                                    type="checkbox"
                                    checked={selecionadosEdicao.has(Number(aluno.id))}
                                    disabled={salvandoAutorizadosId === p.id}
                                    onChange={(e) => toggleAlunoEdicao(aluno.id, e.target.checked)}
                                  />
                                  {aluno.nome}
                                </label>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="empty-note">Cadastre uma turma na aba Alunos antes de editar autorizados.</p>
                    )}
                    <div className="actions">
                      <button
                        onClick={() => salvarEditorAlunos(p.id)}
                        disabled={
                          salvandoAutorizadosId === p.id ||
                          carregandoAutorizadosId === p.id ||
                          !alunosAutorizadosEdicao.length
                        }
                      >
                        {salvandoAutorizadosId === p.id ? "Salvando..." : "Salvar alteracoes"}
                      </button>
                      <button
                        className="secondary"
                        onClick={cancelarEditorAlunos}
                        disabled={salvandoAutorizadosId === p.id}
                      >
                        Cancelar
                      </button>
                    </div>
                    <p className="empty-note">
                      Alterar autorizados nao gera novo link e nao desbloqueia alunos automaticamente.
                    </p>
                  </div>
                ) : null}
              </article>
            );
          })}
        </section>
      ) : null}

      {aba === "resultados" ? (
        <section className="card">
          <h2>Resultados</h2>
          <select value={provaSelecionada} onChange={(e) => setProvaSelecionada(e.target.value)}>
            {provas.map((p) => <option key={p.id} value={p.id}>{p.titulo} ({p.materia})</option>)}
          </select>
          <div className="actions">
            <button onClick={baixarCsvResultados} disabled={!resultados.length || baixandoCsv}>
              {baixandoCsv ? "Baixando..." : "Baixar CSV"}
            </button>
          </div>
          {carregandoResultados ? <p>Carregando resultados...</p> : null}
          {estatisticasResultados ? (
            <div className="stats-grid">
              <div className="stat-card"><strong>Alunos</strong><span>{estatisticasResultados.alunos}</span></div>
              <div className="stat-card"><strong>Media da turma</strong><span>{estatisticasResultados.media_turma}</span></div>
              <div className="stat-card"><strong>Maior nota</strong><span>{estatisticasResultados.maior_nota}</span></div>
              <div className="stat-card"><strong>Menor nota</strong><span>{estatisticasResultados.menor_nota}</span></div>
            </div>
          ) : null}
          <div className="table-wrap">
            <table className="excel-table">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Numero</th>
                  <th>Nota</th>
                  <th>Acertos</th>
                  <th>Acessos</th>
                  <th>Saidas aba</th>
                  <th>Data/Hora</th>
                </tr>
              </thead>
              <tbody>
                {resultados.map((r, i) => (
                  <tr key={i}>
                    <td>{r.nome_aluno}</td>
                    <td>{r.numero_aluno}</td>
                    <td>{r.nota}</td>
                    <td>{r.acertos}/{r.total}</td>
                    <td>{r.acessos}</td>
                    <td>{r.saidas_aba}</td>
                    <td>{r.respondida_em}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {aba === "monitoramento" ? (
        <section className="card">
          <h2>Monitoramento</h2>
          <select value={provaSelecionada} onChange={(e) => setProvaSelecionada(e.target.value)}>
            {provas.map((p) => <option key={p.id} value={p.id}>{p.titulo} ({p.materia})</option>)}
          </select>
          {carregandoMonitoramento ? <p>Carregando monitoramento...</p> : null}
          <div className="table-wrap">
            <table className="excel-table">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Status</th>
                  <th>Dispositivo</th>
                  <th>Saidas</th>
                  <th>Ultimo evento</th>
                  <th>Detalhe</th>
                  <th>Ultima atividade</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {monitor.map((m, i) => (
                  <tr key={i} className={["fraude", "bloqueado"].includes(m.status) ? "fraud-row" : ""}>
                    <td>{m.nome}</td>
                    <td>{m.status}</td>
                    <td>{m.device_id || "-"}</td>
                    <td>{m.vezes_saiu}</td>
                    <td>{m.ultimo_evento}</td>
                    <td>
                      {m.fraude_nome_nao_autorizado
                        ? "Nome nao autorizado tentou acessar a prova."
                        : m.detalhe_ultimo || "-"}
                    </td>
                    <td>{m.data_hora_ultima}</td>
                    <td>
                      {m.status === "bloqueado" && m.aluno_acesso_id && m.pode_desbloquear ? (
                        <button
                          className="secondary"
                          onClick={() => desbloquearAluno(m.aluno_acesso_id)}
                          disabled={desbloqueandoAcessos.includes(m.aluno_acesso_id)}
                        >
                          {desbloqueandoAcessos.includes(m.aluno_acesso_id)
                            ? "Desbloqueando..."
                            : "Desbloquear aluno"}
                        </button>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </main>
  );
}

function AlunoPage() {
  const { provaId } = useParams();
  const location = useLocation();
  const token = new URLSearchParams(location.search).get("token") || "";
  const [deviceId] = useState(() => getOrCreateDeviceId());
  const [prova, setProva] = useState(null);
  const [nome, setNome] = useState("");
  const [numero, setNumero] = useState("");
  const [logado, setLogado] = useState(false);
  const [bloqueado, setBloqueado] = useState(false);
  const [bloqueioMensagem, setBloqueioMensagem] = useState("");
  const [respostas, setRespostas] = useState({});
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [acaoAluno, setAcaoAluno] = useState("");
  const enviarLockRef = useRef(false);
  const securityEventLockRef = useRef(false);
  const ultimaInteracaoInternaRef = useRef(Date.now());
  const loginEmAndamentoRef = useRef(false);
  const faseAluno = bloqueado
    ? "bloqueada"
    : resultado?.entregue
      ? "finalizada"
      : logado
        ? "prova_iniciada"
        : "login";
  const provaIniciada = faseAluno === "prova_iniciada";

  function marcarInteracaoInterna() {
    ultimaInteracaoInternaRef.current = Date.now();
  }

  function houveInteracaoInternaRecente(janelaMs = 900) {
    return loginEmAndamentoRef.current || Date.now() - ultimaInteracaoInternaRef.current < janelaMs;
  }

  useEffect(() => {
    if (!token) {
      setBloqueioMensagem("Link inválido. Solicite um novo link ao professor.");
      return;
    }
    setBloqueioMensagem("");
    api(
      `/api/aluno/provas/${provaId}?token=${encodeURIComponent(token)}&device_id=${encodeURIComponent(deviceId)}`
    )
      .then(setProva)
      .catch((e) => setBloqueioMensagem(getErrorMessage(e)));
  }, [provaId, token, deviceId]);

  useEffect(() => {
    if (!provaIniciada || !nome.trim()) return;

    const isEditableElement = (target) =>
      target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;

    const bloquearAcesso = async (evento, detalhe) => {
      if (!provaIniciada) return;
      if (securityEventLockRef.current) return;
      securityEventLockRef.current = true;
      setBloqueioMensagem("A prova foi bloqueada por saída da aba, minimização ou redimensionamento suspeito.");
      setBloqueado(true);
      setLogado(false);
      try {
        await api(`/api/aluno/provas/${provaId}/eventos`, {
          method: "POST",
          body: JSON.stringify({ nome_aluno: nome, evento, detalhe, token, device_id: deviceId })
        });
      } catch {
        // noop
      }
    };

    const initialWidth = window.innerWidth;
    const initialHeight = window.innerHeight;
    const startedAt = Date.now();
    let blurTimerId = null;
    let visibilityTimerId = null;
    let resizeTimerId = null;

    const clearSecurityTimers = () => {
      if (blurTimerId) window.clearTimeout(blurTimerId);
      if (visibilityTimerId) window.clearTimeout(visibilityTimerId);
      if (resizeTimerId) window.clearTimeout(resizeTimerId);
    };

    const onBlur = () => {
      if (blurTimerId) window.clearTimeout(blurTimerId);
      blurTimerId = window.setTimeout(() => {
        if (!provaIniciada) return;
        const paginaOculta = document.visibilityState === "hidden";
        const janelaSemFoco = typeof document.hasFocus === "function" && !document.hasFocus();
        if (paginaOculta || (janelaSemFoco && !houveInteracaoInternaRecente())) {
          bloquearAcesso("blur", "perda_de_foco_da_janela");
        }
      }, 500);
    };

    const onVisibility = () => {
      if (document.visibilityState === "hidden") {
        if (visibilityTimerId) window.clearTimeout(visibilityTimerId);
        visibilityTimerId = window.setTimeout(() => {
          if (provaIniciada && document.visibilityState === "hidden") {
            bloquearAcesso("visibility_hidden", "aba_oculta_bloqueio");
          }
        }, 500);
      }
    };

    const onResize = () => {
      if (!provaIniciada) return;
      if (Date.now() - startedAt < 1000) return;
      if (isEditableElement(document.activeElement)) return;
      if (resizeTimerId) window.clearTimeout(resizeTimerId);
      resizeTimerId = window.setTimeout(() => {
        if (isEditableElement(document.activeElement)) return;
        const widthDrop = window.innerWidth < initialWidth * 0.65;
        const heightDrop = window.innerHeight < initialHeight * 0.65;
        if (widthDrop || heightDrop) {
          bloquearAcesso(
            "resize_suspeito",
            `janela_redimensionada_${initialWidth}x${initialHeight}_para_${window.innerWidth}x${window.innerHeight}`
          );
        }
      }, 450);
    };

    window.addEventListener("blur", onBlur);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("resize", onResize);
    return () => {
      clearSecurityTimers();
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("resize", onResize);
    };
  }, [provaIniciada, nome, provaId, token, deviceId]);

  useEffect(() => {
    if (!provaIniciada || !nome.trim() || bloqueioMensagem) return;

    const isEditable = (target) =>
      target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;

    const registrarTentativaBloqueada = (detalhe) => {
      setErro("Ação bloqueada durante a prova.");
      api(`/api/aluno/provas/${provaId}/eventos`, {
        method: "POST",
        body: JSON.stringify({
          nome_aluno: nome,
          evento: "tentativa_bloqueada",
          detalhe,
          token,
          device_id: deviceId,
        }),
      }).catch(() => {});
    };

    const blockEvent = (e, detalhe) => {
      e.preventDefault();
      e.stopPropagation();
      registrarTentativaBloqueada(detalhe);
    };

    const onCopy = (e) => blockEvent(e, "copy");
    const onPaste = (e) => blockEvent(e, "paste");
    const onCut = (e) => blockEvent(e, "cut");
    const onContextMenu = (e) => blockEvent(e, "contextmenu");
    const onSelectStart = (e) => {
      if (isEditable(e.target)) return;
      blockEvent(e, "selectstart");
    };
    const onKeyDown = (e) => {
      const key = (e.key || "").toLowerCase();
      if ((e.ctrlKey || e.metaKey) && ["c", "v", "x", "a", "s", "p"].includes(key)) {
        blockEvent(e, `atalho_${key}`);
      }
      if (key === "f12") {
        blockEvent(e, "f12");
      }
      if (key === "printscreen") {
        blockEvent(e, "printscreen");
      }
    };

    document.addEventListener("copy", onCopy, true);
    document.addEventListener("paste", onPaste, true);
    document.addEventListener("cut", onCut, true);
    document.addEventListener("contextmenu", onContextMenu, true);
    document.addEventListener("selectstart", onSelectStart, true);
    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("copy", onCopy, true);
      document.removeEventListener("paste", onPaste, true);
      document.removeEventListener("cut", onCut, true);
      document.removeEventListener("contextmenu", onContextMenu, true);
      document.removeEventListener("selectstart", onSelectStart, true);
      document.removeEventListener("keydown", onKeyDown, true);
    };
  }, [provaIniciada, nome, bloqueioMensagem, provaId, token, deviceId]);

  async function entrar() {
    marcarInteracaoInterna();
    if (acaoAluno) return;
    if (!nome.trim() || !numero.trim()) {
      setErro("Preencha todos os campos obrigatórios.");
      return;
    }
    loginEmAndamentoRef.current = true;
    setErro("");
    setAcaoAluno("entrar");
    try {
      const data = await api(`/api/aluno/provas/${provaId}/login`, {
        method: "POST",
        body: JSON.stringify({ nome_aluno: nome, numero, token, device_id: deviceId })
      });
      if (data.ja_entregue) {
        setResultado({ nota: data.nota, acertos: data.acertos, total: data.total, entregue: true });
        setLogado(false);
        return;
      }
      setLogado(true);
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      setAcaoAluno("");
      window.setTimeout(() => {
        marcarInteracaoInterna();
        loginEmAndamentoRef.current = false;
      }, 800);
    }
  }

  async function enviar() {
    marcarInteracaoInterna();
    if (enviarLockRef.current) return;
    if (!nome.trim()) {
      setErro("Preencha todos os campos obrigatórios.");
      return;
    }
    enviarLockRef.current = true;
    setErro("");
    setAcaoAluno("enviar");
    try {
      const data = await api(`/api/aluno/provas/${provaId}/responder`, {
        method: "POST",
        body: JSON.stringify({ nome_aluno: nome, respostas, token, device_id: deviceId })
      });
      setResultado({ ...data, entregue: true });
      setLogado(false);
    } catch (e) {
      setErro(getErrorMessage(e));
      enviarLockRef.current = false;
    } finally {
      setAcaoAluno("");
    }
  }

  if (bloqueioMensagem) {
    return (
      <main className="page">
        <section className="card">
          <h2>Acesso indisponível</h2>
          <p>{bloqueioMensagem}</p>
        </section>
      </main>
    );
  }

  if (!prova) return <main className="page"><p>Carregando prova...</p>{erro ? <p className="erro">{erro}</p> : null}</main>;

  if (resultado?.entregue) {
    return (
      <main className="page">
        <section className="card">
          <h2>Prova entregue</h2>
          <p>Nota: {resultado.nota}</p>
          <p>Acertos: {resultado.acertos}/{resultado.total}</p>
        </section>
      </main>
    );
  }

  return (
    <main
      className={`page ${logado ? "exam-screen" : ""}`}
      onPointerDownCapture={marcarInteracaoInterna}
      onKeyDownCapture={marcarInteracaoInterna}
      onFocusCapture={marcarInteracaoInterna}
      onWheelCapture={marcarInteracaoInterna}
    >
      <h1>{prova.titulo}</h1>
      <p>{prova.materia}</p>
      {bloqueado ? (
        <section className="card">
          <h2>Acesso bloqueado</h2>
          <p>Voce saiu da aba da prova. O login foi encerrado.</p>
          <p>Peca ao professor um novo link para entrar novamente.</p>
        </section>
      ) : !logado ? (
        <section className="card">
          <h2>Acesso do Aluno</h2>
          <input placeholder="Nome completo" value={nome} disabled={Boolean(acaoAluno)} onChange={(e) => setNome(e.target.value)} />
          <input placeholder="Numero de chamada" value={numero} disabled={Boolean(acaoAluno)} onChange={(e) => setNumero(e.target.value)} />
          <button onClick={entrar} disabled={Boolean(acaoAluno)}>
            {acaoAluno === "entrar" ? "Acessando..." : "Acessar prova"}
          </button>
          {erro ? <p className="erro">{erro}</p> : null}
        </section>
      ) : (
        <section className="card">
          {prova.questoes.map((q, i) => (
            <article key={i} className="list-item">
              <strong>Questao {i + 1}</strong>
              <p>{q.enunciado}</p>
              {q.imagem ? <img className="preview" src={dataUri(q.imagem)} alt="Questao" /> : null}
              {q.tipo === "texto" ? (
                <input onChange={(e) => setRespostas((p) => ({ ...p, [`q${i}`]: e.target.value }))} />
              ) : (
                q.opcoes.map((op, j) => {
                  const letra = LETRAS[j];
                  const inputId = `q_${i}_${letra}`;
                  return (
                    <label className="alternative-option" htmlFor={inputId} key={letra}>
                      <input
                        id={inputId}
                        type="radio"
                        name={`q_${i}`}
                        checked={respostas[`q${i}`] === letra}
                        onChange={() => setRespostas((p) => ({ ...p, [`q${i}`]: letra }))}
                      />
                      <span className="alternative-content">
                        <span className="alternative-text">{letra}) {op}</span>
                        {q.imagens_opcoes?.[j] ? <img className="preview" src={dataUri(q.imagens_opcoes[j])} alt={`Opcao ${letra}`} /> : null}
                      </span>
                    </label>
                  );
                })
              )}
            </article>
          ))}
          <button onClick={enviar} disabled={Boolean(acaoAluno)}>
            {acaoAluno === "enviar" ? "Enviando..." : "Enviar prova"}
          </button>
          {erro ? <p className="erro">{erro}</p> : null}
        </section>
      )}
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardProfessor />} />
      <Route path="/aluno/:provaId" element={<AlunoPage />} />
    </Routes>
  );
}

