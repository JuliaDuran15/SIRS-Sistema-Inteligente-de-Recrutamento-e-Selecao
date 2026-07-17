import { useState, useEffect, useCallback, useRef } from "react"
import { Link } from "react-router-dom"
import { getAuditoria, getVagas } from "../api"

const LIMIT = 20

// ── Labels de status (transições de candidatura) ─────────────────────────────
const STATUS_LABEL = {
  novo:                       "Candidatura criada",
  aguardando_processamento:   "Currículo enviado",
  processando_curriculo:      "Processando currículo",
  triagem_pendente:           "Triagem pendente",
  aprovado_triagem:           "Aprovado na triagem",
  reprovado_triagem:          "Reprovado na triagem",
  entrevista_rh_agendada:     "Entrevista RH agendada",
  entrevista_rh_realizada:    "Entrevista RH realizada",
  reprovado_rh:               "Reprovado na entrev. RH",
  entrevista_tec_agendada:    "Entrevista Técnica agendada",
  entrevista_tec_realizada:   "Entrevista Técnica realizada",
  reprovado_tecnico:          "Reprovado na entrev. técnica",
  decisao_pendente:           "Aguardando decisão",
  contratado:                 "Contratado",
  nao_aprovado:               "Não aprovado",
  banco_de_talentos:          "Banco de talentos",
  curriculo_processado:       "Currículo processado pela IA",
}

const COR_STATUS = {
  contratado:               "var(--ac-green)",
  aprovado_triagem:         "var(--ac-blue)",
  entrevista_rh_agendada:   "var(--ac-blue)",
  entrevista_tec_agendada:  "var(--ac-blue)",
  entrevista_rh_realizada:  "var(--ac-blue)",
  entrevista_tec_realizada: "var(--ac-blue)",
  curriculo_processado:     "var(--ac-purple)",
  decisao_pendente:         "var(--ac-yellow)",
  reprovado_triagem:        "var(--ac-red)",
  reprovado_rh:             "var(--ac-red)",
  reprovado_tecnico:        "var(--ac-red)",
  nao_aprovado:             "var(--ac-red)",
}

// ── Tipos de evento especial ──────────────────────────────────────────────────
const TIPO_CONFIG = {
  alteracao_email:     { label: "E-mail alterado",           cor: "var(--ac-amber)"  },
  vaga_criada:         { label: "Vaga criada",               cor: "var(--ac-green)"  },
  vaga_status:         { label: "Status da vaga",            cor: "var(--ac-blue)"   },
  pesos_alterados:     { label: "Pesos alterados",           cor: "var(--ac-purple)" },
  requisitos_alterados:{ label: "Requisitos alterados",      cor: "var(--ac-purple)" },
  candidatura_excluida:{ label: "Candidatura excluída",      cor: "var(--ac-red)"    },
  triagem_lote:        { label: "Triagem em lote",           cor: "var(--ac-blue)"   },
  resultado_entrevista:{ label: "Nota de entrevista",        cor: "var(--ac-yellow)" },
  login:               { label: "Login",                     cor: "var(--ac-green)"  },
  login_falha:         { label: "Tentativa de login falhou", cor: "var(--ac-red)"    },
  login_fora_horario:  { label: "Login fora do horário",     cor: "var(--ac-amber)"  },
}

// ── Lista unificada de opções de ação para o combobox ────────────────────────
const OPCOES_ACAO = [
  // Transições de candidatura (param: para=xxx)
  ...Object.entries(STATUS_LABEL).map(([k, v]) => ({ id: `status:${k}`, label: v, grupo: "Fluxo de candidatura" })),
  // Eventos especiais (param: tipo=xxx)
  { id: "tipo:vaga_criada",          label: "Vaga criada",               grupo: "Vagas" },
  { id: "tipo:vaga_status",          label: "Status da vaga alterado",   grupo: "Vagas" },
  { id: "tipo:pesos_alterados",      label: "Pesos alterados",           grupo: "Vagas" },
  { id: "tipo:requisitos_alterados", label: "Requisitos alterados",      grupo: "Vagas" },
  { id: "tipo:candidatura_excluida", label: "Candidatura excluída",      grupo: "Admin" },
  { id: "tipo:alteracao_email",      label: "E-mail alterado",           grupo: "Admin" },
  { id: "tipo:triagem_lote",         label: "Triagem em lote",           grupo: "Triagem" },
  { id: "tipo:resultado_entrevista", label: "Nota de entrevista",        grupo: "Entrevistas" },
  { id: "tipo:login",                label: "Login / Acesso",            grupo: "Segurança" },
]

