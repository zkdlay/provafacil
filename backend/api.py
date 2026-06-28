from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import json
import os
import jwt

from auth.professor import AuthService
from prova.services import ProvaService
from eventos.rastreamento import registrar_evento, obter_eventos_prova
from core.constants import LINK_EXPIRATION_MINUTES, MATERIAS_PADRAO
from core.normalization import normalizar_nome


JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if os.getenv("RENDER"):
        raise RuntimeError("JWT_SECRET precisa estar configurado no Render.")
    JWT_SECRET = "dev-secret-change-me"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 12

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

@app.middleware("http")
async def log_auth_failures(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        token = request.headers.get("x-auth-token")
        print(
            "[AUTH_DEBUG] 401 response -> "
            f"method={request.method} endpoint={request.url.path} "
            f"x_auth_token_present={token is not None and token != ''} "
            f"token_size={len(token) if token else 0}"
        )
    return response

LETRAS_GABARITO = ["A", "B", "C", "D", "E"]


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
    embaralhar_questoes: bool = False
    valor_atividade: float = 10


class GabaritoUpdatePayload(BaseModel):
    questoes: List[Dict[str, Any]]


class ProvaAlterarPayload(BaseModel):
    questoes: List[Dict[str, Any]]
    embaralhar_questoes: bool = False
    valor_atividade: float = 10


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


def criar_token_professor(usuario_id: int, usuario_nome: str):
    expira_em = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "usuario_id": usuario_id,
        "usuario_nome": usuario_nome,
        "exp": expira_em,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_user_from_token(token: Optional[str]):
    token_present = bool(token)
    token_size = len(token) if token else 0
    print(
        "[AUTH_DEBUG] validating token -> "
        f"token_present={token_present} token_size={token_size}"
    )
    if not token:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Nao autenticado")

    usuario_id = payload.get("usuario_id")
    usuario_nome = payload.get("usuario_nome")
    if not usuario_id or not usuario_nome:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    return {"usuario_id": usuario_id, "usuario_nome": usuario_nome}


def validar_posse_prova(prova_id: str, token: Optional[str]):
    user = get_user_from_token(token)
    prova = ProvaService.buscar_prova(prova_id)
    if not prova or int(prova["usuario_id"]) != int(user["usuario_id"]):
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    return prova


def prova_com_meta(prova: Dict[str, Any]):
    questoes = json.loads(prova["questoes"])
    valor_atividade = ProvaService.valor_atividade_da_prova(prova)
    return {
        **prova,
        "quantidade_questoes": len(questoes),
        "embaralhar_questoes": bool(int(prova.get("embaralhar_questoes") or 0)),
        "valor_atividade": valor_atividade,
    }


def validar_valor_atividade(valor):
    try:
        valor_float = float(valor)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Informe um valor valido para a atividade.")
    if valor_float <= 0:
        raise HTTPException(status_code=400, detail="O valor da atividade deve ser maior que zero.")
    return round(valor_float, 2)


def validar_questoes_completas(questoes):
    if not questoes:
        raise HTTPException(status_code=400, detail="Adicione pelo menos uma questao.")
    if len(questoes) > 80:
        raise HTTPException(status_code=400, detail="A prova pode ter no maximo 80 questoes.")

    for indice, questao in enumerate(questoes):
        if not str(questao.get("enunciado") or "").strip():
            raise HTTPException(status_code=400, detail=f"Preencha o enunciado da questao {indice + 1}.")
        tipo = questao.get("tipo", "multipla_escolha")
        if tipo == "texto":
            if not str(questao.get("gabarito_texto") or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"Preencha o gabarito textual da questao {indice + 1}.",
                )
            continue

        opcoes = questao.get("opcoes") if isinstance(questao.get("opcoes"), list) else []
        if len(opcoes) < 2 or len(opcoes) > 5:
            raise HTTPException(
                status_code=400,
                detail=f"A questao {indice + 1} deve ter entre 2 e 5 alternativas.",
            )
        if any(not str(opcao or "").strip() for opcao in opcoes):
            raise HTTPException(
                status_code=400,
                detail=f"Preencha todas as alternativas da questao {indice + 1}.",
            )
        letras_validas = LETRAS_GABARITO[: len(opcoes)]
        gabarito = str(questao.get("gabarito") or "").strip().upper()
        if gabarito not in letras_validas:
            raise HTTPException(
                status_code=400,
                detail=f"Selecione um gabarito valido para a questao {indice + 1}.",
            )


def questoes_publicas(questoes, ordem=None):
    questoes_ordenadas = ProvaService.ordenar_questoes_por_ids(questoes, ordem) if ordem else questoes
    publicas = []
    for indice, questao in enumerate(questoes_ordenadas):
        publicas.append(
            {
                "id": ProvaService.questao_id(indice, questao),
                "tipo": questao.get("tipo", "multipla_escolha"),
                "enunciado": questao.get("enunciado", ""),
                "opcoes": questao.get("opcoes", []),
                "imagem": questao.get("imagem"),
                "imagens_opcoes": questao.get("imagens_opcoes", []),
            }
        )
    return publicas


def aplicar_gabaritos_atualizados(questoes_originais, questoes_payload):
    if len(questoes_originais) != len(questoes_payload):
        raise HTTPException(
            status_code=400,
            detail="A quantidade de questoes enviada nao confere com a prova.",
        )

    questoes_atualizadas = []
    for indice, questao_original in enumerate(questoes_originais):
        payload_questao = questoes_payload[indice] or {}
        tipo = questao_original.get("tipo", "multipla_escolha")
        questao = dict(questao_original)

        if tipo == "texto":
            gabarito_texto = str(payload_questao.get("gabarito_texto", "") or "").strip()
            if not gabarito_texto:
                raise HTTPException(
                    status_code=400,
                    detail=f"Preencha o gabarito textual da questao {indice + 1}.",
                )
            questao["gabarito_texto"] = gabarito_texto
        else:
            opcoes = questao_original.get("opcoes") if isinstance(questao_original.get("opcoes"), list) else []
            letras_validas = LETRAS_GABARITO[: len(opcoes)]
            gabarito = str(payload_questao.get("gabarito", "") or "").strip().upper()
            if not letras_validas:
                raise HTTPException(
                    status_code=400,
                    detail=f"A questao {indice + 1} nao possui alternativas validas.",
                )
            if gabarito not in letras_validas:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selecione um gabarito valido para a questao {indice + 1}.",
                )
            questao["gabarito"] = gabarito

        questoes_atualizadas.append(questao)

    return questoes_atualizadas


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


