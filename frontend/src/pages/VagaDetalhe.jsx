import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { getVaga, getCandidaturas, analisarMercado, updatePesos } from "../api"
import { ScoreBar } from "../components/ScoreBar"
import { Badge } from "../components/Badge"

const corStatus = {
  novo: "gray", triagem_pendente: "amber",
  aprovado_triagem: "green", reprovado_triagem: "red",
  entrevista_rh_agendada: "blue", entrevista_rh_realizada: "blue",
  entrevista_tec_agendada: "blue", entrevista_tec_realizada: "blue",
  decisao_pendente: "amber", contratado: "green",
  nao_aprovado: "red", banco_de_talentos: "purple",
}

const labelStatus = {
  novo: "Novo", triagem_pendente: "Triagem pendente",
  aprovado_triagem: "Aprovado triagem", reprovado_triagem: "Reprovado triagem",
  entrevista_rh_agendada: "Entrevista RH", entrevista_rh_realizada: "RH realizada",
  entrevista_tec_agendada: "Entrev. técnica", entrevista_tec_realizada: "Técnica realizada",
  decisao_pendente: "Decisão pendente", contratado: "Contratado",
  nao_aprovado: "Não aprovado", banco_de_talentos: "Banco de talentos",
}

const rankStyle = [
  { background: "linear-gradient(135deg, #1AAA80, #2EE8B4)", color: "#07111A" },
  { background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)", color: "#07111A" },
  { background: "rgba(77, 200, 232, 0.2)",                   color: "#4DC8E8" },
]

