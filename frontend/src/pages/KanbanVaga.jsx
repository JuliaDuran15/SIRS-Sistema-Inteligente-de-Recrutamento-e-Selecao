import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { getVaga, getCandidaturas, atualizarStatusCandidatura } from "../api"
import { ScoreBar } from "../components/ScoreBar"

// ── Colunas ───────────────────────────────────────────────────────────────────
const COLUNAS = [
  { id: "triagem",       label: "Triagem",        cor: "#FCD34D", statuses: ["triagem_pendente"] },
  { id: "aprovados",     label: "Aprovados",       cor: "#4DC8E8", statuses: ["aprovado_triagem"] },
  { id: "entrevista_rh", label: "Entrevista RH",   cor: "#60A5FA", statuses: ["entrevista_rh_agendada", "entrevista_rh_realizada"] },
  { id: "entrevista_tec",label: "Entrevista Téc.", cor: "#A78BFA", statuses: ["entrevista_tec_agendada", "entrevista_tec_realizada"] },
  { id: "decisao",       label: "Decisão",         cor: "#FB923C", statuses: ["decisao_pendente"] },
  { id: "contratados",   label: "Contratados",     cor: "#2EE8B4", statuses: ["contratado"] },
  { id: "encerrados",    label: "Encerrados",      cor: "#FCA5A5", statuses: ["reprovado_triagem", "reprovado_rh", "reprovado_tecnico", "nao_aprovado", "banco_de_talentos"] },
]

const STATUS_LABEL = {
  triagem_pendente       : "Triagem pendente",
  aprovado_triagem       : "Aprovado",
  reprovado_triagem      : "Reprovado triagem",
  entrevista_rh_agendada : "Entrev. RH agendada",
  entrevista_rh_realizada: "Entrev. RH realizada",
  reprovado_rh           : "Reprovado RH",
  entrevista_tec_agendada: "Entrev. Téc. agendada",
  entrevista_tec_realizada:"Entrev. Téc. realizada",
  reprovado_tecnico      : "Reprovado Téc.",
  decisao_pendente       : "Decisão pendente",
  contratado             : "Contratado",
  nao_aprovado           : "Não aprovado",
  banco_de_talentos      : "Banco de talentos",
}

function resolverTransicao(fromStatus, toColId) {
  if (toColId === "aprovados"   && fromStatus === "triagem_pendente") return "aprovado_triagem"
  if (toColId === "encerrados"  && fromStatus === "triagem_pendente") return "reprovado_triagem"
  if (toColId === "contratados" && fromStatus === "decisao_pendente") return "contratado"
  if (toColId === "encerrados"  && fromStatus === "decisao_pendente") return "nao_aprovado"
  if (toColId === "encerrados"  && ["reprovado_triagem","reprovado_rh","reprovado_tecnico","nao_aprovado"].includes(fromStatus))
    return "banco_de_talentos"
  return null
}

