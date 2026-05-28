from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import json
import uuid

from auth.professor import AuthService
from prova.services import ProvaService
from eventos.rastreamento import registrar_evento, obter_eventos_prova
from core.constants import MATERIAS_PADRAO


app = FastAPI(title="Prova Facil API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


class AlunoLoginPayload(BaseModel):
    nome_aluno: str
    numero: str


class EventoPayload(BaseModel):
    nome_aluno: str
    evento: str
    detalhe: str = ""


class RespostaPayload(BaseModel):
    nome_aluno: str
    respostas: Dict[str, Any]


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


@app.get("/api/provas")
def listar_provas(x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    provas = ProvaService.listar_provas(user["usuario_id"])
    return [prova_com_meta(p) for p in provas]


@app.get("/api/provas/{prova_id}")
def detalhar_prova(prova_id: str, x_auth_token: Optional[str] = Header(default=None)):
    prova = validar_posse_prova(prova_id, x_auth_token)
    return prova_com_meta(prova)


@app.post("/api/provas")
def criar_prova(payload: ProvaCreatePayload, x_auth_token: Optional[str] = Header(default=None)):
    user = get_user_from_token(x_auth_token)
    prova_id = ProvaService.salvar_prova(
        user["usuario_id"], payload.materia.strip(), payload.titulo.strip(), payload.questoes
    )
    return {"id": prova_id}


@app.put("/api/provas/{prova_id}")
def atualizar_prova(
    prova_id: str, payload: ProvaCreatePayload, x_auth_token: Optional[str] = Header(default=None)
):
    validar_posse_prova(prova_id, x_auth_token)
    ProvaService.atualizar_prova(prova_id, payload.materia.strip(), payload.titulo.strip(), payload.questoes)
    return {"ok": True}


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
        elif tipo == "blur":
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
                "data_hora_ultima": "-",
            }
        aluno = estado[nome]
        tipo = ev["evento"]
        detalhe = ev.get("detalhe", "")
        if tipo == "login":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Login"
            if "chamada" in detalhe.lower() and ":" in detalhe:
                aluno["chamada"] = detalhe.split(":")[-1].strip()
        elif tipo == "blur":
            aluno["status"] = "fora_da_aba"
            aluno["vezes_saiu"] += 1
            aluno["ultimo_evento"] = "Saiu da aba"
        elif tipo == "focus":
            aluno["status"] = "online"
            aluno["ultimo_evento"] = "Voltou para aba"
        elif tipo == "submit":
            aluno["status"] = "finalizou"
            aluno["ultimo_evento"] = "Enviou prova"
        aluno["data_hora_ultima"] = ev["timestamp"]

    return {"alunos": list(estado.values())}


@app.get("/api/aluno/provas/{prova_id}")
def buscar_prova_aluno(prova_id: str):
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
    }


@app.post("/api/aluno/provas/{prova_id}/login")
def aluno_login(prova_id: str, payload: AlunoLoginPayload):
    prova = ProvaService.buscar_prova(prova_id)
    if not prova:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    nome = payload.nome_aluno.strip()
    numero = payload.numero.strip()
    if not nome or not numero:
        raise HTTPException(status_code=400, detail="Preencha nome e numero")
    if ProvaService.aluno_ja_respondeu(prova_id, nome):
        prova = ProvaService.buscar_prova(prova_id)
        questoes = json.loads(prova["questoes"])
        respostas = ProvaService.buscar_respostas(prova_id)
        resp_aluno = next((r for r in respostas if r["nome_aluno"] == nome), None)
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
    prova = ProvaService.buscar_prova(prova_id)
    if not prova:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    registrar_evento(prova_id, payload.nome_aluno.strip(), payload.evento, payload.detalhe)
    return {"ok": True}


@app.post("/api/aluno/provas/{prova_id}/responder")
def responder_prova(prova_id: str, payload: RespostaPayload):
    prova = ProvaService.buscar_prova(prova_id)
    if not prova:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    nome = payload.nome_aluno.strip()
    if ProvaService.aluno_ja_respondeu(prova_id, nome):
        raise HTTPException(status_code=400, detail="Aluno ja respondeu esta prova")
    questoes = json.loads(prova["questoes"])
    nota = ProvaService.calcular_nota(questoes, payload.respostas)
    ProvaService.salvar_resposta(prova_id, nome, payload.respostas, nota)
    registrar_evento(prova_id, nome, "submit")
    acertos = ProvaService.contar_acertos(questoes, payload.respostas)
    return {"nota": nota, "acertos": acertos, "total": len(questoes)}
