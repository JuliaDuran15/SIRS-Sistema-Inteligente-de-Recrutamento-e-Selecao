"""
Webhook de importação em massa — aceita JSON e XML.

Segurança: chave de API via cabeçalho X-Webhook-Key.
           Se WEBHOOK_SECRET_KEY não estiver configurada, o endpoint é aberto
           (útil em desenvolvimento).

Fluxo por chamada:
  1. Detecta Content-Type (application/json | application/xml | text/xml).
  2. Parseia o payload para ImportacaoPayload.
  3. Upsert de vagas → upsert de candidatos → candidaturas → currículos.
  4. Cada candidato é envolvido num savepoint para isolar falhas individuais.
  5. Retorna resumo de operações e lista de erros parciais.
"""
import json
import re
from datetime import date, datetime

import defusedxml.ElementTree as ET
from app.ai.resume_parser import vetorizar_texto
from app.ai.tasks import atualizar_mercado_vaga, processar_curriculo_texto
from app.api.deps import DB
from app.core.config import settings
from app.core.logger import get_logger
from app.core.rate_limit import checar_rate_limit
from app.models.candidato import Candidato
from app.models.candidatura import Candidatura, StatusCandidatura
from app.models.curriculo import Curriculo
from app.models.vaga import Vaga
from app.schemas.webhook import (
    AvisoDuplicata,
    CandidatoImport,
    ErroImportacao,
    FormacaoImport,
    ImportacaoPayload,
    ImportacaoResponse,
    ImportacaoResultado,
    VagaImport,
)
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session

logger = get_logger("WEBHOOK")

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter()


# ── Autenticação ──────────────────────────────────────────────────────────────

def _checar_api_key(api_key: str | None) -> None:
    chave = settings.WEBHOOK_SECRET_KEY
    if not chave:
        logger.warning("WEBHOOK_SECRET_KEY não configurada — endpoint aberto (inseguro em produção)")
        return
    if api_key != chave:
        raise HTTPException(status_code=401, detail="X-Webhook-Key inválida ou ausente")


# ── Parser XML ────────────────────────────────────────────────────────────────

def _parse_xml(body: bytes) -> ImportacaoPayload:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise HTTPException(status_code=400, detail=f"XML inválido: {exc}")

    fonte = root.get("fonte")

    vagas: list[VagaImport] = []
    for v in root.findall("vagas/vaga"):
        nome = v.findtext("nome", "").strip()
        req  = v.findtext("requisitos_texto", "").strip()
        if not nome or not req:
            continue
        vagas.append(VagaImport(
            external_id      = v.get("external_id"),
            nome             = nome,
            requisitos_texto = req,
        ))

    candidatos: list[CandidatoImport] = []
    for c in root.findall("candidatos/candidato"):
        nome  = c.findtext("nome",  "").strip()
        email = c.findtext("email", "").strip()
        if not nome or not email:
            continue

        formacao: list[FormacaoImport] = []
        for f in c.findall("formacao/item"):
            ano_txt = f.get("ano_conclusao") or f.findtext("ano_conclusao")
            try:
                formacao.append(FormacaoImport(
                    curso         = f.findtext("curso") or f.get("curso", ""),
                    instituicao   = f.findtext("instituicao") or f.get("instituicao", ""),
                    nivel         = f.get("nivel") or f.findtext("nivel") or "graduacao",
                    status        = f.get("status") or f.findtext("status") or "concluido",
                    ano_conclusao = int(ano_txt) if ano_txt else None,
                ))
            except Exception:
                pass

        dn: date | None = None
        dn_txt = c.findtext("data_nascimento")
        if dn_txt:
            try:
                dn = date.fromisoformat(dn_txt.strip())
            except ValueError:
                pass

        candidatos.append(CandidatoImport(
            external_id      = c.get("external_id"),
            nome             = nome,
            email            = email,
            telefone         = c.findtext("telefone"),
            data_nascimento  = dn,
            logradouro       = c.findtext("logradouro"),
            bairro           = c.findtext("bairro"),
            cidade           = c.findtext("cidade"),
            estado           = c.findtext("estado"),
            cep              = c.findtext("cep"),
            formacao         = formacao,
            curriculo_texto  = c.findtext("curriculo_texto"),
            linkedin_url     = c.findtext("linkedin_url") or c.get("linkedin_url"),
            portfolio_url    = c.findtext("portfolio_url") or c.get("portfolio_url"),
            vaga_external_id = c.get("vaga_external_id") or c.findtext("vaga_external_id"),
            vaga_nome        = c.findtext("vaga_nome"),
        ))

    return ImportacaoPayload(fonte=fonte, vagas=vagas, candidatos=candidatos)


