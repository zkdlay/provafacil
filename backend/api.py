from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import json
import uuid

from auth.professor import AuthService
from prova.services import ProvaService
from eventos.rastreamento import registrar_evento, obter_eventos_prova
from core.constants import LINK_EXPIRATION_MINUTES, MATERIAS_PADRAO
from core.normalization import normalizar_nome


app = FastAPI(title="Prova Facil API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://provafacil-rust.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
SESSIONS: Dict[str, Dict[str, Any]] = {}


class RegisterPayload(BaseModel):
    usuario: str
    senha: str = Field(min_length=4)


class LoginPayload(BaseModel):
    usuario: str
    senha: str


class ProvaCreatePayload(BaseModel):
    materia: str
    titulo: str
    questoes: List[Dict[str, Any]]
    alunos_autorizados: Optional[List[int]] = None


class AlunosAutorizadosPayload(BaseModel):
    alunos_autorizados: List[int] = Field(default_factory=list)


class TurmaCreatePayload(BaseModel):
    nome: str
    alunos: List[str] = Field(default_factory=list)


class AlunoLoginPayload(BaseModel):
    nome_aluno: str
    numero: str
    token: Optional[str] = None
    device_id: Optional[str] = None


class EventoPayload(BaseModel):
    nome_aluno: str
    evento: str
    detalhe: str = ""
    token: Optional[str] = None
    device_id: Optional[str] = None


class RespostaPayload(BaseModel):
    nome_aluno: str
    respostas: Dict[str, Any]
    token: Optional[str] = None
    device_id: Optional[str] = None


def get_user_from_token(token: Optional[str]):
    if not token or token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    return SESSIONS[token]


def validar_posse_prova(prova_id: str, token: Optional[str]):
    user = get_user_from_token(token)
    prova = ProvaService.buscar_prova(prova_id)
    if not prova or int(prova["usuario_id"]) != int(user["usuario_id"]):
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    return prova


def prova_com_meta(prova: Dict[str, Any]):
    questoes = json.loads(prova["questoes"])
    return {
        **prova,
        "quantidade_questoes": len(questoes),
    }


def format_expira_em(expira_em):
    if not expira_em:
        return None
    suffix = "Z" if getattr(expira_em, "tzinfo", None) is None else ""
    return f"{expira_em.isoformat()}{suffix}"


def validar_acesso_aluno(prova_id: str, token: Optional[str]):
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Link inválido. Solicite um novo link ao professor.",
        )

    acesso = ProvaService.buscar_acesso_prova(prova_id, token)
    if not acesso:
        raise HTTPException(
            status_code=403,
            detail="Link inválido. Solicite um novo link ao professor.",
        )
    if int(acesso.get("ativo") or 0) != 1:
        raise HTTPException(
            status_code=403,
            detail="Este acesso foi bloqueado ou revogado. Solicite um novo link ao professor.",
        )
    expira_em = acesso.get("expira_em")
    if not expira_em:
        raise HTTPException(
            status_code=403,
            detail="Este link expirou. Solicite um novo link ao professor.",
        )
    from datetime import datetime

    if expira_em <= datetime.utcnow():
        raise HTTPException(
            status_code=403,
            detail="Este link expirou. Solicite um novo link ao professor.",
        )
    return acesso


EVENTOS_BLOQUEIO_INDIVIDUAL = {"blur", "visibility_hidden", "resize_suspeito", "acesso_bloqueado"}
MOTIVOS_DESBLOQUEIO_PERMITIDOS = {
    "blur",
    "visibility_hidden",
    "resize_suspeito",
    "acesso_bloqueado",
    "perda_de_foco",
    "saiu da aba",
    "saiu_da_aba",
    "aba_oculta",
    "janela_redimensionada",
    "minimiz",
}
MENSAGEM_ACESSO_INDIVIDUAL_BLOQUEADO = (
    "Sua prova foi bloqueada por atividade suspeita. Informe o professor."
)
MENSAGEM_FRAUDE_NOME_NAO_AUTORIZADO = (
    "Nome nao autorizado tentou acessar a prova."
)


