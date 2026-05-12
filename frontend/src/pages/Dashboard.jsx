import { useState, useEffect } from "react"
import { getAnalyticsResumo, getAnalyticsFunil, getAnalyticsScores, getVagas } from "../api"
import {
  IconBriefcase, IconUsers, IconActivity, IconCheckCircle,
  IconCalendar, IconClock, IconFilter,
} from "../components/Icons"

const COR_ETAPA = {
  green  : { bg: "rgba(26,170,128,0.18)",  bar: "#2EE8B4", text: "#2EE8B4"  },
  blue   : { bg: "rgba(26,139,191,0.18)",  bar: "#4DC8E8", text: "#4DC8E8"  },
  amber  : { bg: "rgba(245,158,11,0.15)",  bar: "#FCD34D", text: "#FCD34D"  },
  red    : { bg: "rgba(239,68,68,0.15)",   bar: "#FCA5A5", text: "#FCA5A5"  },
  purple : { bg: "rgba(167,139,250,0.15)", bar: "#C4B5FD", text: "#C4B5FD"  },
  gray   : { bg: "rgba(100,116,139,0.12)", bar: "#94A3B8", text: "#94A3B8"  },
}

function Stat({ label, valor, cor = "#4DC8E8", sub, Icon }) {
  return (
    <div className="card-glass rounded-2xl p-5 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-bold text-brand-pale/40 uppercase tracking-wider leading-tight">{label}</p>
        {Icon && (
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: `${cor}1A`, color: cor }}
          >
            <Icon size={15} />
          </div>
        )}
      </div>
      <p className="text-3xl font-bold font-mono" style={{ color: cor }}>{valor ?? "—"}</p>
      {sub && <p className="text-xs text-brand-pale/35">{sub}</p>}
    </div>
  )
}

function Funil({ etapas, total }) {
  if (!etapas?.length) return (
    <p className="text-xs text-brand-pale/35 italic py-4 text-center">Nenhuma candidatura ainda.</p>
  )
  const max = Math.max(...etapas.map(e => e.quantidade))
  return (
    <div className="space-y-2.5">
      {etapas.map(e => {
        const c = COR_ETAPA[e.cor] ?? COR_ETAPA.gray
        const pct = total > 0 ? Math.round((e.quantidade / total) * 100) : 0
        return (
          <div key={e.status} className="flex items-center gap-3">
            <span className="text-xs text-brand-pale/50 w-44 truncate flex-shrink-0">{e.label}</span>
            <div className="flex-1 h-5 rounded-full overflow-hidden" style={{ background: "var(--s-track)" }}>
              <div className="h-full rounded-full transition-all duration-500"
                style={{ width: `${max > 0 ? (e.quantidade / max) * 100 : 0}%`, background: c.bar }} />
            </div>
            <span className="text-xs font-mono font-bold w-8 text-right flex-shrink-0" style={{ color: c.text }}>
              {e.quantidade}
            </span>
            <span className="text-xs text-brand-pale/30 w-8 flex-shrink-0">{pct}%</span>
          </div>
        )
      })}
    </div>
  )
}

const BAR_H = 96   // altura em px da área de barras

function HistogramaScores({ buckets, media, mediana }) {
  if (!buckets) return null
  const max = Math.max(...buckets.map(b => b.quantidade), 1)
  return (
    <div className="space-y-1">
      {/* Área de barras com altura fixa em px — sem % em flex */}
      <div className="flex items-end gap-1" style={{ height: BAR_H }}>
        {buckets.map(b => {
          const h = b.quantidade > 0 ? Math.max(Math.round((b.quantidade / max) * BAR_H), 4) : 0
          return (
            <div key={b.faixa} className="flex-1 flex flex-col justify-end" style={{ height: BAR_H }}>
              <div style={{
                height: h,
                background: h > 0 ? "linear-gradient(180deg, #4DC8E8, #1A8BBF)" : "transparent",
                borderRadius: "3px 3px 0 0",
                transition: "height 0.4s ease",
              }} />
            </div>
          )
        })}
      </div>
      {/* Labels das faixas */}
      <div className="flex gap-1">
        {buckets.map(b => (
          <div key={b.faixa} className="flex-1 text-center">
            <p className="text-xs text-brand-pale/30 font-mono">{b.faixa.split("-")[0]}</p>
          </div>
        ))}
      </div>
      {/* Estatísticas */}
      {(media !== null || mediana !== null) && (
        <div className="flex gap-4 pt-2 justify-center border-t" style={{ borderColor: "var(--b-subtle)" }}>
          {media   !== null && <span className="text-xs text-brand-pale/50">Média: <strong style={{ color: "#4DC8E8" }}>{media}</strong></span>}
          {mediana !== null && <span className="text-xs text-brand-pale/50">Mediana: <strong style={{ color: "#2EE8B4" }}>{mediana}</strong></span>}
        </div>
      )}
    </div>
  )
}