// ── Combobox com busca por digitação ─────────────────────────────────────────
function ComboboxAcao({ value, onChange }) {
  const [texto, setTexto]       = useState("")
  const [aberto, setAberto]     = useState(false)
  const ref                     = useRef(null)

  const opcaoAtual = OPCOES_ACAO.find(o => o.id === value)

  useEffect(() => {
    if (!aberto) setTexto("")
  }, [aberto])

  useEffect(() => {
    function fechar(e) { if (ref.current && !ref.current.contains(e.target)) setAberto(false) }
    document.addEventListener("mousedown", fechar)
    return () => document.removeEventListener("mousedown", fechar)
  }, [])

  const filtradas = texto.trim()
    ? OPCOES_ACAO.filter(o => o.label.toLowerCase().includes(texto.toLowerCase()))
    : OPCOES_ACAO

  // Agrupa opções filtradas por grupo
  const porGrupo = filtradas.reduce((acc, o) => {
    ;(acc[o.grupo] = acc[o.grupo] || []).push(o)
    return acc
  }, {})

  function selecionar(opcao) {
    onChange(opcao ? opcao.id : "")
    setAberto(false)
    setTexto("")
  }

  return (
    <div ref={ref} className="relative">
      <div
        className="flex items-center gap-2 w-full rounded-xl px-3 py-2.5 text-sm cursor-pointer"
        style={{ background: "var(--s-input)", border: "1px solid var(--b-input)", color: "var(--t-base)" }}
        onClick={() => setAberto(v => !v)}
      >
        {aberto ? (
          <input
            autoFocus
            value={texto}
            onChange={e => setTexto(e.target.value)}
            onClick={e => e.stopPropagation()}
            placeholder="Digite para filtrar…"
            className="flex-1 bg-transparent outline-none text-sm"
            style={{ color: "var(--t-base)" }}
          />
        ) : (
          <span className="flex-1 truncate" style={{ color: opcaoAtual ? "var(--t-base)" : "var(--t-muted)" }}>
            {opcaoAtual ? opcaoAtual.label : "Todas as ações"}
          </span>
        )}
        <span className="text-brand-pale/30 text-xs flex-shrink-0">{aberto ? "▲" : "▼"}</span>
      </div>

      {aberto && (
        <div
          className="absolute z-50 w-full mt-1 rounded-xl shadow-2xl overflow-hidden"
          style={{ background: "var(--s-body-from)", border: "1px solid var(--b-strong)", maxHeight: 320, overflowY: "auto" }}
        >
          {/* Limpar filtro */}
          {value && (
            <button
              className="w-full text-left px-3 py-2 text-xs font-semibold transition-colors"
              style={{ color: "var(--ac-blue)", borderBottom: "1px solid var(--b-subtle)" }}
              onClick={() => selecionar(null)}
            >
              ✕ Limpar filtro de ação
            </button>
          )}
          {filtradas.length === 0 ? (
            <p className="px-3 py-3 text-xs text-brand-pale/35">Nenhuma ação encontrada</p>
          ) : (
            Object.entries(porGrupo).map(([grupo, opcoes]) => (
              <div key={grupo}>
                <p className="px-3 pt-2 pb-1 text-xs font-bold uppercase tracking-wider text-brand-pale/30">
                  {grupo}
                </p>
                {opcoes.map(o => (
                  <button
                    key={o.id}
                    className="w-full text-left px-3 py-2 text-xs transition-colors"
                    style={{
                      color: o.id === value ? "var(--ac-blue)" : "var(--t-muted2)",
                      background: o.id === value ? "rgba(77,200,232,0.08)" : "transparent",
                      fontWeight: o.id === value ? 600 : 400,
                    }}
                    onMouseEnter={e => { if (o.id !== value) e.currentTarget.style.background = "rgba(77,200,232,0.04)" }}
                    onMouseLeave={e => { if (o.id !== value) e.currentTarget.style.background = "transparent" }}
                    onClick={() => selecionar(o)}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmt(iso) {
  if (!iso) return "—"
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z")
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
}

function fmtDia(iso) {
  if (!iso) return ""
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z")
  return d.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })
}

function fmtHora(iso) {
  if (!iso) return "—"
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z")
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
}

function diaKey(iso) {
  if (!iso) return ""
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z")
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

// ── Badge de ação (compacto — sempre uma linha) ───────────────────────────────
function AcaoBadge({ evt }) {
  if (evt.tipo === "login") {
    const ex = evt.extra || {}
    if (!ex.sucesso) return <BadgeCompacto cor="var(--ac-red)" label="Login falhou" />
    if (ex.fora_horario) return <BadgeCompacto cor="var(--ac-amber)" label="Login fora do horário" />
    return <BadgeCompacto cor="var(--ac-green)" label="Login" />
  }
  if (evt.tipo && TIPO_CONFIG[evt.tipo]) {
    const cfg = TIPO_CONFIG[evt.tipo]
    return <BadgeCompacto cor={cfg.cor} label={cfg.label} />
  }
  const cor = COR_STATUS[evt.para] ?? "var(--ac-muted)"
  return <BadgeCompacto cor={cor} label={STATUS_LABEL[evt.para] ?? evt.para ?? "—"} />
}

function BadgeCompacto({ cor, label }) {
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cor }} />
      <p className="text-xs font-semibold leading-tight truncate" style={{ color: cor }}>{label}</p>
    </div>
  )
}

// ── Painel expandido — detalhes completos ─────────────────────────────────────
function PainelExpandido({ evt, bgAlerta }) {
  const linhas = []

  if (evt.tipo === "login") {
    const ex = evt.extra || {}
    if (!ex.sucesso) {
      const motivo = ex.motivo === "senha_incorreta" ? "Senha incorreta"
                   : ex.motivo === "usuario_desativado" ? "Usuário desativado"
                   : ex.motivo ?? "Falha"
      linhas.push(["Motivo", motivo])
    }
    if (ex.papel)        linhas.push(["Papel", ex.papel])
    if (ex.ip)           linhas.push(["IP", ex.ip])
    if (ex.fora_horario) linhas.push(["Aviso", "Login fora do horário comercial (seg–sex 07h–22h BRT)"])
  } else if (evt.tipo === "pesos_alterados") {
    linhas.push(["Antes", evt.de ?? "—"])
    linhas.push(["Depois", evt.para ?? "—"])
  } else if (evt.tipo === "alteracao_email") {
    linhas.push(["E-mail anterior", evt.de ?? "—"])
    linhas.push(["E-mail novo", evt.para ?? "—"])
  } else if (evt.tipo === "vaga_status") {
    linhas.push(["Status anterior", evt.de ?? "—"])
    linhas.push(["Novo status", evt.para ?? "—"])
  } else if (evt.tipo === "candidatura_excluida") {
    if (evt.de) linhas.push(["Status que estava", STATUS_LABEL[evt.de] ?? evt.de])
    if (evt.candidatura_id) linhas.push(["ID da candidatura", evt.candidatura_id])
  } else if (evt.tipo === "resultado_entrevista") {
    linhas.push(["Tipo de entrevista", evt.de ?? "—"])
    linhas.push(["Nota", evt.para ?? "—"])
    if (evt.extra?.reedicao) linhas.push(["Observação", "Reedição de resultado já registrado"])
  } else if (evt.tipo === "triagem_lote") {
    linhas.push(["Total no lote", String(evt.extra?.total ?? "?")])
    if (evt.para) linhas.push(["ID do lote", evt.para])
  } else if (!evt.tipo) {
    if (evt.de)  linhas.push(["De", STATUS_LABEL[evt.de]  ?? evt.de])
    if (evt.para) linhas.push(["Para", STATUS_LABEL[evt.para] ?? evt.para])
  }

  if (!linhas.length) return null

  return (
    <tr>
      <td colSpan={5} className="px-4 pb-3 pt-0">
        <div
          className="rounded-xl px-4 py-3 flex flex-wrap gap-x-8 gap-y-2"
          style={{ background: bgAlerta || "var(--ac-panel-bg)", border: "1px solid var(--ac-panel-border)" }}
        >
          {linhas.map(([k, v]) => (
            <div key={k} className="min-w-0">
              <p className="text-xs font-bold text-brand-pale/35 uppercase tracking-wider">{k}</p>
              <p className="text-xs font-mono mt-0.5 break-all" style={{ color: "var(--t-muted2)" }}>{v}</p>
            </div>
          ))}
        </div>
      </td>
    </tr>
  )
}

// ── Coluna Candidato / Usuário ────────────────────────────────────────────────
function ColunaEntidade({ evt }) {
  const nome  = evt.candidato_nome
  const email = evt.candidato_email

  if (!nome) return <span className="text-xs text-brand-pale/25">—</span>

  const linkTo = evt.candidato_id
    ? `/candidatos/${evt.candidato_id}`
    : evt.candidatura_id
    ? `/candidaturas/${evt.candidatura_id}/entrevistas`
    : null

  return (
    <div>
      {linkTo ? (
        <Link to={linkTo} className="text-xs font-semibold hover:text-brand-sky transition-colors" style={{ color: "var(--t-muted2)" }}>
          {nome}
        </Link>
      ) : (
        <span className="text-xs font-semibold" style={{ color: "var(--t-muted2)" }}>{nome}</span>
      )}
      {email && <p className="text-xs font-mono mt-0.5 text-brand-pale/30">{email}</p>}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────
export function Auditoria() {
  const [data, setData]         = useState({ eventos: [], total: 0 })
  const [vagas, setVagas]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [offset, setOffset]     = useState(0)

  const [filtroVaga, setFiltroVaga] = useState("")
  const [filtroAtor, setFiltroAtor] = useState("")
  const [filtroAcao, setFiltroAcao] = useState("") // "status:xxx" ou "tipo:xxx"
  const [expandidos, setExpandidos] = useState(new Set())

  function toggleExpandido(idx) {
    setExpandidos(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const temFiltro = filtroVaga || filtroAtor || filtroAcao

  const carregar = useCallback((off = 0) => {
    setLoading(true)
    const params = { limit: LIMIT, offset: off }
    if (filtroVaga) params.vaga_id = filtroVaga
    if (filtroAtor) params.ator    = filtroAtor
    if (filtroAcao.startsWith("status:")) params.para = filtroAcao.slice(7)
    if (filtroAcao.startsWith("tipo:"))   params.tipo = filtroAcao.slice(5)
    getAuditoria(params)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [filtroVaga, filtroAtor, filtroAcao])

  useEffect(() => { getVagas().then(r => setVagas(r.data)) }, [])

  useEffect(() => {
    setOffset(0)
    carregar(0)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroVaga, filtroAtor, filtroAcao])

  function paginar(novoOffset) {
    setOffset(novoOffset)
    carregar(novoOffset)
  }

  const totalPaginas = Math.ceil(data.total / LIMIT)
  const paginaAtual  = Math.floor(offset / LIMIT) + 1

  // Agrupa eventos por dia para separadores
  const eventosPorDia = []
  let diaAtual = null
  for (const evt of data.eventos) {
    const d = diaKey(evt.em)
    if (d !== diaAtual) {
      eventosPorDia.push({ tipo: "_dia", em: evt.em })
      diaAtual = d
    }
    eventosPorDia.push(evt)
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-brand-cloud">Auditoria</h1>
          <p className="text-sm text-brand-pale/45 mt-1 font-medium">
            {loading ? "Carregando…" : `${data.total} eventos`}
            {temFiltro && !loading && <span className="ml-2 text-brand-pale/30">· filtros ativos</span>}
          </p>
        </div>
        <button
          onClick={() => carregar(offset)}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl transition-all disabled:opacity-40"
          style={{ background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}
        >
          {loading
            ? <span className="w-3.5 h-3.5 border-2 rounded-full animate-spin" style={{ borderColor: "var(--b-normal)", borderTopColor: "var(--ac-blue)" }} />
            : <span>↻</span>}
          Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="card-glass rounded-2xl p-4 mb-5">
        <div className="flex flex-wrap gap-3 items-end">
          {/* Vaga */}
          <div className="flex-1 min-w-44">
            <label className="block text-xs font-bold text-brand-pale/40 uppercase tracking-wider mb-1.5">Vaga</label>
            <select
              value={filtroVaga}
              onChange={e => setFiltroVaga(e.target.value)}
              className="w-full rounded-xl px-3 py-2.5 text-sm"
            >
              <option value="">Todas as vagas</option>
              {vagas.map(v => <option key={v.id} value={v.id}>{v.nome}</option>)}
            </select>
          </div>

          {/* Ator */}
          <div className="flex-1 min-w-36">
            <label className="block text-xs font-bold text-brand-pale/40 uppercase tracking-wider mb-1.5">Realizado por</label>
            <input
              value={filtroAtor}
              onChange={e => setFiltroAtor(e.target.value)}
              placeholder="Nome do usuário…"
              className="w-full rounded-xl px-3 py-2.5 text-sm"
            />
          </div>

          {/* Tipo de ação — combobox com busca */}
          <div className="flex-1 min-w-52">
            <label className="block text-xs font-bold text-brand-pale/40 uppercase tracking-wider mb-1.5">Tipo de ação</label>
            <ComboboxAcao value={filtroAcao} onChange={setFiltroAcao} />
          </div>

          {temFiltro && (
            <button
              onClick={() => { setFiltroVaga(""); setFiltroAtor(""); setFiltroAcao("") }}
              className="px-3 py-2.5 text-xs font-semibold rounded-xl transition-colors"
              style={{ color: "var(--t-muted)", border: "1px solid var(--b-subtle)" }}
            >
              Limpar
            </button>
          )}
        </div>
      </div>

      {/* Conteúdo */}
      {loading ? (
        <div className="space-y-1.5">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="h-12 rounded-xl animate-pulse" style={{ background: "var(--s-skeleton-lt)", opacity: 1 - i * 0.12 }} />
          ))}
        </div>
      ) : data.eventos.length === 0 ? (
        <div className="text-center py-20 rounded-2xl border-2 border-dashed" style={{ borderColor: "var(--b-card)" }}>
          <p className="text-brand-pale/40 text-sm">Nenhum evento para os filtros aplicados.</p>
        </div>
      ) : (
        <div className="card-glass rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px]">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--ac-panel-border)" }}>
                  {[
                    { label: "Hora",        w: "w-24"  },
                    { label: "Ação",        w: "w-56"  },
                    { label: "Usuário / Candidato", w: "" },
                    { label: "Vaga",        w: "w-40"  },
                    { label: "Realizado por", w: "w-32" },
                  ].map(h => (
                    <th key={h.label} className={`px-3 py-2 text-left text-[10px] font-bold text-brand-pale/30 uppercase tracking-wider ${h.w}`}>
                      {h.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {eventosPorDia.map((evt, i) => {
                  // Separador de dia
                  if (evt.tipo === "_dia") {
                    return (
                      <tr key={`dia-${i}`}>
                        <td colSpan={5} className="px-4 pt-4 pb-1">
                          <p className="text-[10px] font-bold text-brand-pale/30 uppercase tracking-widest capitalize">
                            {fmtDia(evt.em)}
                          </p>
                        </td>
                      </tr>
                    )
                  }

                  const alertaLogin    = evt.tipo === "login" && evt.extra && (!evt.extra.sucesso || evt.extra.fora_horario)
                  const alertaExclusao = evt.tipo === "candidatura_excluida"
                  const bgAlerta = alertaLogin
                    ? (evt.extra?.sucesso ? "var(--ac-alert-amber)" : "var(--ac-alert-red)")
                    : alertaExclusao ? "var(--ac-alert-red)" : ""
                  const expandido = expandidos.has(i)

                  return (
                    <>
                      <tr
                        key={`row-${i}`}
                        onClick={() => toggleExpandido(i)}
                        style={{
                          borderBottom: expandido ? "none" : "1px solid var(--ac-row-border)",
                          background: expandido ? "var(--ac-row-hover)" : bgAlerta,
                          cursor: "pointer",
                        }}
                        onMouseEnter={e => { if (!expandido) e.currentTarget.style.background = "var(--ac-row-hover)" }}
                        onMouseLeave={e => { if (!expandido) e.currentTarget.style.background = bgAlerta }}
                      >
                        {/* Hora */}
                        <td className="px-3 py-2 whitespace-nowrap">
                          <span className="text-[11px] font-mono text-brand-pale/40">{fmtHora(evt.em)}</span>
                        </td>

                        {/* Ação */}
                        <td className="px-3 py-2">
                          <AcaoBadge evt={evt} />
                        </td>

                        {/* Entidade */}
                        <td className="px-3 py-2">
                          <ColunaEntidade evt={evt} />
                        </td>

                        {/* Vaga */}
                        <td className="px-3 py-2">
                          <span className="text-[11px] text-brand-pale/45 leading-tight">{evt.vaga_nome ?? "—"}</span>
                        </td>

                        {/* Ator + chevron */}
                        <td className="px-3 py-2">
                          <div className="flex items-center justify-between gap-2">
                            <span
                              className="inline-block text-[11px] font-semibold px-2 py-0.5 rounded-lg whitespace-nowrap"
                              style={
                                evt.ator === "sistema" || !evt.ator
                                  ? { background: "var(--ac-ator-purple-bg)", color: "var(--ac-purple)" }
                                  : { background: "var(--ac-ator-blue-bg)", color: "var(--ac-blue)" }
                              }
                            >
                              {evt.ator ?? "sistema"}
                            </span>
                            <span className="text-[10px] text-brand-pale/25 flex-shrink-0">
                              {expandido ? "▲" : "▾"}
                            </span>
                          </div>
                        </td>
                      </tr>

                      {expandido && (
                        <PainelExpandido key={`exp-${i}`} evt={evt} bgAlerta={bgAlerta} />
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Paginação */}
      {totalPaginas > 1 && (
        <div className="flex items-center justify-between mt-5">
          <p className="text-xs text-brand-pale/40 font-mono">
            {offset + 1}–{Math.min(offset + LIMIT, data.total)} de {data.total}
          </p>
          <div className="flex gap-1.5">
            <button
              disabled={paginaAtual === 1}
              onClick={() => paginar(offset - LIMIT)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-30"
              style={{ background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}
            >
              ← Anterior
            </button>
            {Array.from({ length: Math.min(totalPaginas, 7) }, (_, i) => {
              const pg = i + 1
              return (
                <button
                  key={pg}
                  onClick={() => paginar((pg - 1) * LIMIT)}
                  className="w-8 h-8 rounded-lg text-xs font-bold transition-all"
                  style={pg === paginaAtual
                    ? { background: "var(--ac-ator-blue-bg)", color: "var(--ac-blue)", border: "1px solid var(--b-normal)" }
                    : { background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}
                >
                  {pg}
                </button>
              )
            })}
            <button
              disabled={paginaAtual === totalPaginas}
              onClick={() => paginar(offset + LIMIT)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-30"
              style={{ background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}
            >
              Próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