export function VagaDetalhe({ usuario }) {
  const { id }                          = useParams()
  const [vaga, setVaga]                 = useState(null)
  const [candidaturas, setCandidaturas] = useState([])
  const [analisando, setAnalisando]     = useState(false)
  const [loading, setLoading]           = useState(true)
  const [editandoPesos, setEditandoPesos] = useState(false)
  const [pesos, setPesos]               = useState(null)
  const [salvandoPesos, setSalvandoPesos] = useState(false)
  const [erroPesos, setErroPesos]       = useState(null)

  const podeEditarPesos = usuario?.papel === "admin" || usuario?.papel === "rh"

  useEffect(() => {
    Promise.all([
      getVaga(id),
      getCandidaturas(id),
    ]).then(([rv, rc]) => {
      setVaga(rv.data)
      setCandidaturas(rc.data)
    }).finally(() => setLoading(false))
  }, [id])

  function abrirEdicaoPesos() {
    setPesos({
      peso_rh:             vaga.peso_rh,
      peso_mercado:        vaga.peso_mercado,
      peso_curriculo:      vaga.peso_curriculo,
      peso_entrevista_rh:  vaga.peso_entrevista_rh,
      peso_entrevista_tec: vaga.peso_entrevista_tec,
    })
    setErroPesos(null)
    setEditandoPesos(true)
  }

  function setPeso(campo, valor) {
    const v = Math.max(0, Math.min(100, Number(valor))) / 100
    setPesos(prev => {
      const next = { ...prev, [campo]: v }
      // auto-ajusta o complementar para os pares que devem somar 1
      if (campo === "peso_rh")        next.peso_mercado        = Math.round((1 - v) * 100) / 100
      if (campo === "peso_mercado")   next.peso_rh             = Math.round((1 - v) * 100) / 100
      if (campo === "peso_curriculo") {
        const resto = Math.round((1 - v) * 100) / 100
        next.peso_entrevista_rh  = Math.round(resto / 2 * 100) / 100
        next.peso_entrevista_tec = Math.round((resto - next.peso_entrevista_rh) * 100) / 100
      }
      return next
    })
  }

  async function handleSalvarPesos() {
    const somaScore = Math.round((pesos.peso_rh + pesos.peso_mercado) * 100) / 100
    const somaFinal = Math.round((pesos.peso_curriculo + pesos.peso_entrevista_rh + pesos.peso_entrevista_tec) * 100) / 100
    if (somaScore !== 1) { setErroPesos(`Requisitos + Mercado devem somar 100% (atual: ${Math.round(somaScore*100)}%)`); return }
    if (somaFinal !== 1) { setErroPesos(`Currículo + Entrev. RH + Entrev. Tec. devem somar 100% (atual: ${Math.round(somaFinal*100)}%)`); return }
    setSalvandoPesos(true); setErroPesos(null)
    try {
      const r = await updatePesos(id, pesos)
      setVaga(r.data)
      setEditandoPesos(false)
    } catch (err) {
      setErroPesos(err.response?.data?.detail ?? "Erro ao salvar pesos")
    } finally {
      setSalvandoPesos(false)
    }
  }

  async function handleAnalisarMercado() {
    setAnalisando(true)
    try {
      const r = await analisarMercado(id)
      setVaga(r.data)
    } finally {
      setAnalisando(false)
    }
  }

  if (loading) return (
    <div className="space-y-4">
      <div className="h-8 w-64 rounded-xl animate-pulse" style={{ background: "rgba(14, 80, 104, 0.3)" }} />
      <div className="h-4 w-96 rounded animate-pulse" style={{ background: "rgba(14, 80, 104, 0.2)" }} />
    </div>
  )

  if (!vaga) return (
    <div className="text-center py-20">
      <p className="text-brand-pale/45">Vaga não encontrada.</p>
      <Link to="/" className="text-sm text-brand-sky hover:text-brand-pale mt-2 block font-semibold transition-colors">
        ← Voltar para vagas
      </Link>
    </div>
  )

  const termos     = vaga.ranking_mercado?.termos?.slice(0, 12) || []
  const totalVagas = vaga.ranking_mercado?.total_vagas_analisadas

  return (
    <div>
      {/* Breadcrumb */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-brand-pale/45 hover:text-brand-sky transition-colors mb-6 font-semibold"
      >
        ← Vagas
      </Link>

      {/* Header da vaga */}
      <div className="card-glass rounded-2xl p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-bold text-brand-cloud">{vaga.nome}</h1>
              <Badge cor={{ aberta: "green", pausada: "amber", fechada: "gray" }[vaga.status]}>
                {vaga.status}
              </Badge>
            </div>
            <p className="text-sm text-brand-pale/55 leading-relaxed">{vaga.requisitos_texto}</p>
          </div>
          <button
            onClick={handleAnalisarMercado}
            disabled={analisando}
            className="flex-shrink-0 px-4 py-2 text-brand-sky text-sm font-bold rounded-xl transition-all disabled:opacity-50"
            style={{
              background: "rgba(26, 139, 191, 0.14)",
              border: "1px solid rgba(26, 139, 191, 0.3)",
            }}
            onMouseEnter={e => {
              if (!analisando) {
                e.currentTarget.style.background = "rgba(26, 139, 191, 0.25)"
                e.currentTarget.style.borderColor = "rgba(26, 139, 191, 0.5)"
              }
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "rgba(26, 139, 191, 0.14)"
              e.currentTarget.style.borderColor = "rgba(26, 139, 191, 0.3)"
            }}
          >
            {analisando ? (
              <span className="flex items-center gap-2">
                <span
                  className="w-3 h-3 border-2 rounded-full animate-spin"
                  style={{ borderColor: "rgba(77,200,232,0.4)", borderTopColor: "#4DC8E8" }}
                />
                Analisando...
              </span>
            ) : "Analisar mercado"}
          </button>
        </div>

        {/* Pesos */}
        <div
          className="mt-4 pt-4"
          style={{ borderTop: "1px solid rgba(77, 200, 232, 0.1)" }}
        >
          {!editandoPesos ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-brand-pale/40 font-medium">Pesos:</span>
              {[
                `Requisitos ${Math.round(vaga.peso_rh * 100)}%`,
                `Mercado ${Math.round(vaga.peso_mercado * 100)}%`,
              ].map(label => (
                <span key={label} className="text-xs font-mono px-2.5 py-1 rounded-lg font-semibold"
                  style={{ background: "rgba(26, 139, 191, 0.15)", color: "#4DC8E8" }}>
                  {label}
                </span>
              ))}
              <span className="text-brand-pale/20 mx-0.5">|</span>
              {[
                `Currículo ${Math.round(vaga.peso_curriculo * 100)}%`,
                `Entrev. RH ${Math.round(vaga.peso_entrevista_rh * 100)}%`,
                `Entrev. Tec. ${Math.round(vaga.peso_entrevista_tec * 100)}%`,
              ].map(label => (
                <span key={label} className="text-xs font-mono px-2.5 py-1 rounded-lg font-semibold"
                  style={{ background: "rgba(14, 80, 104, 0.4)", color: "rgba(125, 216, 240, 0.6)" }}>
                  {label}
                </span>
              ))}
              {podeEditarPesos && (
                <button onClick={abrirEdicaoPesos}
                  className="ml-auto text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                  style={{ background: "rgba(26,139,191,0.12)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
                  Editar pesos
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">Editar pesos</p>

              {/* Score curricular */}
              <div>
                <p className="text-xs text-brand-pale/40 mb-2">Score curricular (deve somar 100%)</p>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { campo: "peso_rh",      label: "Requisitos da vaga" },
                    { campo: "peso_mercado", label: "Mercado" },
                  ].map(({ campo, label }) => (
                    <div key={campo}>
                      <label className="block text-xs text-brand-pale/50 mb-1">{label}</label>
                      <div className="flex items-center gap-2">
                        <input type="range" min="0" max="100" step="5"
                          value={Math.round((pesos[campo] ?? 0) * 100)}
                          onChange={e => setPeso(campo, e.target.value)}
                          className="flex-1 accent-sky-400" />
                        <span className="text-xs font-mono font-bold text-brand-sky w-10 text-right">
                          {Math.round((pesos[campo] ?? 0) * 100)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Score consolidado */}
              <div>
                <p className="text-xs text-brand-pale/40 mb-2">Score consolidado (deve somar 100%)</p>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { campo: "peso_curriculo",      label: "Currículo" },
                    { campo: "peso_entrevista_rh",  label: "Entrev. RH" },
                    { campo: "peso_entrevista_tec", label: "Entrev. Tec." },
                  ].map(({ campo, label }) => (
                    <div key={campo}>
                      <label className="block text-xs text-brand-pale/50 mb-1">{label}</label>
                      <div className="flex items-center gap-2">
                        <input type="range" min="0" max="100" step="5"
                          value={Math.round((pesos[campo] ?? 0) * 100)}
                          onChange={e => setPeso(campo, e.target.value)}
                          className="flex-1 accent-sky-400" />
                        <span className="text-xs font-mono font-bold text-brand-sky w-10 text-right">
                          {Math.round((pesos[campo] ?? 0) * 100)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {erroPesos && <p className="text-xs text-red-400">{erroPesos}</p>}

              <div className="flex gap-3">
                <button onClick={() => setEditandoPesos(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-brand-pale/50 transition-colors hover:text-brand-pale"
                  style={{ border: "1px solid rgba(77,200,232,0.15)" }}>
                  Cancelar
                </button>
                <button onClick={handleSalvarPesos} disabled={salvandoPesos}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-brand-black disabled:opacity-50"
                  style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
                  {salvandoPesos ? "Salvando..." : "Salvar pesos"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Ranking de candidatos */}
        <div className="col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
              Candidatos
            </h2>
            <span className="text-xs text-brand-pale/35 font-mono font-semibold">
              {candidaturas.length} {candidaturas.length === 1 ? "candidato" : "candidatos"}
            </span>
          </div>

          {candidaturas.length === 0 ? (
            <div
              className="rounded-2xl p-10 text-center border-2 border-dashed"
              style={{ borderColor: "rgba(77, 200, 232, 0.12)" }}
            >
              <p className="text-brand-pale/40 text-sm font-medium">Nenhum candidato vinculado a esta vaga.</p>
            </div>
          ) : (
            candidaturas
              .sort((a, b) => {
                const sa = a.curriculo?.score_curriculo ?? a.score_total ?? 0
                const sb = b.curriculo?.score_curriculo ?? b.score_total ?? 0
                return sb - sa
              })
              .map((c, i) => {
                const curriculo   = c.curriculo
                const scoreRH     = curriculo?.score_rh      ?? null
                const scoreMkt    = curriculo?.score_mercado  ?? null
                const scoreFinal  = curriculo?.score_curriculo ?? c.score_total ?? null
                const processando = c.status === "processando_curriculo" ||
                                    (c.status === "triagem_pendente" && scoreRH === null)

                const scoreCor =
                  scoreFinal >= 70 ? "#2EE8B4" :
                  scoreFinal >= 50 ? "#FCD34D" : "#FCA5A5"

                return (
                  <div
                    key={c.id}
                    className="card-interactive rounded-2xl p-5"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        {/* Rank badge */}
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold"
                          style={rankStyle[i] ?? {
                            background: "rgba(14, 80, 104, 0.5)",
                            color: "rgba(125, 216, 240, 0.6)",
                          }}
                        >
                          {i + 1}
                        </div>
                        <div>
                          <p className="font-bold text-brand-cloud">
                            {c.candidato?.nome ?? "Candidato"}
                          </p>
                          <p className="text-xs text-brand-pale/40 font-mono mt-0.5">
                            {c.candidato?.email}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {scoreFinal !== null && (
                          <div className="text-right">
                            <p className="text-2xl font-bold font-mono" style={{ color: scoreCor }}>
                              {scoreFinal}
                            </p>
                            <p className="text-xs text-brand-pale/35">/ 100</p>
                          </div>
                        )}
                        <Badge cor={corStatus[c.status] ?? "gray"}>
                          {labelStatus[c.status] ?? c.status}
                        </Badge>
                      </div>
                    </div>

                    {processando ? (
                      <div className="flex items-center gap-2 pl-11">
                        <span
                          className="w-3 h-3 border-2 rounded-full animate-spin"
                          style={{ borderColor: "rgba(77,200,232,0.3)", borderTopColor: "#4DC8E8" }}
                        />
                        <span className="text-xs text-brand-pale/40">Processando currículo...</span>
                      </div>
                    ) : scoreRH !== null ? (
                      <div className="pl-11 space-y-2.5">
                        <ScoreBar score={scoreRH}  label="Aderência aos requisitos da vaga" />
                        <ScoreBar score={scoreMkt} label="Aderência ao mercado" />
                      </div>
                    ) : null}

                    <div className="flex justify-end mt-2">
                      <Link
                        to={`/candidaturas/${c.id}/entrevistas`}
                        className="text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                        style={{
                          background: "rgba(26,139,191,0.12)",
                          border: "1px solid rgba(26,139,191,0.25)",
                          color: "#4DC8E8",
                        }}
                      >
                        Ver entrevistas →
                      </Link>
                    </div>
                  </div>
                )
              })
          )}
        </div>

        {/* Sidebar: skills de mercado */}
        <div className="space-y-3">
          <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
            Top skills de mercado
          </h2>
          <div className="card-glass rounded-2xl p-5">
            {termos.length === 0 ? (
              <div className="text-center py-6">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                  style={{ background: "rgba(26, 139, 191, 0.14)" }}
                >
                  <span className="text-brand-sky text-base">◎</span>
                </div>
                <p className="text-xs text-brand-pale/40 leading-relaxed">
                  Clique em "Analisar mercado" para ver as skills mais demandadas para este cargo.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {termos.map((t, i) => (
                  <div key={t.termo} className="flex items-center gap-2.5">
                    <span className="text-xs font-mono text-brand-pale/25 w-4 text-right flex-shrink-0">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-brand-pale/80 truncate">
                          {t.termo}
                        </span>
                        <span className="text-xs font-mono text-brand-sky ml-2 flex-shrink-0 font-bold">
                          {t.frequencia}×
                        </span>
                      </div>
                      <div
                        className="w-full rounded-full h-1.5 overflow-hidden"
                        style={{ background: "rgba(7, 17, 26, 0.5)" }}
                      >
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${(t.frequencia / termos[0].frequencia) * 100}%`,
                            background: "linear-gradient(90deg, #1A8BBF, #4DC8E8)",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}

                {totalVagas && (
                  <p
                    className="text-xs text-brand-pale/35 pt-3 font-mono"
                    style={{ borderTop: "1px solid rgba(77, 200, 232, 0.1)" }}
                  >
                    {totalVagas} vagas analisadas · {vaga.ranking_mercado.fonte}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
