import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { getVagas, createVaga, updateVagaStatus, getUsuarios } from "../api"
import { Badge } from "../components/Badge"
import { IconSearch } from "../components/Icons"

const PESOS_DEFAULT = {
  peso_rh: 0.6, peso_mercado: 0.4,
  peso_curriculo: 0.5, peso_entrevista_rh: 0.25, peso_entrevista_tec: 0.25,
}

const STATUS_COR   = { aberta: "green", pausada: "amber", fechada: "gray" }
const STATUS_LABEL = { aberta: "aberta", pausada: "pausada", fechada: "fechada" }

const inputClass   = "w-full rounded-xl px-4 py-2.5 text-sm transition-all"
const numInputClass= "w-20 rounded-lg px-2.5 py-1.5 text-sm font-mono text-center transition-all"

export function Vagas({ usuario }) {
  const [vagas, setVagas]     = useState([])
  const [gestores, setGestores] = useState([])
  const [form, setForm]       = useState({ nome: "", requisitos_texto: "", gestores_ids: [], ...PESOS_DEFAULT })
  const [criando, setCriando] = useState(false)
  const [erro, setErro]       = useState("")
  const [loading, setLoading] = useState(true)
  const [busca, setBusca]     = useState("")

  const podeGerenciar = usuario?.papel === "rh" || usuario?.papel === "admin"

  // Por vaga: admin sempre pode; RH só pode se estiver nos rhs_autorizados (ou vaga sem restrição)
  function podeEditarVaga(v) {
    if (usuario?.papel === "admin") return true
    if (usuario?.papel !== "rh") return false
    const rhs = v.rhs_autorizados ?? []
    return rhs.length === 0 || rhs.includes(String(usuario?.id))
  }

  useEffect(() => {
    const reqs = [getVagas()]
    if (podeGerenciar) reqs.push(getUsuarios())
    Promise.all(reqs)
      .then(([rv, ru]) => {
        setVagas(rv.data)
        if (ru) setGestores(ru.data.filter(u => u.papel === "gestor"))
      })
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(e) {
    e.preventDefault(); setErro("")
    try {
      const r = await createVaga(form)
      setVagas(v => [r.data, ...v])
      setForm({ nome: "", requisitos_texto: "", gestores_ids: [], ...PESOS_DEFAULT })
      setCriando(false)
    } catch (e) {
      const msg = e.response?.data?.detail
      setErro(Array.isArray(msg) ? msg[0]?.msg : msg || "Erro ao criar vaga")
    }
  }

  async function handleStatus(vaga, novoStatus) {
    try {
      const r = await updateVagaStatus(vaga.id, novoStatus)
      setVagas(prev => prev.map(v => v.id === vaga.id ? r.data : v))
    } catch {/* silent */}
  }

  function toggleGestor(id) {
    setForm(f => ({
      ...f,
      gestores_ids: f.gestores_ids.includes(id)
        ? f.gestores_ids.filter(g => g !== id)
        : [...f.gestores_ids, id],
    }))
  }

  const vagasOrdenadas = [...vagas]
    .sort((a, b) => {
      const ordem = { aberta: 0, pausada: 1, fechada: 2 }
      const so = (ordem[a.status] ?? 3) - (ordem[b.status] ?? 3)
      if (so !== 0) return so
      return new Date(b.criado_em) - new Date(a.criado_em)
    })
    .filter(v => !busca || v.nome.toLowerCase().includes(busca.toLowerCase()))

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-brand-cloud">Vagas</h1>
          <p className="text-sm text-brand-pale/45 mt-1 font-medium">
            {loading ? "Carregando..." : `${vagas.length} ${vagas.length === 1 ? "vaga" : "vagas"}`}
          </p>
        </div>
        {podeGerenciar && (
          <button onClick={() => setCriando(!criando)}
            className="flex items-center gap-2 px-4 py-2.5 text-brand-black text-sm font-bold rounded-xl hover:opacity-90"
            style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
            <span className="text-base font-light">+</span>
            Nova vaga
          </button>
        )}
      </div>

      {/* Formulário de criação */}
      {criando && (
        <div className="card-glass rounded-2xl p-6 mb-8">
          <h2 className="text-base font-bold text-brand-cloud mb-5">Nova vaga</h2>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                Nome da vaga
              </label>
              <input required value={form.nome}
                onChange={e => setForm(f => ({ ...f, nome: e.target.value }))}
                placeholder="ex: Desenvolvedor Python Sênior"
                className={inputClass} />
            </div>

            <div>
              <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                Requisitos
              </label>
              <textarea required rows={4} value={form.requisitos_texto}
                onChange={e => setForm(f => ({ ...f, requisitos_texto: e.target.value }))}
                placeholder="Python, FastAPI, PostgreSQL, Docker. Inglês intermediário..."
                className={`${inputClass} resize-none`} />
            </div>

            {/* Gestores */}
            {gestores.length > 0 && (
              <div>
                <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-2">
                  Gestores técnicos
                </label>
                <div className="flex flex-wrap gap-2">
                  {gestores.map(g => {
                    const sel = form.gestores_ids.includes(g.id)
                    return (
                      <button key={g.id} type="button" onClick={() => toggleGestor(g.id)}
                        className="px-3 py-1.5 rounded-xl text-xs font-semibold transition-all"
                        style={sel
                          ? { background: "linear-gradient(135deg,#1A8BBF,#4DC8E8)", color: "#07111A" }
                          : { background: "var(--s-chip)", color: "var(--t-muted2)",
                              border: "1px solid rgba(77,200,232,0.15)" }}>
                        {g.nome}
                      </button>
                    )
                  })}
                </div>
                {form.gestores_ids.length === 0 && (
                  <p className="text-xs text-amber-400/60 mt-1.5">
                    Sem gestor atribuído — a vaga não aparecerá para nenhum gestor.
                  </p>
                )}
              </div>
            )}

            {/* Pesos */}
            <div className="card-inner rounded-xl p-4 space-y-4">
              <p className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">Pesos</p>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-xs font-semibold text-brand-pale/55 mb-3">Score curricular</p>
                  <div className="space-y-2.5">
                    {[
                      { key: "peso_rh",      label: "Requisitos RH" },
                      { key: "peso_mercado", label: "Mercado"       },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex items-center justify-between gap-3">
                        <span className="text-sm text-brand-pale/65">{label}</span>
                        <input type="number" step="0.1" min="0" max="1" value={form[key]}
                          onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) }))}
                          className={numInputClass} />
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold text-brand-pale/55 mb-3">Score final</p>
                  <div className="space-y-2.5">
                    {[
                      { key: "peso_curriculo",      label: "Currículo"    },
                      { key: "peso_entrevista_rh",  label: "Entrev. RH"   },
                      { key: "peso_entrevista_tec", label: "Entrev. Tec." },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex items-center justify-between gap-3">
                        <span className="text-sm text-brand-pale/65">{label}</span>
                        <input type="number" step="0.05" min="0" max="1" value={form[key]}
                          onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) }))}
                          className={numInputClass} />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {erro && (
              <div className="rounded-xl px-4 py-3"
                style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }}>
                <p className="text-sm font-medium" style={{ color: "#FCA5A5" }}>{erro}</p>
              </div>
            )}

            <div className="flex items-center gap-3 pt-1">
              <button type="submit"
                className="px-5 py-2.5 text-brand-black text-sm font-bold rounded-xl hover:opacity-90"
                style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
                Criar vaga
              </button>
              <button type="button" onClick={() => { setCriando(false); setErro("") }}
                className="px-5 py-2.5 text-brand-pale/45 hover:text-brand-cloud text-sm font-semibold transition-colors">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Busca */}
      {!loading && vagas.length > 0 && (
        <div className="relative mb-2">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-pale/35 flex items-center">
            <IconSearch size={15} />
          </span>
          <input
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar vaga por nome…"
            className="w-full rounded-xl pl-9 pr-4 py-2.5 text-sm transition-all"
          />
          {busca && (
            <button onClick={() => setBusca("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-pale/35 hover:text-brand-pale transition-colors text-lg leading-none">
              ×
            </button>
          )}
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="space-y-2.5">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 rounded-2xl animate-pulse"
              style={{ background: "var(--s-skeleton-lt)" }} />
          ))}
        </div>
      ) : vagasOrdenadas.length === 0 ? (
        <div className="text-center py-20 rounded-2xl border-2 border-dashed"
          style={{ borderColor: "var(--b-card)" }}>
          <p className="text-brand-pale/55 text-sm font-semibold">
            {busca ? `Nenhuma vaga encontrada para "${busca}"` : "Nenhuma vaga"}
          </p>
          {busca && (
            <button onClick={() => setBusca("")}
              className="mt-2 text-xs text-brand-sky hover:underline">
              Limpar busca
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2.5">
          {vagasOrdenadas.map(v => (
            <div key={v.id} className="card-interactive rounded-2xl px-6 py-4 flex items-center gap-4">
              <Link to={`/vagas/${v.id}`} className="flex-1 min-w-0 group">
                <p className="font-bold text-brand-cloud group-hover:text-brand-sky transition-colors">
                  {v.nome}
                </p>
                <p className="text-sm text-brand-pale/45 mt-0.5 truncate max-w-xl">
                  {v.requisitos_texto}
                </p>
              </Link>

              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="vaga-peso-pill text-xs font-mono px-2 py-1 rounded-lg font-semibold">
                  RH {Math.round(v.peso_rh * 100)}% · Mkt {Math.round(v.peso_mercado * 100)}%
                </span>
                <Badge cor={STATUS_COR[v.status] ?? "gray"}>
                  {STATUS_LABEL[v.status] ?? v.status}
                </Badge>

                {/* Botões de status — só para RHs autorizados nesta vaga ou admin */}
                {podeEditarVaga(v) && v.status !== "fechada" && (
                  <div className="flex gap-1">
                    {v.status === "aberta" && (
                      <button onClick={() => handleStatus(v, "pausada")}
                        className="btn-vaga-pausar px-2.5 py-1 rounded-lg text-xs font-bold transition-all"
                        title="Pausar vaga">
                        ⏸
                      </button>
                    )}
                    {v.status === "pausada" && (
                      <button onClick={() => handleStatus(v, "aberta")}
                        className="btn-vaga-reabrir px-2.5 py-1 rounded-lg text-xs font-bold transition-all"
                        title="Reabrir vaga">
                        ▶
                      </button>
                    )}
                    <button onClick={() => handleStatus(v, "fechada")}
                      className="btn-vaga-encerrar px-2.5 py-1 rounded-lg text-xs font-bold transition-all"
                      title="Encerrar vaga">
                      ✕
                    </button>
                  </div>
                )}

                <Link to={`/vagas/${v.id}`}
                  className="text-brand-pale/30 hover:text-brand-sky transition-colors text-lg">
                  →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}