// ── Card ──────────────────────────────────────────────────────────────────────
function CandidatoCard({ cand, isMoving, onDragStart }) {
  const cur      = cand.curriculo
  const score    = cur?.score_curriculo ?? cand.score_total ?? null
  const corScore = score >= 70 ? "#2EE8B4" : score >= 50 ? "#FCD34D" : score != null ? "#FCA5A5" : null
  const initials = (cand.candidato?.nome ?? "?").charAt(0).toUpperCase()
  const col      = COLUNAS.find(c => c.statuses.includes(cand.status))
  const corCol   = col?.cor ?? "#7DD8F0"

  return (
    <div
      draggable
      onDragStart={e => onDragStart(e, cand)}
      className="group rounded-2xl p-3.5 cursor-grab active:cursor-grabbing select-none transition-all"
      style={{
        background : "var(--s-section)",
        border     : "1px solid var(--b-card)",
        opacity    : isMoving ? 0.35 : 1,
        boxShadow  : "0 1px 4px rgba(0,0,0,0.18)",
      }}
    >
      {/* Topo: drag handle + avatar + nome + score */}
      <div className="flex items-start gap-2.5">
        {/* Drag handle */}
        <span
          className="mt-1 flex-shrink-0 text-brand-pale/20 group-hover:text-brand-pale/45 transition-colors"
          style={{ fontSize: "14px", lineHeight: 1, letterSpacing: "-1px" }}
        >
          ⠿
        </span>

        {/* Avatar */}
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold"
          style={{ background: `linear-gradient(135deg, ${corCol}55, ${corCol}33)`, color: corCol, border: `1px solid ${corCol}40` }}
        >
          {initials}
        </div>

        {/* Nome + email */}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-brand-cloud truncate leading-tight">
            {cand.candidato?.nome ?? "Candidato"}
          </p>
          <p className="text-xs text-brand-pale/35 font-mono truncate mt-0.5">
            {cand.candidato?.email}
          </p>
        </div>

        {/* Score */}
        {score != null && (
          <div
            className="flex-shrink-0 px-2 py-0.5 rounded-lg text-xs font-bold font-mono"
            style={{ background: `${corScore}18`, color: corScore }}
          >
            {score}
          </div>
        )}
      </div>

      {/* Barra de score RH */}
      {cur?.score_rh != null && (
        <div className="mt-2.5 pl-[3.75rem]">
          <ScoreBar score={cur.score_rh} showValue={false} />
        </div>
      )}

      {/* Status label */}
      <div className="mt-2.5 pl-[3.75rem]">
        <span
          className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full"
          style={{ background: `${corCol}18`, color: corCol }}
        >
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: corCol }} />
          {STATUS_LABEL[cand.status] ?? cand.status}
        </span>
      </div>
    </div>
  )
}

// ── Coluna ────────────────────────────────────────────────────────────────────
function Coluna({ coluna, cards, dragOver, onDragOver, onDragLeave, onDrop, movendo, loading }) {
  const isOver   = dragOver === coluna.id
  const canDrop  = isOver
  const hexAlpha = (hex, a) => hex + Math.round(a * 255).toString(16).padStart(2, "0")

  return (
    <div
      className="flex flex-col flex-shrink-0 rounded-2xl overflow-hidden transition-all"
      style={{
        width     : "256px",
        minWidth  : "256px",
        background: isOver ? hexAlpha(coluna.cor, 0.06) : "var(--s-skeleton-lt)",
        border    : `1px solid ${isOver ? coluna.cor + "80" : "var(--b-card)"}`,
        boxShadow : isOver ? `0 0 0 2px ${coluna.cor}25, 0 8px 24px ${coluna.cor}12` : "none",
        transition: "border-color 0.15s, box-shadow 0.15s, background 0.15s",
      }}
      onDragOver={e => onDragOver(e, coluna.id)}
      onDragLeave={onDragLeave}
      onDrop={e => onDrop(e, coluna.id)}
    >
      {/* Barra colorida no topo */}
      <div style={{ height: "3px", background: isOver ? coluna.cor : `${coluna.cor}55` , transition: "background 0.15s" }} />

      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: coluna.cor }}>
          {coluna.label}
        </span>
        {cards.length > 0 && (
          <span
            className="text-xs font-bold font-mono px-2 py-0.5 rounded-full"
            style={{ background: `${coluna.cor}20`, color: coluna.cor }}
          >
            {cards.length}
          </span>
        )}
      </div>

      {/* Divisor */}
      <div className="mx-3 mb-2" style={{ height: "1px", background: `${coluna.cor}20` }} />

      {/* Cards */}
      <div
        className="flex-1 px-2 pb-3 space-y-2 overflow-y-auto"
        style={{ maxHeight: "calc(100vh - 260px)", minHeight: "80px" }}
      >
        {loading ? (
          <>
            {[1, 2].map(i => (
              <div key={i} className="h-20 rounded-2xl animate-pulse" style={{ background: "var(--s-skeleton)" }} />
            ))}
          </>
        ) : cards.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center gap-1.5 py-6 rounded-xl border-2 border-dashed"
            style={{ borderColor: isOver ? coluna.cor : "var(--b-ghost)" }}
          >
            {isOver ? (
              <p className="text-xs font-bold" style={{ color: coluna.cor }}>Soltar aqui</p>
            ) : (
              <p className="text-xs text-brand-pale/20">Vazio</p>
            )}
          </div>
        ) : (
          cards.map(c => (
            <CandidatoCard
              key={c.id}
              cand={c}
              isMoving={movendo === c.id}
              onDragStart={(e, cand) => {
                e.dataTransfer.setData("candidaturaId", cand.id)
                e.dataTransfer.setData("fromStatus",    cand.status)
              }}
            />
          ))
        )}
      </div>
    </div>
  )
}


