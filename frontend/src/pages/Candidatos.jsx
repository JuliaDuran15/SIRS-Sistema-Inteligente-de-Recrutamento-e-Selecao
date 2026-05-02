import { useState, useEffect, useCallback } from "react"
import { Link } from "react-router-dom"
import { getCandidatos, createCandidato, getVagas, createCandidatura } from "../api"
import { Badge } from "../components/Badge"

const inputClass = "w-full rounded-xl px-4 py-2.5 text-sm transition-all"
const LIMIT = 30

export function Candidatos() {
  const [data, setData]         = useState({ items: [], total: 0 })
  const [vagas, setVagas]       = useState([])
  const [criando, setCriando]   = useState(false)
  const [loading, setLoading]   = useState(true)
  const [offset, setOffset]     = useState(0)
  const [busca, setBusca]       = useState("")
  const [origem, setOrigem]     = useState("")  // "" | "manual" | "externo"
  const [form, setForm]         = useState({
    nome: "", email: "", telefone: "",
    cidade: "", estado: "", vaga_id: "",
  })

  const carregar = useCallback((off = 0, q = busca, orig = origem) => {
    setLoading(true)
    const params = { limit: LIMIT, offset: off }
    if (q)    params.q      = q
    if (orig) params.origem = orig
    getCandidatos(params)
      .then(r => setData(r.data))
      .finally(() => setLoading(false))
  }, [busca, origem])

  useEffect(() => {
    getVagas().then(r => setVagas(r.data))
  }, [])

  useEffect(() => {
    setOffset(0)
    carregar(0, busca, origem)
  }, [busca, origem])

  function set(key) {
    return e => setForm(f => ({ ...f, [key]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const { vaga_id, ...dados } = form
    const r = await createCandidato(dados)
    if (vaga_id) await createCandidatura({ candidato_id: r.data.id, vaga_id })
    setCriando(false)
    setForm({ nome: "", email: "", telefone: "", cidade: "", estado: "", vaga_id: "" })
    carregar(0)
  }

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
          <h1 className="text-2xl font-bold text-brand-cloud">Candidatos</h1>
          <p className="text-sm text-brand-pale/45 mt-1 font-medium">
            {loading ? "Carregando..." : `${data.total} encontrados`}
          </p>
        </div>
        <button
          onClick={() => setCriando(!criando)}
          className="flex items-center gap-2 px-4 py-2.5 text-brand-black text-sm font-bold rounded-xl hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
          <span className="text-base leading-none font-light">+</span>
          Novo candidato
        </button>
      </div>

      {/* Barra de busca + filtros */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <div className="flex-1 min-w-48 relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-brand-pale/35 text-sm">⌕</span>
          <input
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar por nome ou e-mail…"
            className="w-full rounded-xl pl-9 pr-4 py-2.5 text-sm transition-all"
          />
        </div>
        {/* Filtro origem */}
        <div className="flex gap-1.5">
          {[["", "Todos"], ["manual", "Manual"], ["externo", "Externo"]].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setOrigem(val)}
              className="px-3 py-2 rounded-xl text-xs font-semibold transition-all"
              style={origem === val
                ? { background: "rgba(26,139,191,0.25)", color: "#4DC8E8", border: "1px solid rgba(26,139,191,0.4)" }
                : { background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Formulário de criação */}
      {criando && (
        <div className="card-glass rounded-2xl p-6 mb-8">
          <h2 className="text-base font-bold text-brand-cloud mb-5">Novo candidato</h2>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              {[
                ["nome", "Nome completo", "text", "Ana Silva", true],
                ["email", "Email", "email", "ana@email.com", true],
                ["telefone", "Telefone", "text", "(11) 99999-0000", false],
                ["cidade", "Cidade", "text", "São Paulo", false],
              ].map(([key, label, type, ph, req]) => (
                <div key={key}>
                  <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">{label}</label>
                  <input required={req} type={type} value={form[key]} onChange={set(key)}
                    placeholder={ph} className={inputClass} />
                </div>
              ))}
            </div>
            <div>
              <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                Vincular à vaga
              </label>
              <select value={form.vaga_id} onChange={set("vaga_id")} className={inputClass}>
                <option value="">Sem vaga por enquanto</option>
                {vagas.map(v => <option key={v.id} value={v.id}>{v.nome}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-3 pt-1">
              <button type="submit"
                className="px-5 py-2.5 text-brand-black text-sm font-bold rounded-xl hover:opacity-90"
                style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
                Cadastrar
              </button>
              <button type="button" onClick={() => setCriando(false)}
                className="px-5 py-2.5 text-brand-pale/45 hover:text-brand-cloud text-sm font-semibold transition-colors">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="space-y-2.5">
          {[1,2,3,4].map(i => (
            <div key={i} className="h-16 rounded-2xl animate-pulse" style={{ background: "var(--s-skeleton-lt)" }} />
          ))}
        </div>
      ) : data.items.length === 0 ? (
        <div className="text-center py-24 rounded-2xl border-2 border-dashed" style={{ borderColor: "var(--b-card)" }}>
          <p className="text-brand-pale/55 text-sm font-semibold">
            {busca || origem ? "Nenhum candidato encontrado para os filtros aplicados" : "Nenhum candidato cadastrado"}
          </p>
          {(busca || origem) && (
            <button onClick={() => { setBusca(""); setOrigem("") }}
              className="mt-3 text-xs text-brand-sky hover:underline">
              Limpar filtros
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2.5">
          {data.items.map(c => (
            <Link key={c.id} to={`/candidatos/${c.id}`}
              className="card-interactive rounded-2xl px-6 py-4 flex items-center justify-between group">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: c.tem_candidatura_externa
                    ? "linear-gradient(135deg, #1A8BBF, #4DC8E8)"
                    : "linear-gradient(135deg, #1AAA80, #2EE8B4)" }}>
                  <span className="text-sm font-bold text-brand-black">{c.nome.charAt(0).toUpperCase()}</span>
                </div>
                <div>
                  <p className="font-bold text-brand-cloud group-hover:text-brand-sky transition-colors">{c.nome}</p>
                  <p className="text-xs text-brand-pale/45 font-mono">{c.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {c.cidade && <span className="text-sm text-brand-pale/45">{c.cidade}</span>}
                <Badge cor={c.tem_candidatura_externa ? "blue" : "green"}>
                  {c.tem_candidatura_externa ? "externo" : "manual"}
                </Badge>
                <span className="text-brand-pale/30 group-hover:text-brand-sky transition-colors">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Paginação */}
      {totalPaginas > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-xs text-brand-pale/40 font-mono">
            {offset + 1}–{Math.min(offset + LIMIT, data.total)} de {data.total}
          </p>
          <div className="flex gap-1.5">
            <button
              disabled={paginaAtual === 1}
              onClick={() => paginar(offset - LIMIT)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-30"
              style={{ background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}>
              ← Anterior
            </button>
            {Array.from({ length: Math.min(totalPaginas, 7) }, (_, i) => {
              const pg = i + 1
              return (
                <button key={pg} onClick={() => paginar((pg - 1) * LIMIT)}
                  className="w-8 h-8 rounded-lg text-xs font-bold transition-all"
                  style={pg === paginaAtual
                    ? { background: "rgba(26,139,191,0.25)", color: "#4DC8E8", border: "1px solid rgba(26,139,191,0.4)" }
                    : { background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}>
                  {pg}
                </button>
              )
            })}
            <button
              disabled={paginaAtual === totalPaginas}
              onClick={() => paginar(offset + LIMIT)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-30"
              style={{ background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}>
              Próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
