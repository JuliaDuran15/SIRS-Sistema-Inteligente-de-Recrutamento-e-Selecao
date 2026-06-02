import { useState, useEffect, useCallback } from "react"
import { Link } from "react-router-dom"
import { getAuditoria, getVagas } from "../api"

const LIMIT = 50

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
  contratado:               "#2EE8B4",
  aprovado_triagem:         "#4DC8E8",
  entrevista_rh_agendada:   "#4DC8E8",
  entrevista_tec_agendada:  "#4DC8E8",
  entrevista_rh_realizada:  "#4DC8E8",
  entrevista_tec_realizada: "#4DC8E8",
  curriculo_processado:     "#A78BFA",
  decisao_pendente:         "#FCD34D",
  reprovado_triagem:        "#FCA5A5",
  reprovado_rh:             "#FCA5A5",
  reprovado_tecnico:        "#FCA5A5",
  nao_aprovado:             "#FCA5A5",
}

function fmt(iso) {
  if (!iso) return "—"
  const d = new Date(iso)
  return d.toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

function PontoCor({ para }) {
  const cor = COR_STATUS[para] ?? "rgba(125,216,240,0.3)"
  return (
    <span
      className="inline-block w-2 h-2 rounded-full flex-shrink-0 mt-0.5"
      style={{ background: cor }}
    />
  )
}

export function Auditoria() {
  const [data, setData]     = useState({ eventos: [], total: 0 })
  const [vagas, setVagas]   = useState([])
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)

  const [filtroVaga, setFiltroVaga] = useState("")
  const [filtroAtor, setFiltroAtor] = useState("")
  const [filtroPara, setFiltroPara] = useState("")

  const carregar = useCallback((off = 0) => {
    setLoading(true)
    const params = { limit: LIMIT, offset: off }
    if (filtroVaga) params.vaga_id = filtroVaga
    if (filtroAtor) params.ator    = filtroAtor
    if (filtroPara) params.para    = filtroPara
    getAuditoria(params)
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [filtroVaga, filtroAtor, filtroPara])

  useEffect(() => { getVagas().then(r => setVagas(r.data)) }, [])

  useEffect(() => {
    setOffset(0)
    carregar(0)
  }, [filtroVaga, filtroAtor, filtroPara])

  function paginar(novoOffset) {
    setOffset(novoOffset)
    carregar(novoOffset)
  }

  const totalPaginas = Math.ceil(data.total / LIMIT)
  const paginaAtual  = Math.floor(offset / LIMIT) + 1

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-brand-cloud">Auditoria</h1>
          <p className="text-sm text-brand-pale/45 mt-1 font-medium">
            {loading ? "Carregando..." : `${data.total} eventos registrados`}
          </p>
        </div>
        <button
          onClick={() => carregar(offset)}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl transition-all disabled:opacity-40"
          style={{ background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}>
          {loading ? (
            <span className="w-3.5 h-3.5 border-2 rounded-full animate-spin"
              style={{ borderColor: "var(--b-normal)", borderTopColor: "#4DC8E8" }} />
          ) : "↻"} Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="card-glass rounded-2xl p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
            Vaga
          </label>
          <select
            value={filtroVaga}
            onChange={e => setFiltroVaga(e.target.value)}
            className="w-full rounded-xl px-3 py-2.5 text-sm"
          >
            <option value="">Todas as vagas</option>
            {vagas.map(v => (
              <option key={v.id} value={v.id}>{v.nome}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-36">
          <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
            Ator
          </label>
          <input
            value={filtroAtor}
            onChange={e => setFiltroAtor(e.target.value)}
            placeholder="Nome do usuário…"
            className="w-full rounded-xl px-3 py-2.5 text-sm"
          />
        </div>

        <div className="flex-1 min-w-44">
          <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
            Tipo de ação
          </label>
          <select
            value={filtroPara}
            onChange={e => setFiltroPara(e.target.value)}
            className="w-full rounded-xl px-3 py-2.5 text-sm"
          >
            <option value="">Todas as ações</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        {(filtroVaga || filtroAtor || filtroPara) && (
          <button
            onClick={() => { setFiltroVaga(""); setFiltroAtor(""); setFiltroPara("") }}
            className="px-3 py-2.5 text-xs font-semibold rounded-xl transition-colors text-brand-pale/45 hover:text-brand-cloud"
            style={{ border: "1px solid var(--b-subtle)" }}
          >
            Limpar filtros
          </button>
        )}
      </div>

      {/* Tabela */}
      {loading ? (
        <div className="space-y-2">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="h-14 rounded-xl animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
          ))}
        </div>
      ) : data.eventos.length === 0 ? (
        <div className="text-center py-20 rounded-2xl border-2 border-dashed" style={{ borderColor: "var(--b-card)" }}>
          <p className="text-brand-pale/40 text-sm">Nenhum evento encontrado para os filtros aplicados.</p>
        </div>
      ) : (
        <div className="card-glass rounded-2xl">
          <div className="overflow-x-auto">
          <table className="w-full min-w-[700px]">
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(77,200,232,0.08)" }}>
                {["Data / Hora", "Ação", "Candidato", "Vaga", "Realizado por"].map(h => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-bold text-brand-pale/35 uppercase tracking-wider whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.eventos.map((evt, i) => (
                <tr
                  key={`${evt.candidatura_id}-${i}`}
                  className="transition-colors"
                  style={{
                    borderBottom: "1px solid rgba(77,200,232,0.05)",
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(77,200,232,0.03)"}
                  onMouseLeave={e => e.currentTarget.style.background = ""}
                >
                  {/* Data */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-xs font-mono text-brand-pale/45">{fmt(evt.em)}</span>
                  </td>

                  {/* Ação */}
                  <td className="px-4 py-3">
                    <div className="flex items-start gap-2">
                      <PontoCor para={evt.para} />
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-brand-pale/80 leading-tight">
                          {STATUS_LABEL[evt.para] ?? evt.para}
                        </p>
                        {evt.de && (
                          <p className="text-xs text-brand-pale/30 mt-0.5">
                            ← {STATUS_LABEL[evt.de] ?? evt.de}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Candidato */}
                  <td className="px-4 py-3">
                    <Link
                      to={`/candidaturas/${evt.candidatura_id}/entrevistas`}
                      className="text-xs font-semibold text-brand-pale/70 hover:text-brand-sky transition-colors"
                    >
                      {evt.candidato_nome}
                    </Link>
                    <p className="text-xs font-mono text-brand-pale/30 mt-0.5">{evt.candidato_email}</p>
                  </td>

                  {/* Vaga */}
                  <td className="px-4 py-3">
                    <span className="text-xs text-brand-pale/55">{evt.vaga_nome}</span>
                  </td>

                  {/* Ator */}
                  <td className="px-4 py-3">
                    <span
                      className="text-xs font-semibold px-2 py-0.5 rounded-lg"
                      style={
                        evt.ator === "sistema" || !evt.ator
                          ? { background: "rgba(167,139,250,0.12)", color: "#A78BFA" }
                          : { background: "rgba(26,139,191,0.12)", color: "#4DC8E8" }
                      }
                    >
                      {evt.ator ?? "sistema"}
                    </span>
                  </td>
                </tr>
              ))}
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
                    ? { background: "rgba(26,139,191,0.25)", color: "#4DC8E8", border: "1px solid rgba(26,139,191,0.4)" }
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
