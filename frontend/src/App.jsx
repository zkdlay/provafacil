import { useEffect, useRef, useState } from "react";
import { Route, Routes, useParams } from "react-router-dom";
import { api, getErrorMessage } from "./api";

const LETRAS = ["A", "B", "C", "D", "E"];

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
        <input
          placeholder="Usuario"
          value={usuario}
          disabled={Boolean(authAction)}
          onChange={(e) => setUsuario(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") entrar();
          }}
        />
        <input
          placeholder="Senha"
          type="password"
          value={senha}
          disabled={Boolean(authAction)}
          onChange={(e) => setSenha(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") entrar();
          }}
        />
        <div className="actions auth-actions">
          <button onClick={entrar} disabled={Boolean(authAction)}>
            {authAction === "login" ? "Entrando..." : "Entrar"}
          </button>
          <button className="secondary" onClick={registrar} disabled={Boolean(authAction)}>
            {authAction === "register" ? "Criando..." : "Criar conta"}
          </button>
        </div>
        {erro ? <p className="erro">{erro}</p> : null}
      </section>
    </main>
  );
}

function CriacaoProva({ token, onCreated }) {
  const [config, setConfig] = useState({ materia: "", titulo: "", qtd: 5, modo: "multipla_escolha", qtdOp: 4 });
  const [etapa, setEtapa] = useState(1);
  const [questoes, setQuestoes] = useState([]);
  const [materias, setMaterias] = useState([]);
  const [erro, setErro] = useState("");
  const [ultimoLink, setUltimoLink] = useState("");
  const [copiado, setCopiado] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [copiandoUltimoLink, setCopiandoUltimoLink] = useState(false);

  useEffect(() => {
    api("/api/config").then((d) => setMaterias(d.materias_padrao || [])).catch(() => {});
  }, []);

  function iniciarEtapa2() {
    if (!config.titulo.trim() || !config.materia.trim()) {
      setErro("Preencha materia e titulo.");
      return;
    }
    setErro("");
    const nova = Array.from({ length: Number(config.qtd) }).map(() => ({
      tipo: config.modo === "texto" ? "texto" : "multipla_escolha",
      enunciado: "",
      imagem: null,
      opcoes: Array.from({ length: Number(config.qtdOp) }).map(() => ""),
      imagens_opcoes: Array.from({ length: Number(config.qtdOp) }).map(() => null),
      gabarito: "A",
      gabarito_texto: ""
    }));
    setQuestoes(nova);
    setEtapa(2);
  }

  function atualizarQuestao(idx, patch) {
    setQuestoes((prev) => prev.map((q, i) => (i === idx ? { ...q, ...patch } : q)));
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

  async function gerar() {
    if (gerando) return;
    if (!config.titulo.trim() || !config.materia.trim() || !questoes.length) {
      setErro("Preencha todos os campos obrigatórios.");
      return;
    }
    setErro("");
    setGerando(true);
    try {
      const payloadQuestoes = questoes.map((q) => {
        if (q.tipo === "texto") {
          return {
            tipo: "texto",
            enunciado: q.enunciado,
            imagem: q.imagem,
            opcoes: [],
            imagens_opcoes: [],
            gabarito_texto: q.gabarito_texto || ""
          };
        }
        return {
          tipo: "multipla_escolha",
          enunciado: q.enunciado,
          imagem: q.imagem,
          opcoes: q.opcoes,
          imagens_opcoes: q.imagens_opcoes,
          gabarito: q.gabarito
        };
      });

      const created = await api(
        "/api/provas",
        {
          method: "POST",
          body: JSON.stringify({ materia: config.materia, titulo: config.titulo, questoes: payloadQuestoes })
        },
        token
      );
      const link = `${window.location.origin}/aluno/${created.id}`;
      setUltimoLink(link);
      setCopiado(false);
      setEtapa(1);
      setConfig({ materia: "", titulo: "", qtd: 5, modo: "multipla_escolha", qtdOp: 4 });
      setQuestoes([]);
      await onCreated();
    } catch (e) {
      setErro(getErrorMessage(e));
    } finally {
      setGerando(false);
    }
  }

  async function copiarLink(link) {
    if (copiandoUltimoLink) return;
    setCopiandoUltimoLink(true);
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1200);
    } catch {
      setErro("Nao foi possivel copiar o link.");
    } finally {
      setCopiandoUltimoLink(false);
    }
  }

  return (
    <section className="card">
      <h2>Criar Prova</h2>
      {etapa === 1 ? (
        <>
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
          <button onClick={iniciarEtapa2}>Proximo</button>
          {ultimoLink ? (
            <div className="link-box">
              <p>Link da prova criada:</p>
              <input readOnly value={ultimoLink} />
              <button onClick={() => copiarLink(ultimoLink)} disabled={copiandoUltimoLink}>
                {copiandoUltimoLink ? "Copiando..." : "Copiar link"}
              </button>
              {copiado ? <span className="ok">Copiado</span> : null}
            </div>
          ) : null}
        </>
      ) : (
        <>
          {questoes.map((q, i) => (
            <article key={i} className="list-item">
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
                <select value={q.tipo} onChange={(e) => atualizarQuestao(i, { tipo: e.target.value })}>
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
                    {LETRAS.slice(0, Number(config.qtdOp)).map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                </>
              )}
            </article>
          ))}
          <div className="actions">
            <button onClick={gerar} disabled={gerando}>
              {gerando ? "Salvando..." : "Salvar prova"}
            </button>
            <button className="secondary" onClick={() => setEtapa(1)} disabled={gerando}>Voltar</button>
          </div>
        </>
      )}
      {erro ? <p className="erro">{erro}</p> : null}
    </section>
  );
}

