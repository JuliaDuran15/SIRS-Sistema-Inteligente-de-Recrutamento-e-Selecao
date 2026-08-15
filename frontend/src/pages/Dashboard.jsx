import { useState, useEffect, useRef, useCallback } from "react"
import { getAnalyticsResumo, getAnalyticsFunil, getAnalyticsScores, getAnalyticsScoresPorVaga, getAnalyticsTopSkills, getAnalyticsPreview, getVagas } from "../api"
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
    <div className="card-glass rounded-2xl p-5 flex flex-col gap-2 relative overflow-hidden">
      <div
        className="stat-accent-bar"
        style={{ background: `linear-gradient(90deg, ${cor}99, ${cor}22)` }}
      />
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

const STATUS_LABEL = {
  triagem_pendente         : "Triagem pendente",
  aprovado_triagem         : "Aprovado triagem",
  entrevista_rh_agendada   : "Entrev. RH agendada",
  entrevista_rh_realizada  : "Entrev. RH realizada",
  entrevista_tec_agendada  : "Entrev. Téc. agendada",
  entrevista_tec_realizada : "Entrev. Téc. realizada",
  decisao_pendente         : "Decisão pendente",
  contratado               : "Contratado",
  banco_de_talentos        : "Banco de talentos",
}

function StatComPreview({ tipo, label, valor, cor, sub, Icon }) {
  const [aberto, setAberto]   = useState(false)
  const [preso, setPreso]     = useState(false)
  const [items, setItems]     = useState(null)
  const [total, setTotal]     = useState(0)
  const [carregando, setCarr] = useState(false)
  const timerEntrar           = useRef(null)
  const timerSair             = useRef(null)
  const fetchedRef            = useRef(false)
  const wrapRef               = useRef(null)

  const carregar = useCallback(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    setCarr(true)
    getAnalyticsPreview(tipo, 100)
      .then(r => { setItems(r.data.items); setTotal(r.data.total) })
      .catch(() => setItems([]))
      .finally(() => setCarr(false))
  }, [tipo])

  const onMouseEnter = useCallback(() => {
    clearTimeout(timerSair.current)
    timerEntrar.current = setTimeout(() => {
      setAberto(true)
      carregar()
    }, 200)
  }, [carregar])

  const onMouseLeave = useCallback(() => {
    clearTimeout(timerEntrar.current)
    if (!preso) timerSair.current = setTimeout(() => setAberto(false), 120)
  }, [preso])

  const onClick = useCallback(() => {
    if (!aberto) { setAberto(true); carregar() }
    setPreso(p => !p)
  }, [aberto, carregar])

  // fechar ao clicar fora
  useEffect(() => {
    if (!preso) return
    function handleOut(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setPreso(false)
        setAberto(false)
      }
    }
    document.addEventListener("mousedown", handleOut)
    return () => document.removeEventListener("mousedown", handleOut)
  }, [preso])

  return (
    <div ref={wrapRef} className="relative"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* Card clicável */}
      <div onClick={onClick} className="cursor-pointer select-none">
        <Stat label={label} valor={valor} cor={cor} sub={sub} Icon={Icon} />
        {/* indicador de preso */}
        {preso && (
          <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full"
            style={{ background: cor, boxShadow: `0 0 6px ${cor}` }} />
        )}
      </div>

      {aberto && (
        <div
          className="absolute top-full left-0 mt-2 z-50 rounded-2xl min-w-[290px] max-w-xs"
          style={{
            background    : "var(--s-header)",
            border        : `1px solid ${preso ? cor + "55" : "var(--b-normal)"}`,
            boxShadow     : "0 8px 32px rgba(0,0,0,0.45)",
            backdropFilter: "blur(12px)",
          }}
          onMouseEnter={() => clearTimeout(timerSair.current)}
          onMouseLeave={onMouseLeave}
        >
          {/* Header do popover */}
          <div className="flex items-center justify-between px-4 pt-4 pb-2">
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: cor }}>
              {label}
              {total > 0 && (
                <span className="normal-case font-normal text-brand-pale/35 ml-1">— {total}</span>
              )}
            </p>
            <button
              onClick={() => { setPreso(false); setAberto(false) }}
              className="text-brand-pale/30 hover:text-brand-pale/70 transition-colors text-lg leading-none ml-3"
            >×</button>
          </div>

          <div className="px-4 pb-4">
            {carregando ? (
              <div className="space-y-1.5">
                {[1,2,3].map(i => (
                  <div key={i} className="h-10 rounded-xl animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
                ))}
              </div>
            ) : items?.length === 0 ? (
              <p className="text-xs text-brand-pale/35 italic py-2">Nenhuma candidatura no momento.</p>
            ) : (
              <div className="space-y-1.5 overflow-y-auto pr-1" style={{ maxHeight: 320 }}>
                {items.map(it => (
                  <div key={it.candidatura_id}
                    className="flex items-start justify-between gap-2 px-3 py-2.5 rounded-xl"
                    style={{ background: "var(--s-chip)" }}>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-brand-cloud truncate">{it.candidato_nome}</p>
                      <p className="text-[10px] text-brand-pale/40 truncate mt-0.5">{it.vaga_nome}</p>
                    </div>
                    <span className="text-[10px] font-bold flex-shrink-0 mt-0.5 text-right leading-tight"
                      style={{ color: cor }}>
                      {STATUS_LABEL[it.status] ?? it.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function Funil({ etapas, total }) {
  if (!etapas?.length) return (
    <p className="text-xs text-brand-pale/35 italic py-4 text-center">Nenhuma candidatura ainda.</p>
  )
  const max = Math.max(...etapas.map(e => e.quantidade))
  return (
    <div className="space-y-2">
      {etapas.map(e => {
        const c   = COR_ETAPA[e.cor] ?? COR_ETAPA.gray
        const pct = total > 0 ? (e.quantidade / total) * 100 : 0
        return (
          <div key={e.status} className="flex items-center gap-3">
            <span className="text-xs font-medium w-40 truncate flex-shrink-0" style={{ color: "var(--t-muted2)" }}>
              {e.label}
            </span>
            <div className="flex-1 h-4 rounded-full overflow-hidden" style={{ background: "var(--s-track)" }}>
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${max > 0 ? (e.quantidade / max) * 100 : 0}%`, background: c.bar }}
              />
            </div>
            <span className="text-xs font-mono font-bold w-7 text-right flex-shrink-0" style={{ color: c.text }}>
              {e.quantidade}
            </span>
            <span className="text-xs font-bold w-10 text-right flex-shrink-0 tabular-nums" style={{ color: c.text }}>
              {pct.toFixed(1)}%
            </span>
          </div>
        )
      })}
    </div>
  )
}

const BAR_H = 96

function _corFaixa(faixa) {
  const inicio = parseInt(faixa.split("-")[0], 10)
  if (inicio >= 70) return { top: "#2EE8B4", bot: "#1AAA80" }   // verde
  if (inicio >= 40) return { top: "#FCD34D", bot: "#B45309" }   // âmbar
  return           { top: "#FCA5A5", bot: "#B91C1C" }            // vermelho
}

function HistogramaScores({ buckets, media, mediana }) {
  if (!buckets) return null
  const max = Math.max(...buckets.map(b => b.quantidade), 1)
  return (
    <div className="space-y-1">
      <div className="flex items-end gap-1" style={{ height: BAR_H }}>
        {buckets.map(b => {
          const h   = b.quantidade > 0 ? Math.max(Math.round((b.quantidade / max) * BAR_H), 4) : 0
          const cor = _corFaixa(b.faixa)
          return (
            <div key={b.faixa} className="flex-1 flex flex-col justify-end group relative" style={{ height: BAR_H }}>
              {/* Tooltip */}
              {b.quantidade > 0 && (
                <span
                  className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 text-[10px] font-bold font-mono px-1.5 py-0.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10"
                  style={{ background: "var(--s-header)", border: "1px solid var(--b-normal)", color: "var(--t-main)" }}
                >
                  {b.quantidade}
                </span>
              )}
              <div style={{
                height: h,
                background: h > 0 ? `linear-gradient(180deg, ${cor.top}, ${cor.bot})` : "transparent",
                borderRadius: "3px 3px 0 0",
                transition: "height 0.4s ease",
              }} />
            </div>
          )
        })}
      </div>
      <div className="flex gap-1">
        {buckets.map(b => {
          const cor = _corFaixa(b.faixa)
          return (
            <div key={b.faixa} className="flex-1 text-center">
              <p className="text-[10px] font-mono font-semibold" style={{ color: cor.top, opacity: 0.7 }}>
                {b.faixa.split("-")[0]}
              </p>
            </div>
          )
        })}
      </div>
      {(media !== null || mediana !== null) && (
        <div className="flex gap-4 pt-2 justify-center border-t" style={{ borderColor: "var(--b-subtle)" }}>
          {media   !== null && <span className="text-xs text-brand-pale/50">Média: <strong style={{ color: "#4DC8E8" }}>{media}</strong></span>}
          {mediana !== null && <span className="text-xs text-brand-pale/50">Mediana: <strong style={{ color: "#2EE8B4" }}>{mediana}</strong></span>}
        </div>
      )}
    </div>
  )
}

function BarrasHorizontais({ itens, corBarra = "#4DC8E8", corTexto, formatarValor, emptyMsg }) {
  if (!itens?.length) return (
    <p className="text-xs text-brand-pale/35 italic py-6 text-center">{emptyMsg ?? "Sem dados."}</p>
  )
  const max = Math.max(...itens.map(i => i.valor), 1)
  return (
    <div className="space-y-2.5">
      {itens.map((item, idx) => (
        <div key={idx} className="flex items-center gap-3">
          <span className="text-xs text-brand-pale/50 truncate flex-shrink-0" style={{ width: 140 }}>
            {item.label}
          </span>
          <div className="flex-1 h-4 rounded-full overflow-hidden" style={{ background: "var(--s-track)" }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${(item.valor / max) * 100}%`, background: corBarra }}
            />
          </div>
          <span className="text-xs font-mono font-bold flex-shrink-0 w-12 text-right"
            style={{ color: corTexto ?? corBarra }}>
            {formatarValor ? formatarValor(item.valor) : item.valor}
          </span>
        </div>
      ))}
    </div>
  )
}

export function Dashboard() {
  const [resumo, setResumo]               = useState(null)
  const [vagas, setVagas]                 = useState([])
  const [vagaSel, setVagaSel]             = useState("")
  const [funil, setFunil]                 = useState(null)
  const [scores, setScores]               = useState(null)
  const [scoresPorVaga, setScoresPorVaga] = useState(null)
  const [topSkills, setTopSkills]         = useState(null)
  const [loadingResumo, setLR]            = useState(true)
  const [loadingFunil, setLF]             = useState(false)
  const [loadingScores, setLS]            = useState(false)
  const [loadingExtra, setLE]             = useState(true)

  useEffect(() => {
    Promise.all([getAnalyticsResumo(), getVagas()])
      .then(([r, rv]) => { setResumo(r.data); setVagas(rv.data) })
      .finally(() => setLR(false))
    getAnalyticsFunil().then(r => setFunil(r.data))
    Promise.all([getAnalyticsScoresPorVaga(), getAnalyticsTopSkills()])
      .then(([rs, rt]) => { setScoresPorVaga(rs.data); setTopSkills(rt.data) })
      .finally(() => setLE(false))
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
      getAnalyticsTopSkills(vagaSel)
        .then(r => setTopSkills(r.data))
        .catch(() => {})
    } else {
      setScores(null)
      getAnalyticsTopSkills().then(r => setTopSkills(r.data)).catch(() => {})
    }
  }, [vagaSel])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-brand-cloud">Dashboard</h1>
        <p className="text-sm mt-1" style={{ color: "var(--t-muted2)" }}>Visão geral do processo seletivo</p>
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
            <StatComPreview tipo="ativas" label="Candidaturas ativas" valor={resumo.candidaturas_ativas} cor="#4DC8E8" sub={`${resumo.em_triagem} em triagem`} Icon={IconActivity} />
            <StatComPreview tipo="contratados" label="Contratados" valor={resumo.contratados_total} cor="#2EE8B4" Icon={IconCheckCircle} />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <StatComPreview tipo="entrevistas_agendadas" label="Entrevistas agendadas" valor={resumo.entrevistas_agendadas} cor="#FCD34D" Icon={IconCalendar} />
            <StatComPreview tipo="decisoes_pendentes" label="Decisões pendentes" valor={resumo.decisoes_pendentes} cor="#FCD34D" Icon={IconClock} />
            <StatComPreview
              tipo="banco_de_talentos"
              label="Banco de talentos"
              valor={funil?.etapas?.find(e => e.status === "banco_de_talentos")?.quantidade ?? "—"}
              cor="#C4B5FD"
              Icon={IconUsers}
            />
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

      <div className="grid grid-cols-2 gap-6">
        {/* Score médio por vaga */}
        <div className="card-glass rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
              Score médio por vaga
            </h2>
            <span className="text-xs text-brand-pale/35 font-mono">top 10</span>
          </div>
          {loadingExtra ? (
            <div className="space-y-2">
              {[1,2,3,4].map(i => (
                <div key={i} className="h-4 rounded animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
              ))}
            </div>
          ) : (
            <BarrasHorizontais
              itens={scoresPorVaga?.vagas?.map(v => ({ label: v.vaga_nome, valor: v.score_medio }))}
              corBarra="linear-gradient(90deg, #1A8BBF, #2EE8B4)"
              corTexto="#2EE8B4"
              formatarValor={v => `${v}`}
              emptyMsg="Nenhum currículo processado ainda."
            />
          )}
        </div>

        {/* Top skills */}
        <div className="card-glass rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
              Top skills dos candidatos
            </h2>
            <span className="text-xs text-brand-pale/35 font-mono">
              {vagaSel && topSkills?.vaga_nome ? topSkills.vaga_nome : "todas as vagas"}
            </span>
          </div>
          {loadingExtra ? (
            <div className="space-y-2">
              {[1,2,3,4,5].map(i => (
                <div key={i} className="h-4 rounded animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
              ))}
            </div>
          ) : (
            <BarrasHorizontais
              itens={topSkills?.skills?.map(s => ({ label: s.skill, valor: s.contagem }))}
              corBarra="#7C3AED"
              corTexto="#C4B5FD"
              emptyMsg="Nenhuma skill detectada ainda."
            />
          )}
        </div>
      </div>
    </div>
  )
}
