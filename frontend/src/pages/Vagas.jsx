import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { getVagas, createVaga } from "../api"
import { Badge } from "../components/Badge"

const PESOS = {
  peso_rh: 0.6, peso_mercado: 0.4,
  peso_curriculo: 0.5, peso_entrevista_rh: 0.25, peso_entrevista_tec: 0.25,
}

const corStatus = { aberta: "green", pausada: "amber", fechada: "gray" }

const inputClass = "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"

export function Vagas() {
  const [vagas, setVagas]     = useState([])
  const [form, setForm]       = useState({ nome: "", requisitos_texto: "", ...PESOS })
  const [criando, setCriando] = useState(false)
  const [erro, setErro]       = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getVagas()
      .then(r => setVagas(r.data))
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setErro("")
    try {
      const r = await createVaga(form)
      setVagas(v => [r.data, ...v])
      setForm({ nome: "", requisitos_texto: "", ...PESOS })
      setCriando(false)
    } catch (e) {
      const msg = e.response?.data?.detail
      setErro(Array.isArray(msg) ? msg[0]?.msg : msg || "Erro ao criar vaga")
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Vagas</h1>
          <p className="text-sm text-slate-400 mt-1 font-medium">
            {loading ? "Carregando..." : `${vagas.length} ${vagas.length === 1 ? "vaga cadastrada" : "vagas cadastradas"}`}
          </p>
        </div>
        <button
          onClick={() => setCriando(!criando)}
          className="flex items-center gap-2 px-4 py-2.5 text-white text-sm font-bold rounded-xl transition-all shadow-sm hover:shadow-md"
          style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}
        >
          <span className="text-base leading-none font-light">+</span>
          Nova vaga
        </button>
      </div>

      {/* Formulário */}
      {criando && (
        <div className="mb-8 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-base font-bold text-slate-900 mb-5">Nova vaga</h2>
          <form onSubmit={handleSubmit} className="space-y-5">

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Nome da vaga
              </label>
              <input
                required value={form.nome}
                onChange={e => setForm(f => ({ ...f, nome: e.target.value }))}
                placeholder="ex: Desenvolvedor Python Sênior"
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Requisitos
              </label>
              <p className="text-xs text-slate-400 mb-2">
                Escreva livremente o que você busca — o sistema interpreta semanticamente.
              </p>
              <textarea
                required rows={4} value={form.requisitos_texto}
                onChange={e => setForm(f => ({ ...f, requisitos_texto: e.target.value }))}
                placeholder="ex: Python, FastAPI, PostgreSQL, Docker. Inglês intermediário. Perfil proativo e comunicativo com experiência em equipes ágeis..."
                className={`${inputClass} resize-none`}
              />
            </div>

            {/* Pesos */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-4">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Configuração de pesos
              </p>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <p className="text-xs font-semibold text-slate-600 mb-3">Score curricular</p>
                  <div className="space-y-2.5">
                    {[
                      { key: "peso_rh",      label: "Requisitos RH" },
                      { key: "peso_mercado", label: "Mercado"       },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex items-center justify-between gap-3">
                        <span className="text-sm text-slate-600">{label}</span>
                        <input
                          type="number" step="0.1" min="0" max="1"
                          value={form[key]}
                          onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) }))}
                          className="w-20 border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-center"
                        />
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-600 mb-3">Score final</p>
                  <div className="space-y-2.5">
                    {[
                      { key: "peso_curriculo",      label: "Currículo"    },
                      { key: "peso_entrevista_rh",  label: "Entrev. RH"   },
                      { key: "peso_entrevista_tec", label: "Entrev. Tec." },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex items-center justify-between gap-3">
                        <span className="text-sm text-slate-600">{label}</span>
                        <input
                          type="number" step="0.05" min="0" max="1"
                          value={form[key]}
                          onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) }))}
                          className="w-20 border border-slate-300 rounded-lg px-2.5 py-1.5 text-sm font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-center"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {erro && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <p className="text-sm text-red-600 font-medium">{erro}</p>
              </div>
            )}

            <div className="flex items-center gap-3 pt-1">
              <button type="submit"
                className="px-5 py-2.5 text-white text-sm font-bold rounded-xl transition-all shadow-sm hover:shadow-md"
                style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
                Criar vaga
              </button>
              <button type="button" onClick={() => { setCriando(false); setErro("") }}
                className="px-5 py-2.5 text-slate-500 hover:text-slate-900 text-sm font-semibold transition-colors">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="space-y-2.5">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-slate-100 rounded-2xl animate-pulse"/>
          ))}
        </div>
      ) : vagas.length === 0 ? (
        <div className="text-center py-24 border-2 border-dashed border-slate-200 rounded-2xl">
          <div className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center bg-indigo-50">
            <span className="text-indigo-400 text-xl">◫</span>
          </div>
          <p className="text-slate-500 text-sm font-semibold">Nenhuma vaga cadastrada</p>
          <p className="text-slate-400 text-xs mt-1">Clique em "Nova vaga" para começar.</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {vagas.map(v => (
            <Link key={v.id} to={`/vagas/${v.id}`}
              className="group flex items-center justify-between bg-white hover:bg-indigo-50/30 border border-slate-200 hover:border-indigo-200 rounded-2xl px-6 py-5 transition-all hover:shadow-sm">
              <div className="min-w-0">
                <p className="font-bold text-slate-900 group-hover:text-indigo-700 transition-colors">
                  {v.nome}
                </p>
                <p className="text-sm text-slate-400 mt-0.5 truncate max-w-xl">
                  {v.requisitos_texto}
                </p>
              </div>
              <div className="flex items-center gap-3 ml-6 flex-shrink-0">
                <span className="text-xs font-mono text-indigo-500 bg-indigo-50 px-2.5 py-1 rounded-lg font-semibold">
                  RH {Math.round(v.peso_rh * 100)}% · Mkt {Math.round(v.peso_mercado * 100)}%
                </span>
                <Badge cor={corStatus[v.status] ?? "gray"}>{v.status}</Badge>
                <span className="text-slate-300 group-hover:text-indigo-400 transition-colors text-lg">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
