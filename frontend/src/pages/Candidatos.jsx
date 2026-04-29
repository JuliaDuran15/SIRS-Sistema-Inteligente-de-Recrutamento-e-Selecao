import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { getCandidatos, createCandidato, getVagas, createCandidatura } from "../api"
import { Badge } from "../components/Badge"

const inputClass = "w-full rounded-xl px-4 py-2.5 text-sm transition-all"

export function Candidatos() {
  const [candidatos, setCandidatos] = useState([])
  const [vagas, setVagas]           = useState([])
  const [criando, setCriando]       = useState(false)
  const [loading, setLoading]       = useState(true)
  const [form, setForm]             = useState({
    nome: "", email: "", telefone: "",
    cidade: "", estado: "", vaga_id: "",
  })

  useEffect(() => {
    Promise.all([getCandidatos(), getVagas()])
      .then(([rc, rv]) => {
        setCandidatos(rc.data)
        setVagas(rv.data)
      })
      .finally(() => setLoading(false))
  }, [])

  function set(key) {
    return e => setForm(f => ({ ...f, [key]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const { vaga_id, ...dados } = form
    const r = await createCandidato({ ...dados, origem: "manual" })
    if (vaga_id) {
      await createCandidatura({ candidato_id: r.data.id, vaga_id })
    }
    setCandidatos(c => [r.data, ...c])
    setCriando(false)
    setForm({ nome: "", email: "", telefone: "", cidade: "", estado: "", vaga_id: "" })
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-brand-cloud">Candidatos</h1>
          <p className="text-sm text-brand-pale/45 mt-1 font-medium">
            {loading ? "Carregando..." : `${candidatos.length} cadastrados`}
          </p>
        </div>
        <button
          onClick={() => setCriando(!criando)}
          className="flex items-center gap-2 px-4 py-2.5 text-brand-black text-sm font-bold rounded-xl transition-all hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}
        >
          <span className="text-base leading-none font-light">+</span>
          Novo candidato
        </button>
      </div>

      {criando && (
        <div className="card-glass rounded-2xl p-6 mb-8">
          <h2 className="text-base font-bold text-brand-cloud mb-5">Novo candidato</h2>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                  Nome completo
                </label>
                <input required value={form.nome} onChange={set("nome")}
                  placeholder="Ana Silva" className={inputClass}/>
              </div>
              <div>
                <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                  Email
                </label>
                <input required type="email" value={form.email} onChange={set("email")}
                  placeholder="ana@email.com" className={inputClass}/>
              </div>
              <div>
                <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                  Telefone
                </label>
                <input value={form.telefone} onChange={set("telefone")}
                  placeholder="(11) 99999-0000" className={inputClass}/>
              </div>
              <div>
                <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                  Cidade
                </label>
                <input value={form.cidade} onChange={set("cidade")}
                  placeholder="São Paulo" className={inputClass}/>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                Vincular à vaga
              </label>
              <select value={form.vaga_id} onChange={set("vaga_id")} className={inputClass}>
                <option value="">Sem vaga por enquanto</option>
                {vagas.map(v => (
                  <option key={v.id} value={v.id}>{v.nome}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                className="px-5 py-2.5 text-brand-black text-sm font-bold rounded-xl transition-all hover:opacity-90"
                style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}
              >
                Cadastrar
              </button>
              <button
                type="button"
                onClick={() => setCriando(false)}
                className="px-5 py-2.5 text-brand-pale/45 hover:text-brand-cloud text-sm font-semibold transition-colors"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="space-y-2.5">
          {[1, 2, 3, 4].map(i => (
            <div
              key={i}
              className="h-16 rounded-2xl animate-pulse"
              style={{ background: "var(--s-skeleton-lt)" }}
            />
          ))}
        </div>
      ) : candidatos.length === 0 ? (
        <div
          className="text-center py-24 rounded-2xl border-2 border-dashed"
          style={{ borderColor: "var(--b-card)" }}
        >
          <div
            className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center"
            style={{ background: "rgba(26, 139, 191, 0.14)" }}
          >
            <span className="text-brand-sky text-xl">◷</span>
          </div>
          <p className="text-brand-pale/55 text-sm font-semibold">Nenhum candidato cadastrado</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {candidatos.map(c => (
            <Link
              key={c.id}
              to={`/candidatos/${c.id}`}
              className="card-interactive rounded-2xl px-6 py-4 flex items-center justify-between group"
            >
              <div className="flex items-center gap-4">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{
                    background: c.origem === "externo"
                      ? "linear-gradient(135deg, #1A8BBF, #4DC8E8)"
                      : "linear-gradient(135deg, #1AAA80, #2EE8B4)",
                  }}
                >
                  <span className="text-sm font-bold text-brand-black">
                    {c.nome.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="font-bold text-brand-cloud group-hover:text-brand-sky transition-colors">
                    {c.nome}
                  </p>
                  <p className="text-xs text-brand-pale/45 font-mono">{c.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {c.cidade && (
                  <span className="text-sm text-brand-pale/45 font-medium">{c.cidade}</span>
                )}
                <Badge cor={c.origem === "externo" ? "blue" : "green"}>
                  {c.origem}
                </Badge>
                <span className="text-brand-pale/30 group-hover:text-brand-sky transition-colors">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