export function Dashboard() {
  const [resumo, setResumo]           = useState(null)
  const [vagas, setVagas]             = useState([])
  const [vagaSel, setVagaSel]         = useState("")
  const [funil, setFunil]             = useState(null)
  const [scores, setScores]           = useState(null)
  const [loadingResumo, setLR]        = useState(true)
  const [loadingFunil, setLF]         = useState(false)
  const [loadingScores, setLS]        = useState(false)

  useEffect(() => {
    Promise.all([getAnalyticsResumo(), getVagas()])
      .then(([r, rv]) => { setResumo(r.data); setVagas(rv.data) })
      .finally(() => setLR(false))
    getAnalyticsFunil().then(r => setFunil(r.data))
  }, [])

  useEffect(() => {
    setLF(true)
    getAnalyticsFunil(vagaSel || undefined)
      .then(r => setFunil(r.data))
      .finally(() => setLF(false))

    if (vagaSel) {
      setLS(true)
      getAnalyticsScores(vagaSel)
        .then(r => setScores(r.data))
        .catch(() => setScores(null))
        .finally(() => setLS(false))
    } else {
      setScores(null)
    }
  }, [vagaSel])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-brand-cloud">Dashboard</h1>
        <p className="text-sm text-brand-pale/45 mt-1">Visão geral do processo seletivo</p>
      </div>

      {/* Cards de resumo */}
      {loadingResumo ? (
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => (
            <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
          ))}
        </div>
      ) : resumo && (
        <>
          <div className="grid grid-cols-4 gap-4">
            <Stat label="Vagas abertas"       valor={resumo.vagas_abertas}       cor="#2EE8B4" sub={resumo.vagas_pausadas ? `${resumo.vagas_pausadas} pausadas` : undefined} Icon={IconBriefcase} />
            <Stat label="Candidatos"          valor={resumo.candidatos_total}    cor="#4DC8E8" Icon={IconUsers} />
            <Stat label="Candidaturas ativas" valor={resumo.candidaturas_ativas} cor="#4DC8E8" sub={`${resumo.em_triagem} em triagem`} Icon={IconActivity} />
            <Stat label="Contratados"         valor={resumo.contratados_total}   cor="#2EE8B4" Icon={IconCheckCircle} />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Stat label="Entrevistas agendadas" valor={resumo.entrevistas_agendadas} cor="#FCD34D" Icon={IconCalendar} />
            <Stat label="Decisões pendentes"    valor={resumo.decisoes_pendentes}    cor="#FCD34D" Icon={IconClock} />
            <Stat label="Em triagem"            valor={resumo.em_triagem}            cor="#FCD34D" Icon={IconFilter} />
          </div>
        </>
      )}

      {/* Filtro por vaga */}
      <div className="flex items-center gap-4">
        <label className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider flex-shrink-0">
          Filtrar por vaga:
        </label>
        <select
          value={vagaSel}
          onChange={e => setVagaSel(e.target.value)}
          className="rounded-xl px-4 py-2.5 text-sm flex-1 max-w-xs transition-all">
          <option value="">Todas as vagas</option>
          {vagas.map(v => <option key={v.id} value={v.id}>{v.nome}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Funil */}
        <div className="card-glass rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
              Funil do processo
            </h2>
            {funil?.total > 0 && (
              <span className="text-xs text-brand-pale/35 font-mono">{funil.total} candidaturas</span>
            )}
          </div>
          {loadingFunil ? (
            <div className="space-y-2">
              {[1,2,3,4,5].map(i => (
                <div key={i} className="h-5 rounded animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
              ))}
            </div>
          ) : (
            <Funil etapas={funil?.etapas} total={funil?.total} />
          )}
        </div>

        {/* Distribuição de scores */}
        <div className="card-glass rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
              Distribuição de scores
            </h2>
            {scores && (
              <span className="text-xs text-brand-pale/35 font-mono">score curricular</span>
            )}
          </div>
          {!vagaSel ? (
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <p className="text-xs text-brand-pale/35">Selecione uma vaga para ver a distribuição de scores.</p>
            </div>
          ) : loadingScores ? (
            <div className="h-32 rounded animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
          ) : scores ? (
            <HistogramaScores buckets={scores.buckets} media={scores.media} mediana={scores.mediana} />
          ) : (
            <p className="text-xs text-brand-pale/35 italic text-center py-8">Nenhum currículo processado para esta vaga.</p>
          )}
        </div>
      </div>
    </div>
  )
}