def aluno_tem_evento_desbloqueavel_recente(prova_id: str, nome_aluno: str):
    nome_referencia = normalizar_nome(nome_aluno)
    if not nome_referencia:
        return False

    for evento in reversed(obter_eventos_prova(prova_id)):
        if normalizar_nome(evento.get("nome_aluno") or "") != nome_referencia:
            continue
        return evento.get("evento") in EVENTOS_BLOQUEIO_INDIVIDUAL
    return False


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
    token = criar_token_professor(uid, payload.usuario.strip())
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


@app.get("/api/provas/{prova_id}/gabarito")
def obter_gabarito_prova(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    prova = validar_posse_prova(prova_id, x_auth_token)
    questoes = json.loads(prova["questoes"])
    return {
        "prova": {
            "id": prova["id"],
            "titulo": prova["titulo"],
            "materia": prova["materia"],
            "quantidade_questoes": len(questoes),
        },
        "questoes": questoes,
    }


@app.put("/api/provas/{prova_id}/gabarito")
def atualizar_gabarito_prova(
    prova_id: str,
    payload: GabaritoUpdatePayload,
    x_auth_token: Optional[str] = Header(default=None),
):
    prova = validar_posse_prova(prova_id, x_auth_token)
    questoes_originais = json.loads(prova["questoes"])
    questoes_atualizadas = aplicar_gabaritos_atualizados(questoes_originais, payload.questoes)
    respostas_recalculadas = ProvaService.atualizar_gabarito_e_recalcular(
        prova_id,
        questoes_atualizadas,
    )
    return {
        "ok": True,
        "message": "Gabarito atualizado e notas recalculadas.",
        "respostas_recalculadas": respostas_recalculadas,
        "questoes": questoes_atualizadas,
    }


@app.post("/api/provas")
def criar_prova(payload: ProvaCreatePayload, x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    validar_questoes_completas(payload.questoes)
    valor_atividade = validar_valor_atividade(payload.valor_atividade)
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
        user["usuario_id"],
        payload.materia.strip(),
        payload.titulo.strip(),
        payload.questoes,
        payload.embaralhar_questoes,
        valor_atividade,
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
        "valor_atividade": valor_atividade,
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


@app.get("/api/provas/{prova_id}/alterar")
def obter_prova_para_alteracao(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    prova = validar_posse_prova(prova_id, x_auth_token)
    questoes = json.loads(prova["questoes"])
    questoes = ProvaService.normalizar_questoes_para_salvar(questoes)
    return {
        "prova": {
            "id": prova["id"],
            "titulo": prova["titulo"],
            "materia": prova["materia"],
            "quantidade_questoes": len(questoes),
            "embaralhar_questoes": bool(int(prova.get("embaralhar_questoes") or 0)),
            "valor_atividade": ProvaService.valor_atividade_da_prova(prova),
        },
        "questoes": questoes,
    }


@app.put("/api/provas/{prova_id}/alterar")
def alterar_prova(
    prova_id: str,
    payload: ProvaAlterarPayload,
    x_auth_token: Optional[str] = Header(default=None),
):
    prova = validar_posse_prova(prova_id, x_auth_token)
    questoes_atuais = json.loads(prova["questoes"])
    questoes_normalizadas = ProvaService.normalizar_questoes_para_salvar(
        payload.questoes,
        questoes_atuais,
    )
    validar_questoes_completas(questoes_normalizadas)
    valor_atividade = validar_valor_atividade(payload.valor_atividade)
    recalculadas = ProvaService.alterar_prova_e_recalcular(
        prova_id,
        questoes_normalizadas,
        payload.embaralhar_questoes,
        valor_atividade,
    )
    return {
        "ok": True,
        "message": "Prova alterada e notas recalculadas.",
        "respostas_recalculadas": recalculadas,
        "quantidade_questoes": len(questoes_normalizadas),
        "embaralhar_questoes": payload.embaralhar_questoes,
        "valor_atividade": valor_atividade,
    }


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
    valor_atividade = ProvaService.valor_atividade_da_prova(prova)
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
        total_questoes = len(questoes)
        nota_recalculada = ProvaService.calcular_nota_por_acertos(
            acertos,
            total_questoes,
            valor_atividade,
        )
        ev = eventos_por_aluno.get(r["nome_aluno"], {})
        detalhes_respostas = []
        for idx, questao in enumerate(questoes):
            tipo = questao.get("tipo", "multipla_escolha")
            resposta_aluno = ProvaService.resposta_da_questao(resps, idx, questao)
            if tipo == "texto":
                gabarito = questao.get("gabarito_texto", "")
                correta = ProvaService.corrigir_resposta_texto(resposta_aluno, gabarito)
                detalhes_respostas.append(
                    {
                        "indice": idx,
                        "questao_id": ProvaService.questao_id(idx, questao),
                        "tipo": "texto",
                        "enunciado": questao.get("enunciado", ""),
                        "imagem": questao.get("imagem"),
                        "resposta_aluno": resposta_aluno or "",
                        "gabarito": gabarito,
                        "correta": correta,
                    }
                )
            else:
                opcoes = questao.get("opcoes") if isinstance(questao.get("opcoes"), list) else []
                gabarito = questao.get("gabarito", "")
                detalhes_respostas.append(
                    {
                        "indice": idx,
                        "questao_id": ProvaService.questao_id(idx, questao),
                        "tipo": "multipla_escolha",
                        "enunciado": questao.get("enunciado", ""),
                        "imagem": questao.get("imagem"),
                        "opcoes": opcoes,
                        "imagens_opcoes": questao.get("imagens_opcoes", []),
                        "resposta_aluno": resposta_aluno or "",
                        "resposta_texto": opcoes[ord(resposta_aluno) - ord("A")]
                        if isinstance(resposta_aluno, str)
                        and len(resposta_aluno) == 1
                        and 0 <= ord(resposta_aluno) - ord("A") < len(opcoes)
                        else "",
                        "gabarito": gabarito,
                        "gabarito_texto": opcoes[ord(gabarito) - ord("A")]
                        if isinstance(gabarito, str)
                        and len(gabarito) == 1
                        and 0 <= ord(gabarito) - ord("A") < len(opcoes)
                        else "",
                        "correta": resposta_aluno == gabarito,
                    }
                )
        notas.append(float(nota_recalculada))
        dados.append(
            {
                "id": r["id"],
                "nome_aluno": r["nome_aluno"],
                "numero_aluno": ev.get("numero_aluno", "-"),
                "nota": nota_recalculada,
                "valor_atividade": valor_atividade,
                "acertos": acertos,
                "total": total_questoes,
                "respondida_em": r["respondida_em"],
                "acessos": ev.get("acessos", 0),
                "saidas_aba": ev.get("saidas_aba", 0),
                "eventos_total": ev.get("eventos_total", 0),
                "respostas": detalhes_respostas,
            }
        )
    media = round(sum(notas) / len(notas), 2) if notas else 0.0
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
            "valor_atividade": valor_atividade,
            "acessos_total": sum(v["acessos"] for v in eventos_por_aluno.values()),
            "saidas_aba_total": sum(v["saidas_aba"] for v in eventos_por_aluno.values()),
        },
    }


@app.delete("/api/provas/{prova_id}/respostas/{resposta_id}")
def excluir_tentativa_aluno(
    prova_id: str,
    resposta_id: int,
    x_auth_token: Optional[str] = Header(default=None),
):
    validar_posse_prova(prova_id, x_auth_token)
    resposta = ProvaService.excluir_tentativa(prova_id, resposta_id)
    if not resposta:
        raise HTTPException(status_code=404, detail="Tentativa nao encontrada.")
    registrar_evento(
        prova_id,
        resposta.get("nome_aluno") or "",
        "tentativa_excluida_professor",
        "Professor excluiu a tentativa para permitir nova realizacao.",
    )
    return {
        "ok": True,
        "message": "Tentativa excluida. O aluno podera responder novamente se nao estiver bloqueado.",
        "resposta": {
            "id": resposta.get("id"),
            "nome_aluno": resposta.get("nome_aluno"),
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
                "evento_desbloqueavel": False,
            }
        aluno = estado[nome]
        tipo = ev["evento"]
        detalhe = ev.get("detalhe", "")
        if tipo == "login":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Login"
            aluno["evento_desbloqueavel"] = False
            if "chamada" in detalhe.lower() and ":" in detalhe:
                aluno["chamada"] = detalhe.split(":")[-1].strip()
        elif tipo in ("blur", "visibility_hidden"):
            aluno["status"] = "fora_da_aba"
            aluno["vezes_saiu"] += 1
            aluno["ultimo_evento"] = "Saiu da aba"
            aluno["evento_desbloqueavel"] = True
        elif tipo == "resize_suspeito":
            aluno["status"] = "fora_da_aba"
            aluno["ultimo_evento"] = "Resize suspeito"
            aluno["evento_desbloqueavel"] = True
        elif tipo == "acesso_bloqueado":
            aluno["status"] = "fora_da_aba"
            aluno["ultimo_evento"] = "Acesso bloqueado"
            aluno["evento_desbloqueavel"] = True
        elif tipo == "tentativa_bloqueada":
            aluno["ultimo_evento"] = "Tentativa bloqueada"
        elif tipo == "fraude_nome_nao_autorizado":
            aluno["status"] = "fraude"
            aluno["ultimo_evento"] = MENSAGEM_FRAUDE_NOME_NAO_AUTORIZADO
            aluno["detalhe_ultimo"] = MENSAGEM_FRAUDE_NOME_NAO_AUTORIZADO
            aluno["aluno_autorizado"] = False
            aluno["pode_desbloquear"] = False
            aluno["fraude_nome_nao_autorizado"] = True
            aluno["evento_desbloqueavel"] = False
        elif tipo == "aluno_desbloqueado":
            aluno["status"] = "ativo"
            aluno["ultimo_evento"] = "Aluno desbloqueado"
            aluno["evento_desbloqueavel"] = False
        elif tipo == "focus":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Voltou para aba"
        elif tipo == "submit":
            aluno["status"] = "finalizou"
            aluno["ultimo_evento"] = "Enviou prova"
            aluno["evento_desbloqueavel"] = False
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
        chave_estado = f"{nome}::{device_id}"
        if chave_estado in estado_final:
            continue
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
                    "evento_desbloqueavel": False,
                },
            )
        }
        status = acesso.get("status") or item["status"]
        motivo_bloqueio = acesso.get("motivo_bloqueio") or ""
        autorizado = bool(ProvaService.aluno_autorizado_prova(prova_id, nome))
        motivo_desbloqueavel = motivo_permite_desbloqueio(motivo_bloqueio)
        evento_desbloqueavel = not motivo_bloqueio and bool(item.get("evento_desbloqueavel"))
        item["aluno_acesso_id"] = acesso.get("id")
        item["aluno_autorizado"] = autorizado
        item["pode_desbloquear"] = (
            status == "bloqueado" and autorizado and (motivo_desbloqueavel or evento_desbloqueavel)
        )
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
        estado_final[chave_estado] = item

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
    motivo_atual = acesso_atual.get("motivo_bloqueio") or ""
    motivo_ou_evento_desbloqueavel = motivo_permite_desbloqueio(
        motivo_atual
    ) or (not motivo_atual and aluno_tem_evento_desbloqueavel_recente(prova_id, nome_acesso))
    if not motivo_ou_evento_desbloqueavel:
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
    return {
        "id": prova["id"],
        "titulo": prova["titulo"],
        "materia": prova["materia"],
        "aguardando_identificacao": True,
        "message": "Informe nome e numero para acessar a prova.",
        "expira_em": format_expira_em(acesso.get("expira_em")),
        "valor_atividade": ProvaService.valor_atividade_da_prova(prova),
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
    acesso_individual = garantir_acesso_individual_ativo(prova_id, payload.token, nome, device_id)
    questoes = json.loads(prova["questoes"])
    valor_atividade = ProvaService.valor_atividade_da_prova(prova)
    if ProvaService.aluno_ja_respondeu(prova_id, nome):
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
                "nota": ProvaService.calcular_nota(questoes, respostas_aluno, valor_atividade),
                "valor_atividade": valor_atividade,
                "acertos": acertos,
                "total": len(questoes),
            }
    registrar_evento(prova_id, nome, "login", f"Chamada: {numero}")
    embaralhar = bool(int(prova.get("embaralhar_questoes") or 0))
    ordem_salva = acesso_individual.get("questoes_ordem") if acesso_individual else None
    if ordem_salva:
        ordem = ProvaService.normalizar_ordem_questoes(questoes, ordem_salva)
    else:
        ordem = ProvaService.gerar_ordem_questoes(questoes, embaralhar)
    if not ordem_salva:
        ProvaService.salvar_ordem_questoes_aluno_acesso(
            prova_id,
            payload.token,
            nome,
            device_id,
            ordem,
        )
    return {
        "ok": True,
        "ja_entregue": False,
        "questoes": questoes_publicas(questoes, ordem),
        "valor_atividade": valor_atividade,
    }


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
    valor_atividade = ProvaService.valor_atividade_da_prova(prova)
    nota = ProvaService.calcular_nota(questoes, payload.respostas, valor_atividade)
    ProvaService.salvar_resposta(prova_id, nome, payload.respostas, nota)
    registrar_evento(prova_id, nome, "submit")
    ProvaService.finalizar_aluno_acesso(prova_id, payload.token, nome, device_id)
    acertos = ProvaService.contar_acertos(questoes, payload.respostas)
    return {
        "nota": nota,
        "valor_atividade": valor_atividade,
        "acertos": acertos,
        "total": len(questoes),
    }