# ── Lógica de importação ──────────────────────────────────────────────────────

def _importar(dados: ImportacaoPayload, db: Session) -> ImportacaoResponse:
    logger.info(
        f"fonte={dados.fonte or 'sem-fonte'} | "
        f"vagas={len(dados.vagas)} candidatos={len(dados.candidatos)}"
    )
    resultado = ImportacaoResultado()
    erros: list[ErroImportacao] = []
    avisos: list[AvisoDuplicata] = []
    vagas_map: dict[str, Vaga] = {}  # external_id → instância Vaga
    tasks_pendentes: list = []       # (func, args) — despachadas após db.commit()

    # ── 1. Vagas ──────────────────────────────────────────────────────────────
    for vd in dados.vagas:
        sp = db.begin_nested()
        try:
            vaga = db.query(Vaga).filter(Vaga.nome == vd.nome).first()
            if not vaga:
                vaga = Vaga(
                    nome             = vd.nome,
                    requisitos_texto = vd.requisitos_texto,
                    vetor_vaga       = vetorizar_texto(vd.requisitos_texto),
                )
                db.add(vaga)
                db.flush()
                tasks_pendentes.append((atualizar_mercado_vaga, [str(vaga.id)]))
                resultado.vagas_criadas += 1
            if vd.external_id:
                vagas_map[vd.external_id] = vaga
            sp.commit()
        except Exception as exc:
            sp.rollback()
            erros.append(ErroImportacao(
                tipo          = "vaga",
                identificador = vd.external_id or vd.nome,
                detalhe       = str(exc),
            ))

    # ── 2. Candidatos ─────────────────────────────────────────────────────────
    for cd in dados.candidatos:
        sp = db.begin_nested()
        try:
            if not _RE_EMAIL.match(cd.email):
                raise ValueError(f"Formato de e-mail inválido: {cd.email!r}")

            # Upsert por e-mail
            candidato = db.query(Candidato).filter(Candidato.email == cd.email).first()
            if candidato:
                for campo in ("nome", "telefone", "data_nascimento",
                              "logradouro", "bairro", "cidade", "estado", "cep",
                              "linkedin_url", "portfolio_url"):
                    val = getattr(cd, campo)
                    if val is not None:
                        setattr(candidato, campo, val)
                if cd.formacao:
                    candidato.formacao = [f.model_dump() for f in cd.formacao]
                resultado.candidatos_atualizados += 1
            else:
                candidato = Candidato(
                    nome            = cd.nome,
                    email           = cd.email,
                    telefone        = cd.telefone,
                    data_nascimento = cd.data_nascimento,
                    logradouro      = cd.logradouro,
                    bairro          = cd.bairro,
                    cidade          = cd.cidade,
                    estado          = cd.estado,
                    cep             = cd.cep,
                    formacao        = [f.model_dump() for f in cd.formacao],
                    linkedin_url    = cd.linkedin_url,
                    portfolio_url   = cd.portfolio_url,
                )
                db.add(candidato)
                db.flush()
                resultado.candidatos_criados += 1

            # ── 3. Candidatura ────────────────────────────────────────────────
            vaga: Vaga | None = None
            if cd.vaga_external_id:
                vaga = vagas_map.get(cd.vaga_external_id)
            if vaga is None and cd.vaga_nome:
                vaga = db.query(Vaga).filter(Vaga.nome == cd.vaga_nome).first()

            candidatura: Candidatura | None = None
            if vaga:
                candidatura = db.query(Candidatura).filter(
                    Candidatura.candidato_id == candidato.id,
                    Candidatura.vaga_id      == vaga.id,
                ).first()
                if not candidatura:
                    candidatura = Candidatura(
                        candidato_id = candidato.id,
                        vaga_id      = vaga.id,
                        status       = StatusCandidatura.NOVO,
                        historico    = [],
                        origem       = "externo",
                        fonte        = dados.fonte,
                    )
                    db.add(candidatura)
                    db.flush()
                    resultado.candidaturas_criadas += 1
                else:
                    # Candidatura já existe — mesmo email para a mesma vaga
                    avisos.append(AvisoDuplicata(
                        email     = candidato.email,
                        nome      = candidato.nome,
                        vaga_nome = vaga.nome,
                    ))
                    logger.warning(
                        f"duplicata_detectada | fonte={dados.fonte or 'sem-fonte'} | "
                        f"email={candidato.email} | vaga={vaga.nome} | "
                        f"candidatura_id={candidatura.id}"
                    )
                    novo_historico = list(candidatura.historico or [])
                    novo_historico.append({
                        "tipo"  : "resubmissao_duplicata",
                        "detalhe": (
                            f"Re-submissão detectada via webhook "
                            f"(fonte: {dados.fonte or 'sem-fonte'}). "
                            "Candidatura já existia — nenhuma alteração feita."
                        ),
                        "em"    : datetime.utcnow().isoformat(),
                    })
                    candidatura.historico = novo_historico

            # ── 4. Currículo ──────────────────────────────────────────────────
            if cd.curriculo_texto and candidatura:
                curriculo = db.query(Curriculo).filter(
                    Curriculo.candidatura_id == candidatura.id
                ).first()
                texto_mudou = True
                if not curriculo:
                    curriculo = Curriculo(
                        candidatura_id = candidatura.id,
                        texto_extraido = cd.curriculo_texto,
                    )
                    db.add(curriculo)
                    db.flush()
                else:
                    texto_mudou = curriculo.texto_extraido != cd.curriculo_texto
                    if texto_mudou:
                        curriculo.texto_extraido = cd.curriculo_texto
                if texto_mudou:
                    # Avança status para ativar o spinner no frontend enquanto a task roda
                    if candidatura.status == StatusCandidatura.NOVO:
                        candidatura.status = StatusCandidatura.AGUARDANDO_PROC
                    tasks_pendentes.append((processar_curriculo_texto, [str(candidatura.id), cd.curriculo_texto]))
                    resultado.curriculos_processados += 1

            sp.commit()

        except Exception as exc:
            sp.rollback()
            erros.append(ErroImportacao(
                tipo          = "candidato",
                identificador = cd.external_id or cd.email,
                detalhe       = str(exc),
            ))

    db.commit()

    # Despacha tasks somente após commit — evita race condition onde o worker
    # tenta ler registros que ainda não foram visíveis para outras sessões.
    for task_fn, task_args in tasks_pendentes:
        task_fn.delay(*task_args)

    if erros:
        logger.warning(
            f"fonte={dados.fonte or 'sem-fonte'} | {len(erros)} erro(s): "
            + "; ".join(f"{e.tipo}/{e.identificador}: {e.detalhe}" for e in erros[:5])
        )
    logger.info(
        f"fonte={dados.fonte or 'sem-fonte'} | importação concluída | "
        f"vagas_criadas={resultado.vagas_criadas} "
        f"candidatos_criados={resultado.candidatos_criados} "
        f"candidatos_atualizados={resultado.candidatos_atualizados} "
        f"candidaturas_criadas={resultado.candidaturas_criadas} "
        f"curriculos={resultado.curriculos_processados}"
    )
    return ImportacaoResponse(
        importados   = resultado,
        erros        = erros,
        total_erros  = len(erros),
        avisos       = avisos,
        total_avisos = len(avisos),
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/importar", response_model=ImportacaoResponse)
async def importar(
    request : Request,
    db      : Session = DB,
    api_key : str | None = Header(None, alias="X-Webhook-Key"),
):
    """
    Importa candidatos, vagas e candidaturas de sistemas externos.

    Aceita **application/json** ou **application/xml** / **text/xml**.

    ### Estrutura JSON
    ```json
    {
      "fonte": "greenhouse",
      "vagas": [
        { "external_id": "v1", "nome": "Dev Python", "requisitos_texto": "Python, FastAPI" }
      ],
      "candidatos": [
        {
          "external_id": "c1",
          "nome": "João Silva",
          "email": "joao@example.com",
          "curriculo_texto": "Desenvolvedor com 5 anos...",
          "vaga_external_id": "v1"
        }
      ]
    }
    ```

    ### Estrutura XML
    ```xml
    <importacao fonte="greenhouse">
      <vagas>
        <vaga external_id="v1">
          <nome>Dev Python</nome>
          <requisitos_texto>Python, FastAPI</requisitos_texto>
        </vaga>
      </vagas>
      <candidatos>
        <candidato external_id="c1" vaga_external_id="v1">
          <nome>João Silva</nome>
          <email>joao@example.com</email>
          <curriculo_texto>Desenvolvedor com 5 anos...</curriculo_texto>
        </candidato>
      </candidatos>
    </importacao>
    ```
    """
    _checar_api_key(api_key)
    await checar_rate_limit(request, max_por_hora=120, max_por_minuto=15)

    content_type = request.headers.get("content-type", "").lower()
    body = await request.body()

    if not body:
        raise HTTPException(status_code=400, detail="Corpo da requisição vazio")

    if "xml" in content_type:
        payload = _parse_xml(body)
    else:
        try:
            payload = ImportacaoPayload.model_validate(json.loads(body))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"JSON inválido: {exc}")

    if not payload.vagas and not payload.candidatos:
        raise HTTPException(status_code=400, detail="Payload sem vagas nem candidatos")

    return _importar(payload, db)