// ── Página ────────────────────────────────────────────────────────────────────
export function KanbanVaga({ usuario }) {
  const { id } = useParams()
  const [vaga, setVaga]                 = useState(null)
  const [candidaturas, setCandidaturas] = useState([])
  const [loading, setLoading]           = useState(true)
  const [dragOver, setDragOver]         = useState(null)
  const [movendo, setMovendo]           = useState(null)
  const [erroMsg, setErroMsg]           = useState(null)

  useEffect(() => {
    Promise.all([getVaga(id), getCandidaturas(id)])
      .then(([rv, rc]) => { setVaga(rv.data); setCandidaturas(rc.data) })
      .finally(() => setLoading(false))
  }, [id])

  function onDragOver(e, colId) { e.preventDefault(); setDragOver(colId) }
  function onDragLeave()        { setDragOver(null) }

  async function onDrop(e, toColId) {
    e.preventDefault()
    setDragOver(null)
    const candidaturaId = e.dataTransfer.getData("candidaturaId")
    const fromStatus    = e.dataTransfer.getData("fromStatus")
    const novoStatus    = resolverTransicao(fromStatus, toColId)

    if (!novoStatus) {
      setErroMsg("Transição não permitida nesta etapa.")
      setTimeout(() => setErroMsg(null), 3000)
      return
    }
    setMovendo(candidaturaId)
    try {
      const r = await atualizarStatusCandidatura(candidaturaId, novoStatus, usuario?.nome ?? "rh")
      setCandidaturas(prev => prev.map(c => c.id === candidaturaId ? r.data : c))
    } catch (err) {
      const msg = err.response?.data?.detail ?? "Erro ao mover candidatura"
      setErroMsg(typeof msg === "string" ? msg : "Transição inválida.")
      setTimeout(() => setErroMsg(null), 3000)
    } finally {
      setMovendo(null)
    }
  }

  const cardsPorColuna = (col) => candidaturas.filter(c => col.statuses.includes(c.status))

  return (
    <div className="flex flex-col gap-4" style={{ height: "calc(100vh - 120px)" }}>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap flex-shrink-0">
        <div>
          <Link
            to={`/vagas/${id}`}
            className="inline-flex items-center gap-1.5 text-sm text-brand-pale/45 hover:text-brand-sky transition-colors font-semibold"
          >
            ← Detalhes da vaga
          </Link>
          <h1 className="text-xl font-bold text-brand-cloud mt-1">
            {loading ? "Carregando..." : vaga?.nome}
          </h1>
        </div>
        <div className="text-xs font-mono text-brand-pale/35 mt-1">
          {candidaturas.length} candidatos
        </div>
      </div>

      {/* Erro */}
      {erroMsg && (
        <div className="rounded-xl px-4 py-3 text-sm font-medium flex-shrink-0"
          style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)", color: "#FCA5A5" }}>
          {erroMsg}
        </div>
      )}

      {/* Board */}
      <div className="flex gap-3 overflow-x-auto pb-2 flex-1" style={{ alignItems: "flex-start" }}>
        {COLUNAS.map(col => (
          <Coluna
            key={col.id}
            coluna={col}
            cards={cardsPorColuna(col)}
            dragOver={dragOver}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            movendo={movendo}
            loading={loading}
          />
        ))}
      </div>
    </div>
  )
}