function DashboardProfessor() {
  const [auth, setAuth] = useState(null);
  const [aba, setAba] = useState("criar");
  const [provas, setProvas] = useState([]);
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
  const [baixandoCsv, setBaixandoCsv] = useState(false);
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

  useEffect(() => {
    if (auth?.token) carregarProvas(auth.token);
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
        <button onClick={() => setAba("provas")} className={aba === "provas" ? "" : "secondary"}>Minhas Provas</button>
        <button onClick={() => setAba("resultados")} className={aba === "resultados" ? "" : "secondary"}>Resultados</button>
        <button onClick={() => setAba("monitoramento")} className={aba === "monitoramento" ? "" : "secondary"}>Monitoramento</button>
      </div>
      {erro ? <p className="erro">{erro}</p> : null}

      {aba === "criar" ? <CriacaoProva token={auth.token} onCreated={() => carregarProvas()} /> : null}

      {aba === "provas" ? (
        <section className="card">
          <h2>Minhas Provas</h2>
          {provas.map((p) => {
            const link = `${window.location.origin}/aluno/${p.id}`;
            return (
              <article className="list-item" key={p.id}>
                <strong>{p.titulo}</strong>
                <span>{p.materia} - {p.quantidade_questoes} questoes</span>
                <input readOnly value={link} />
                <div className="actions">
                  <button onClick={() => copiarLink(link, p.id)} disabled={Boolean(copiandoLinkId)}>
                    {copiandoLinkId === p.id ? "Copiando..." : linkCopiadoId === p.id ? "Copiado" : "Copiar link"}
                  </button>
                  <button className="danger" onClick={() => excluir(p.id)} disabled={Boolean(excluindoId)}>
                    {excluindoId === p.id ? "Excluindo..." : "Excluir"}
                  </button>
                </div>
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
                  <th>Saidas</th>
                  <th>Ultimo evento</th>
                  <th>Ultima atividade</th>
                </tr>
              </thead>
              <tbody>
                {monitor.map((m, i) => (
                  <tr key={i}>
                    <td>{m.nome}</td>
                    <td>{m.status}</td>
                    <td>{m.vezes_saiu}</td>
                    <td>{m.ultimo_evento}</td>
                    <td>{m.data_hora_ultima}</td>
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
  const [prova, setProva] = useState(null);
  const [nome, setNome] = useState("");
  const [numero, setNumero] = useState("");
  const [logado, setLogado] = useState(false);
  const [bloqueado, setBloqueado] = useState(false);
  const [respostas, setRespostas] = useState({});
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState("");
  const [acaoAluno, setAcaoAluno] = useState("");
  const enviarLockRef = useRef(false);

  useEffect(() => {
    api(`/api/aluno/provas/${provaId}`).then(setProva).catch((e) => setErro(getErrorMessage(e)));
  }, [provaId]);

  useEffect(() => {
    if (!logado || !nome || resultado) return;

    const bloquearAcesso = async (evento, detalhe) => {
      setBloqueado(true);
      setLogado(false);
      try {
        await api(`/api/aluno/provas/${provaId}/eventos`, {
          method: "POST",
          body: JSON.stringify({ nome_aluno: nome, evento, detalhe })
        });
      } catch {
        // noop
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "hidden") {
        bloquearAcesso("blur", "aba_oculta_bloqueio");
      }
    };

    const onKeyDown = (e) => {
      const key = (e.key || "").toLowerCase();
      if ((e.ctrlKey || e.metaKey) && ["c", "v", "x", "a", "u", "s", "t", "n"].includes(key)) {
        e.preventDefault();
      }
      if (key === "f12") e.preventDefault();
    };

    document.addEventListener("visibilitychange", onVisibility);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [logado, nome, provaId, resultado]);

  async function entrar() {
    if (acaoAluno) return;
    if (!nome.trim() || !numero.trim()) {
      setErro("Preencha todos os campos obrigatórios.");
      return;
    }
    setErro("");
    setAcaoAluno("entrar");
    try {
      const data = await api(`/api/aluno/provas/${provaId}/login`, {
        method: "POST",
        body: JSON.stringify({ nome_aluno: nome, numero })
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
    }
  }

  async function enviar() {
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
        body: JSON.stringify({ nome_aluno: nome, respostas })
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
    <main className="page">
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
