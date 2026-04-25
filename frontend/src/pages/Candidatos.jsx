import { useState, useEffect } from "react"
import { getCandidatos, createCandidato, getVagas, createCandidatura } from "../api"
import { Badge } from "../components/Badge"

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

  const inputClass = "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Candidatos</h1>
          <p className="text-sm text-slate-400 mt-1 font-medium">
            {loading ? "Carregando..." : `${candidatos.length} cadastrados`}
          </p>
        </div>
        <button
          onClick={() => setCriando(!criando)}
          className="flex items-center gap-2 px-4 py-2.5 text-white text-sm font-bold rounded-xl transition-all shadow-sm hover:shadow-md"
          style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}
        >
          <span className="text-base leading-none font-light">+</span>
          Novo candidato
        </button>
      </div>

      {criando && (
        <div className="mb-8 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-base font-bold text-slate-900 mb-5">Novo candidato</h2>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Nome completo</label>
                <input required value={form.nome} onChange={set("nome")}
                  placeholder="Ana Silva" className={inputClass}/>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email</label>
                <input required type="email" value={form.email} onChange={set("email")}
                  placeholder="ana@email.com" className={inputClass}/>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Telefone</label>
                <input value={form.telefone} onChange={set("telefone")}
                  placeholder="(11) 99999-0000" className={inputClass}/>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Cidade</label>
                <input value={form.cidade} onChange={set("cidade")}
                  placeholder="São Paulo" className={inputClass}/>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
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
              <button type="submit"
                className="px-5 py-2.5 text-white text-sm font-bold rounded-xl transition-all shadow-sm hover:shadow-md"
                style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
                Cadastrar
              </button>
              <button type="button" onClick={() => setCriando(false)}
                className="px-5 py-2.5 text-slate-500 hover:text-slate-900 text-sm font-semibold transition-colors">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="space-y-2.5">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-16 bg-slate-100 rounded-2xl animate-pulse"/>
          ))}
        </div>
      ) : candidatos.length === 0 ? (
        <div className="text-center py-24 border-2 border-dashed border-slate-200 rounded-2xl">
          <div className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center bg-indigo-50">
            <span className="text-indigo-400 text-xl">◷</span>
          </div>
          <p className="text-slate-500 text-sm font-semibold">Nenhum candidato cadastrado</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {candidatos.map(c => (
            <div key={c.id}
              className="bg-white border border-slate-200 rounded-2xl px-6 py-4 flex items-center justify-between hover:border-indigo-200 hover:shadow-sm transition-all">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm"
                  style={{
                    background: c.origem === "externo"
                      ? "linear-gradient(135deg, #0ea5e9, #6366f1)"
                      : "linear-gradient(135deg, #4f46e5, #7c3aed)"
                  }}>
                  <span className="text-sm font-bold text-white">
                    {c.nome.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="font-bold text-slate-900">{c.nome}</p>
                  <p className="text-xs text-slate-400 font-mono">{c.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {c.cidade && (
                  <span className="text-sm text-slate-400 font-medium">{c.cidade}</span>
                )}
                <Badge cor={c.origem === "externo" ? "blue" : "purple"}>
                  {c.origem}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