def validar_device_id(device_id: Optional[str]):
    if not device_id or not device_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Identificacao do dispositivo ausente. Atualize a pagina e tente novamente.",
        )
    return device_id.strip()


def garantir_acesso_individual_ativo(prova_id: str, token: str, nome_aluno: str, device_id: str):
    acesso = ProvaService.criar_ou_atualizar_aluno_acesso(prova_id, token, nome_aluno, device_id)
    if acesso and acesso.get("status") == "bloqueado":
        raise HTTPException(status_code=403, detail=MENSAGEM_ACESSO_INDIVIDUAL_BLOQUEADO)
    return acesso


def motivo_permite_desbloqueio(motivo: Optional[str]):
    texto = (motivo or "").lower()
    return any(motivo_permitido in texto for motivo_permitido in MOTIVOS_DESBLOQUEIO_PERMITIDOS)


@app.get("/api/config")
def config():
    return {"materias_padrao": MATERIAS_PADRAO}


@app.post("/api/auth/register")
def register(payload: RegisterPayload):
    ok, msg = AuthService.registrar_professor(payload.usuario.strip(), payload.senha)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/auth/login")
def login(payload: LoginPayload):
    ok, uid = AuthService.verificar_login(payload.usuario.strip(), payload.senha)
    if not ok:
        raise HTTPException(status_code=401, detail="Usuario ou senha invalidos")
    token = str(uuid.uuid4())
    SESSIONS[token] = {"usuario_id": uid, "usuario_nome": payload.usuario.strip()}
    return {"token": token, "usuario_id": uid, "usuario_nome": payload.usuario.strip()}


