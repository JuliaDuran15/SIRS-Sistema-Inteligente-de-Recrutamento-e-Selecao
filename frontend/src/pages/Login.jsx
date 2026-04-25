import { useState } from "react"
import { useNavigate } from "react-router-dom"
import api from "../api"

export function Login({ onLogin }) {
  const [email, setEmail]     = useState("")
  const [senha, setSenha]     = useState("")
  const [erro, setErro]       = useState("")
  const [loading, setLoading] = useState(false)
  const navigate              = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setErro("")
    setLoading(true)

    try {
      const form = new URLSearchParams()
      form.append("username", email)
      form.append("password", senha)

      const r = await api.post("/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      })

      const { access_token, usuario } = r.data

      localStorage.setItem("token",   access_token)
      localStorage.setItem("usuario", JSON.stringify(usuario))

      api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`

      onLogin(usuario)
      navigate("/")
    } catch (e) {
      setErro(e.response?.data?.detail || "Email ou senha incorretos")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">

      {/* Left: brand panel */}
      <div className="hidden lg:flex lg:w-[45%] flex-col items-center justify-center p-12 relative overflow-hidden"
        style={{ background: "linear-gradient(145deg, #4338ca 0%, #4f46e5 45%, #7c3aed 100%)" }}>

        {/* Decorative blobs */}
        <div className="absolute top-0 right-0 w-80 h-80 rounded-full opacity-20"
          style={{ background: "radial-gradient(circle, #a5b4fc, transparent)", transform: "translate(30%, -30%)" }}/>
        <div className="absolute bottom-0 left-0 w-64 h-64 rounded-full opacity-15"
          style={{ background: "radial-gradient(circle, #c4b5fd, transparent)", transform: "translate(-30%, 30%)" }}/>

        <div className="relative z-10 text-center max-w-xs">
          {/* Logo */}
          <div className="w-20 h-20 rounded-3xl flex items-center justify-center mx-auto mb-8 shadow-lg"
            style={{ background: "rgba(255,255,255,0.2)", backdropFilter: "blur(8px)" }}>
            <span className="text-white font-mono text-3xl font-bold">S</span>
          </div>

          <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">SIRS</h1>
          <p className="text-indigo-200 text-base leading-relaxed mb-10">
            Sistema Inteligente de<br/>Recrutamento e Seleção
          </p>

          {/* Feature pills */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { icon: "✦", label: "IA Semântica" },
              { icon: "◈", label: "Ranking Auto" },
              { icon: "◎", label: "Tendências" },
            ].map(f => (
              <div key={f.label}
                className="rounded-2xl p-3 text-center"
                style={{ background: "rgba(255,255,255,0.1)" }}>
                <p className="text-white text-lg mb-1">{f.icon}</p>
                <p className="text-indigo-200 text-xs font-medium leading-tight">{f.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: form panel */}
      <div className="flex-1 flex items-center justify-center bg-white px-8 py-12">
        <div className="w-full max-w-sm">

          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-10">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
              <span className="text-white font-mono text-lg font-bold">S</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">SIRS</h1>
            <p className="text-sm text-slate-400 mt-1">Sistema Inteligente de Recrutamento</p>
          </div>

          <h2 className="text-2xl font-bold text-slate-900 mb-1">Bem-vindo de volta</h2>
          <p className="text-sm text-slate-500 mb-8">Entre com sua conta para continuar</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email</label>
              <input
                type="email" required value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                className="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Senha</label>
              <input
                type="password" required value={senha}
                onChange={e => setSenha(e.target.value)}
                placeholder="••••••••"
                className="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"
              />
            </div>

            {erro && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <p className="text-sm text-red-600 font-medium">{erro}</p>
              </div>
            )}

            <button
              type="submit" disabled={loading}
              className="w-full py-3 text-white text-sm font-bold rounded-xl transition-all shadow-sm hover:shadow-md disabled:opacity-50 mt-2"
              style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}
            >
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>

          {/* Test users */}
          <div className="mt-8 pt-6 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Usuários de teste
            </p>
            <div className="space-y-1">
              {[
                { email: "ana@sirs.com",    papel: "RH"     },
                { email: "carlos@sirs.com", papel: "Gestor" },
                { email: "admin@sirs.com",  papel: "Admin"  },
              ].map(u => (
                <button key={u.email}
                  onClick={() => { setEmail(u.email); setSenha("senha123") }}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-slate-50 transition-colors group"
                >
                  <span className="text-xs font-mono text-slate-500 group-hover:text-slate-700">
                    {u.email}
                  </span>
                  <span className="text-xs bg-indigo-50 text-indigo-600 px-2.5 py-0.5 rounded-full font-semibold">
                    {u.papel}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
