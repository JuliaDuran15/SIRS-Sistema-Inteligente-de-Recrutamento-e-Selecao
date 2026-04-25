import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { getVagas, createVaga } from "../api"
import { Badge } from "../components/Badge"

const PESOS = {
  peso_rh: 0.6, peso_mercado: 0.4,
  peso_curriculo: 0.5, peso_entrevista_rh: 0.25, peso_entrevista_tec: 0.25,
}

const corStatus = { aberta: "green", pausada: "amber", fechada: "gray" }

const inputClass = "w-full rounded-xl px-4 py-2.5 text-sm transition-all"
const numInputClass = "w-20 rounded-lg px-2.5 py-1.5 text-sm font-mono text-center transition-all"

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
          <h1 className="text-2xl font-bold text-brand-cloud">Vagas</h1>
          <p className="text-sm text-brand-pale/45 mt-1 font-medium">
            {loading ? "Carregando..." : `${vagas.length} ${vagas.length === 1 ? "vaga cadastrada" : "vagas cadastradas"}`}
          </p>
        </div>
        <button
          onClick={() => setCriando(!criando)}
          className="flex items-center gap-2 px-4 py-2.5 text-brand-black text-sm font-bold rounded-xl transition-all hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}
        >
          <span className="text-base leading-none font-light">+</span>
          Nova vaga
        </button>
      </div>

      {/* Formulário */}
      {criando && (
        <div className="card-glass rounded-2xl p-6 mb-8">
          <h2 className="text-base font-bold text-brand-cloud mb-5">Nova vaga</h2>
          <form onSubmit={handleSubmit} className="space-y-5">

            <div>
              <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
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
              <label className="block text-xs font-bold text-brand-pale/65 uppercase tracking-wider mb-1.5">
                Requisitos
              </label>
              <p className="text-xs text-brand-pale/38 mb-2">
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
            <div className="card-inner rounded-xl p-4 space-y-4">
              <p className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
                Configuração de pesos
              </p>
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
                        <input
                          type="number" step="0.1" min="0" max="1"
                          value={form[key]}
                          onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) }))}
                          className={numInputClass}
                        />
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
                        <input
                          type="number" step="0.05" min="0" max="1"
                          value={form[key]}
                          onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) }))}
                          className={numInputClass}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {erro && (
              <div
                className="rounded-xl px-4 py-3"
                style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)" }}
              >
                <p className="text-sm font-medium" style={{ color: "#FCA5A5" }}>{erro}</p>
              </div>
            )}

            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                className="px-5 py-2.5 text-brand-black text-sm font-bold rounded-xl transition-all hover:opacity-90"
                style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}
              >
                Criar vaga
              </button>
              <button
                type="button"
                onClick={() => { setCriando(false); setErro("") }}
                className="px-5 py-2.5 text-brand-pale/45 hover:text-brand-cloud text-sm font-semibold transition-colors"
              >
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
            <div
              key={i}
              className="h-20 rounded-2xl animate-pulse"
              style={{ background: "rgba(14, 80, 104, 0.2)" }}
            />
          ))}
        </div>
      ) : vagas.length === 0 ? (
        <div
          className="text-center py-24 rounded-2xl border-2 border-dashed"
          style={{ borderColor: "rgba(77, 200, 232, 0.14)" }}
        >
          <div
            className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center"
            style={{ background: "rgba(26, 139, 191, 0.14)" }}
          >
            <span className="text-brand-sky text-xl">◫</span>
          </div>
          <p className="text-brand-pale/55 text-sm font-semibold">Nenhuma vaga cadastrada</p>
          <p className="text-brand-pale/35 text-xs mt-1">Clique em "Nova vaga" para começar.</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {vagas.map(v => (
            <Link
              key={v.id}
              to={`/vagas/${v.id}`}
              className="group card-interactive flex items-center justify-between rounded-2xl px-6 py-5"
            >
              <div className="min-w-0">
                <p className="font-bold text-brand-cloud group-hover:text-brand-sky transition-colors">
                  {v.nome}
                </p>
                <p className="text-sm text-brand-pale/45 mt-0.5 truncate max-w-xl">
                  {v.requisitos_texto}
                </p>
              </div>
              <div className="flex items-center gap-3 ml-6 flex-shrink-0">
                <span
                  className="text-xs font-mono px-2.5 py-1 rounded-lg font-semibold"
                  style={{ background: "rgba(26, 139, 191, 0.15)", color: "#4DC8E8" }}
                >
                  RH {Math.round(v.peso_rh * 100)}% · Mkt {Math.round(v.peso_mercado * 100)}%
                </span>
                <Badge cor={corStatus[v.status] ?? "gray"}>{v.status}</Badge>
                <span className="text-brand-pale/30 group-hover:text-brand-sky transition-colors text-lg">→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