@app.get("/api/turmas")
def listar_turmas(x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    return ProvaService.listar_turmas(user["usuario_id"])


@app.post("/api/turmas")
def criar_turma(payload: TurmaCreatePayload, x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    nome = payload.nome.strip()
    alunos = [aluno.strip() for aluno in payload.alunos if aluno and aluno.strip()]
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome da turma.")
    if not alunos:
        raise HTTPException(status_code=400, detail="Informe pelo menos um aluno.")
    turma = ProvaService.criar_turma(user["usuario_id"], nome, alunos)
    return {"ok": True, "turma": turma}


@app.delete("/api/turmas/{turma_id}")
def excluir_turma(turma_id: int, x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    removida = ProvaService.excluir_turma(turma_id, user["usuario_id"])
    if not removida:
        raise HTTPException(status_code=404, detail="Turma nao encontrada.")
    return {"ok": True, "message": "Turma excluida com sucesso."}


@app.get("/api/alunos")
def listar_alunos(x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    return ProvaService.listar_alunos(user["usuario_id"])


@app.get("/api/provas")
def listar_provas(x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    provas = ProvaService.listar_provas(user["usuario_id"])
    dados = []
    for prova in provas:
        item = prova_com_meta(prova)
        acesso = ProvaService.buscar_acesso_ativo(prova["id"])
        if acesso:
            item["token_acesso"] = acesso["token"]
            item["expira_em"] = format_expira_em(acesso.get("expira_em"))
        else:
            item["token_acesso"] = None
            item["expira_em"] = None
        dados.append(item)
    return dados


@app.get("/api/provas/{prova_id}")
def detalhar_prova(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    prova = validar_posse_prova(prova_id, x_auth_token)
    return prova_com_meta(prova)


@app.post("/api/provas")
def criar_prova(payload: ProvaCreatePayload, x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    aluno_ids = payload.alunos_autorizados or []
    if not aluno_ids:
        raise HTTPException(
            status_code=400,
            detail="Selecione pelo menos um aluno autorizado para esta prova.",
        )
    if not ProvaService.alunos_pertencem_usuario(user["usuario_id"], aluno_ids):
        raise HTTPException(
            status_code=403,
            detail="A lista de alunos autorizados contem alunos invalidos.",
        )

    prova_id = ProvaService.salvar_prova(
        user["usuario_id"], payload.materia.strip(), payload.titulo.strip(), payload.questoes
    )
    try:
        ProvaService.salvar_alunos_autorizados(prova_id, aluno_ids)
    except Exception:
        ProvaService.excluir_prova(prova_id)
        raise

    acesso = ProvaService.gerar_token_acesso(prova_id)
    return {
        "id": prova_id,
        "token": acesso["token"],
        "expira_em": format_expira_em(acesso["expira_em"]),
    }


@app.post("/api/provas/{prova_id}/link")
def renovar_link_prova(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    validar_posse_prova(prova_id, x_auth_token)
    acesso = ProvaService.gerar_token_acesso(prova_id)
    return {
        "ok": True,
        "token": acesso["token"],
        "expira_em": format_expira_em(acesso["expira_em"]),
        "validade_minutos": LINK_EXPIRATION_MINUTES,
    }


@app.put("/api/provas/{prova_id}")
def atualizar_prova(
    prova_id: str, payload: ProvaCreatePayload, x_auth_token: Optional[str] = Header(default=None)
):
    validar_posse_prova(prova_id, x_auth_token)
    if payload.alunos_autorizados is not None:
        user = get_user_from_token(x_auth_token)
        if not payload.alunos_autorizados:
            raise HTTPException(
                status_code=400,
                detail="Selecione pelo menos um aluno autorizado para esta prova.",
            )
        if not ProvaService.alunos_pertencem_usuario(user["usuario_id"], payload.alunos_autorizados):
            raise HTTPException(
                status_code=403,
                detail="A lista de alunos autorizados contem alunos invalidos.",
            )
    ProvaService.atualizar_prova(prova_id, payload.materia.strip(), payload.titulo.strip(), payload.questoes)
    if payload.alunos_autorizados is not None:
        ProvaService.salvar_alunos_autorizados(prova_id, payload.alunos_autorizados)
    return {"ok": True}


@app.get("/api/provas/{prova_id}/alunos-autorizados")
def listar_alunos_autorizados_prova(
    prova_id: str,
    x_auth_token: Optional[str] = Header(default=None),
):
    validar_posse_prova(prova_id, x_auth_token)
    alunos = ProvaService.listar_alunos_autorizados_prova(prova_id)
    return {
        "alunos_autorizados": [aluno["id"] for aluno in alunos],
        "alunos": alunos,
    }


@app.put("/api/provas/{prova_id}/alunos-autorizados")
def atualizar_alunos_autorizados_prova(
    prova_id: str,
    payload: AlunosAutorizadosPayload,
    x_auth_token: Optional[str] = Header(default=None),
):
    validar_posse_prova(prova_id, x_auth_token)
    user = get_user_from_token(x_auth_token)
    aluno_ids = payload.alunos_autorizados or []
    if not aluno_ids:
        raise HTTPException(
            status_code=400,
            detail="Selecione pelo menos um aluno autorizado para esta prova.",
        )
    if not ProvaService.alunos_pertencem_usuario(user["usuario_id"], aluno_ids):
        raise HTTPException(
            status_code=403,
            detail="A lista de alunos autorizados contem alunos invalidos.",
        )
    ProvaService.salvar_alunos_autorizados(prova_id, aluno_ids)
    return {"ok": True, "message": "Alunos autorizados atualizados com sucesso."}


@app.delete("/api/provas/{prova_id}")
def excluir_prova(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    validar_posse_prova(prova_id, x_auth_token)
    ProvaService.excluir_prova(prova_id)
    return {"ok": True, "message": "Prova e dados relacionados excluidos com sucesso."}


@app.get("/api/provas/{prova_id}/resultados")
def resultados_prova(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    prova = validar_posse_prova(prova_id, x_auth_token)
    questoes = json.loads(prova["questoes"])
    respostas = ProvaService.buscar_respostas(prova_id)
    eventos = obter_eventos_prova(prova_id)
    eventos_por_aluno: Dict[str, Dict[str, int]] = {}
    for ev in eventos:
        nome = ev.get("nome_aluno") or ""
        if not nome:
            continue
        if nome not in eventos_por_aluno:
            eventos_por_aluno[nome] = {
                "acessos": 0,
                "saidas_aba": 0,
                "eventos_total": 0,
                "numero_aluno": "-",
            }
        item = eventos_por_aluno[nome]
        item["eventos_total"] += 1
        tipo = ev.get("evento")
        if tipo == "login":
            item["acessos"] += 1
            detalhe = (ev.get("detalhe") or "").strip()
            if "chamada" in detalhe.lower() and ":" in detalhe:
                item["numero_aluno"] = detalhe.split(":")[-1].strip() or "-"
        elif tipo in ("blur", "visibility_hidden", "resize_suspeito"):
            item["saidas_aba"] += 1

    dados = []
    notas: List[float] = []
    for r in respostas:
        resps = json.loads(r["respostas"])
        acertos = ProvaService.contar_acertos(questoes, resps)
        ev = eventos_por_aluno.get(r["nome_aluno"], {})
        notas.append(float(r["nota"]))
        dados.append(
            {
                "nome_aluno": r["nome_aluno"],
                "numero_aluno": ev.get("numero_aluno", "-"),
                "nota": r["nota"],
                "acertos": acertos,
                "total": len(questoes),
                "respondida_em": r["respondida_em"],
                "acessos": ev.get("acessos", 0),
                "saidas_aba": ev.get("saidas_aba", 0),
                "eventos_total": ev.get("eventos_total", 0),
            }
        )
    media = round(sum(notas) / len(notas), 1) if notas else 0.0
    maior = max(notas) if notas else 0.0
    menor = min(notas) if notas else 0.0
    return {
        "prova": prova_com_meta(prova),
        "resultados": dados,
        "estatisticas": {
            "alunos": len(respostas),
            "media_turma": media,
            "maior_nota": maior,
            "menor_nota": menor,
            "acessos_total": sum(v["acessos"] for v in eventos_por_aluno.values()),
            "saidas_aba_total": sum(v["saidas_aba"] for v in eventos_por_aluno.values()),
        },
    }


@app.get("/api/provas/{prova_id}/monitoramento")
def monitoramento_prova(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    validar_posse_prova(prova_id, x_auth_token)
    eventos = obter_eventos_prova(prova_id)
    estado: Dict[str, Dict[str, Any]] = {}
    for ev in eventos:
        nome = ev["nome_aluno"]
        if not nome:
            continue
        if nome not in estado:
            estado[nome] = {
                "nome": nome,
                "chamada": "-",
                "status": "offline",
                "vezes_saiu": 0,
                "ultimo_evento": "-",
                "detalhe_ultimo": "",
                "device_id": "-",
                "data_hora_ultima": "-",
                "aluno_acesso_id": None,
                "aluno_autorizado": False,
                "pode_desbloquear": False,
                "fraude_nome_nao_autorizado": False,
            }
        aluno = estado[nome]
        tipo = ev["evento"]
        detalhe = ev.get("detalhe", "")
        if tipo == "login":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Login"
            if "chamada" in detalhe.lower() and ":" in detalhe:
                aluno["chamada"] = detalhe.split(":")[-1].strip()
        elif tipo in ("blur", "visibility_hidden"):
            aluno["status"] = "fora_da_aba"
            aluno["vezes_saiu"] += 1
            aluno["ultimo_evento"] = "Saiu da aba"
        elif tipo == "resize_suspeito":
            aluno["status"] = "fora_da_aba"
            aluno["ultimo_evento"] = "Resize suspeito"
        elif tipo == "tentativa_bloqueada":
            aluno["ultimo_evento"] = "Tentativa bloqueada"
        elif tipo == "fraude_nome_nao_autorizado":
            aluno["status"] = "fraude"
            aluno["ultimo_evento"] = MENSAGEM_FRAUDE_NOME_NAO_AUTORIZADO
            aluno["detalhe_ultimo"] = MENSAGEM_FRAUDE_NOME_NAO_AUTORIZADO
            aluno["aluno_autorizado"] = False
            aluno["pode_desbloquear"] = False
            aluno["fraude_nome_nao_autorizado"] = True
        elif tipo == "aluno_desbloqueado":
            aluno["status"] = "ativo"
            aluno["ultimo_evento"] = "Aluno desbloqueado"
        elif tipo == "focus":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Voltou para aba"
        elif tipo == "submit":
            aluno["status"] = "finalizou"
            aluno["ultimo_evento"] = "Enviou prova"
        if tipo != "fraude_nome_nao_autorizado":
            aluno["detalhe_ultimo"] = detalhe
        aluno["data_hora_ultima"] = ev["timestamp"]

    estado_final: Dict[str, Dict[str, Any]] = {}
    nomes_com_acesso = set()

    for acesso in ProvaService.listar_aluno_acessos_prova(prova_id):
        nome = acesso.get("nome_aluno") or ""
        if not nome:
            continue
        nomes_com_acesso.add(nome)
        device_id = acesso.get("device_id") or "-"
        item = {
            **estado.get(
                nome,
                {
                    "nome": nome,
                    "chamada": "-",
                    "status": "offline",
                    "vezes_saiu": 0,
                    "ultimo_evento": "-",
                    "detalhe_ultimo": "",
                    "device_id": "-",
                    "data_hora_ultima": "-",
                    "aluno_acesso_id": None,
                    "aluno_autorizado": False,
                    "pode_desbloquear": False,
                    "fraude_nome_nao_autorizado": False,
                },
            )
        }
        status = acesso.get("status") or item["status"]
        motivo_bloqueio = acesso.get("motivo_bloqueio") or ""
        autorizado = bool(ProvaService.aluno_autorizado_prova(prova_id, nome))
        motivo_desbloqueavel = motivo_permite_desbloqueio(motivo_bloqueio)
        item["aluno_acesso_id"] = acesso.get("id")
        item["aluno_autorizado"] = autorizado
        item["pode_desbloquear"] = status == "bloqueado" and autorizado and motivo_desbloqueavel
        item["fraude_nome_nao_autorizado"] = (
            bool(item.get("fraude_nome_nao_autorizado")) and not autorizado
        )
        item["status"] = status
        item["device_id"] = device_id
        if status == "bloqueado":
            if not autorizado:
                item["ultimo_evento"] = MENSAGEM_FRAUDE_NOME_NAO_AUTORIZADO
                item["detalhe_ultimo"] = MENSAGEM_FRAUDE_NOME_NAO_AUTORIZADO
                item["fraude_nome_nao_autorizado"] = True
            else:
                item["ultimo_evento"] = "Aluno/dispositivo bloqueado"
                item["detalhe_ultimo"] = motivo_bloqueio or item["detalhe_ultimo"]
        elif status == "finalizado":
            item["ultimo_evento"] = "Enviou prova"
        elif status == "ativo" and item["ultimo_evento"] == "-":
            item["ultimo_evento"] = "Acesso ativo"
        if acesso.get("ultimo_evento_em"):
            item["data_hora_ultima"] = acesso["ultimo_evento_em"]
        estado_final[f"{nome}::{device_id}"] = item

    for nome, item in estado.items():
        if nome not in nomes_com_acesso:
            estado_final[f"{nome}::-"] = {
                **item,
                "aluno_acesso_id": None,
                "device_id": item.get("device_id") or "-",
                "pode_desbloquear": False,
            }

    return {"alunos": list(estado_final.values())}


@app.post("/api/provas/{prova_id}/aluno-acessos/{acesso_id}/desbloquear")
def desbloquear_aluno_monitoramento(
    prova_id: str,
    acesso_id: int,
    x_auth_token: Optional[str] = Header(default=None),
):
    validar_posse_prova(prova_id, x_auth_token)
    acesso_atual = ProvaService.buscar_aluno_acesso_por_id(prova_id, acesso_id)
    if not acesso_atual:
        raise HTTPException(status_code=404, detail="Acesso bloqueado nao encontrado.")
    if acesso_atual.get("status") != "bloqueado":
        raise HTTPException(status_code=400, detail="Este aluno/dispositivo nao esta bloqueado.")
    nome_acesso = acesso_atual.get("nome_aluno") or acesso_atual.get("nome_normalizado") or ""
    if not ProvaService.aluno_autorizado_prova(prova_id, nome_acesso):
        raise HTTPException(
            status_code=403,
            detail="Este aluno nao esta autorizado para esta prova e nao pode ser desbloqueado.",
        )
    if not motivo_permite_desbloqueio(acesso_atual.get("motivo_bloqueio")):
        raise HTTPException(
            status_code=403,
            detail="Este bloqueio nao pode ser desbloqueado pelo monitoramento.",
        )

    acesso = ProvaService.desbloquear_aluno_acesso(prova_id, acesso_id)
    if not acesso:
        raise HTTPException(status_code=404, detail="Acesso bloqueado nao encontrado.")

    detalhe = (
        f"Aluno/dispositivo desbloqueado pelo professor. "
        f"Device: {acesso.get('device_id') or '-'}. "
        f"Motivo anterior: {acesso.get('motivo_bloqueio') or '-'}"
    )
    registrar_evento(prova_id, acesso.get("nome_aluno") or "", "aluno_desbloqueado", detalhe)
    return {"ok": True, "acesso": acesso, "message": "Aluno desbloqueado com sucesso."}


@app.get("/api/aluno/provas/{prova_id}")
def buscar_prova_aluno(
    prova_id: str,
    token: Optional[str] = Query(default=None),
    device_id: Optional[str] = Query(default=None),
):
    acesso = validar_acesso_aluno(prova_id, token)
    prova = ProvaService.buscar_prova(prova_id)
    if not prova:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    questoes = json.loads(prova["questoes"])
    questoes_publicas = []
    for q in questoes:
        questoes_publicas.append(
            {
                "tipo": q.get("tipo", "multipla_escolha"),
                "enunciado": q.get("enunciado", ""),
                "opcoes": q.get("opcoes", []),
                "imagem": q.get("imagem"),
                "imagens_opcoes": q.get("imagens_opcoes", []),
            }
        )
    return {
        "id": prova["id"],
        "titulo": prova["titulo"],
        "materia": prova["materia"],
        "questoes": questoes_publicas,
        "expira_em": format_expira_em(acesso.get("expira_em")),
    }


@app.post("/api/aluno/provas/{prova_id}/login")
def aluno_login(prova_id: str, payload: AlunoLoginPayload):
    validar_acesso_aluno(prova_id, payload.token)
    prova = ProvaService.buscar_prova(prova_id)
    if not prova:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    nome = payload.nome_aluno.strip()
    numero = payload.numero.strip()
    device_id = validar_device_id(payload.device_id)
    if not nome or not numero:
        raise HTTPException(status_code=400, detail="Preencha nome e numero")
    requer_autorizacao = int(prova.get("requer_alunos_autorizados") or 0) == 1
    if requer_autorizacao and not ProvaService.aluno_autorizado_prova(prova_id, nome):
        detalhe = f"Nome informado nao esta na lista de alunos autorizados: {nome}"
        registrar_evento(prova_id, nome, "fraude_nome_nao_autorizado", detalhe)
        raise HTTPException(
            status_code=403,
            detail="Fraude detectada: seu nome nao esta autorizado para esta prova.",
        )
    garantir_acesso_individual_ativo(prova_id, payload.token, nome, device_id)
    if ProvaService.aluno_ja_respondeu(prova_id, nome):
        prova = ProvaService.buscar_prova(prova_id)
        questoes = json.loads(prova["questoes"])
        respostas = ProvaService.buscar_respostas(prova_id)
        nome_normalizado = normalizar_nome(nome)
        resp_aluno = next(
            (r for r in respostas if normalizar_nome(r["nome_aluno"]) == nome_normalizado),
            None,
        )
        if resp_aluno:
            respostas_aluno = json.loads(resp_aluno["respostas"])
            acertos = ProvaService.contar_acertos(questoes, respostas_aluno)
            return {
                "ok": True,
                "ja_entregue": True,
                "nota": resp_aluno["nota"],
                "acertos": acertos,
                "total": len(questoes),
            }
    registrar_evento(prova_id, nome, "login", f"Chamada: {numero}")
    return {"ok": True, "ja_entregue": False}


@app.post("/api/aluno/provas/{prova_id}/eventos")
def aluno_evento(prova_id: str, payload: EventoPayload):
    validar_acesso_aluno(prova_id, payload.token)
    prova = ProvaService.buscar_prova(prova_id)
    if not prova:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    nome = payload.nome_aluno.strip()
    device_id = (payload.device_id or "").strip()
    registrar_evento(prova_id, nome, payload.evento, payload.detalhe)
    if payload.evento in EVENTOS_BLOQUEIO_INDIVIDUAL and nome and device_id:
        requer_autorizacao = int(prova.get("requer_alunos_autorizados") or 0) == 1
        if requer_autorizacao and not ProvaService.aluno_autorizado_prova(prova_id, nome):
            return {"ok": True}
        ProvaService.criar_ou_atualizar_aluno_acesso(prova_id, payload.token, nome, device_id)
        ProvaService.bloquear_aluno_acesso(
            prova_id,
            payload.token,
            nome,
            device_id,
            payload.detalhe or payload.evento,
        )
    return {"ok": True}


@app.post("/api/aluno/provas/{prova_id}/responder")
def responder_prova(prova_id: str, payload: RespostaPayload):
    validar_acesso_aluno(prova_id, payload.token)
    prova = ProvaService.buscar_prova(prova_id)
    if not prova:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    nome = payload.nome_aluno.strip()
    device_id = validar_device_id(payload.device_id)
    if not nome:
        raise HTTPException(status_code=400, detail="Preencha todos os campos obrigatorios.")
    requer_autorizacao = int(prova.get("requer_alunos_autorizados") or 0) == 1
    if requer_autorizacao and not ProvaService.aluno_autorizado_prova(prova_id, nome):
        detalhe = f"Nome informado nao esta na lista de alunos autorizados: {nome}"
        registrar_evento(prova_id, nome, "fraude_nome_nao_autorizado", detalhe)
        raise HTTPException(
            status_code=403,
            detail="Fraude detectada: seu nome nao esta autorizado para esta prova.",
        )
    garantir_acesso_individual_ativo(prova_id, payload.token, nome, device_id)
    if ProvaService.aluno_ja_respondeu(prova_id, nome):
        raise HTTPException(status_code=400, detail="Aluno ja respondeu esta prova")
    questoes = json.loads(prova["questoes"])
    nota = ProvaService.calcular_nota(questoes, payload.respostas)
    ProvaService.salvar_resposta(prova_id, nome, payload.respostas, nota)
    registrar_evento(prova_id, nome, "submit")
    ProvaService.finalizar_aluno_acesso(prova_id, payload.token, nome, device_id)
    acertos = ProvaService.contar_acertos(questoes, payload.respostas)
    return {"nota": nota, "acertos": acertos, "total": len(questoes)}
