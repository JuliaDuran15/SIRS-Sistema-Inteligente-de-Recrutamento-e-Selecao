import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import api from "../api"
import logo from "../assets/logo.png"

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
<div className="auth-page flex h-screen w-screen items-center justify-center p-4">
      
      {/* O Card */}
      <div className="w-full max-w-[400px] rounded-3xl border border-brand-sky/20 bg-brand-teal/20 p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col items-center">
             <h1 className="text-2xl font-bold text-white">Entrar no SIRS</h1>
        
        {/* LOGO E HEADER */}
        <div className="flex flex-col items-center mb-8">
          <img
            src={logo}
            alt="SIRS Logo"
            className="h-20 w-auto mb-2 object-contain"
          />
          <p className="text-sm text-white/50 mt-2">
            Acesse sua conta para continuar
          </p>
        </div>

        {/* FORMULÁRIO */}
        <form onSubmit={handleSubmit} className="w-full space-y-5">
          <div className="space-y-1">
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="Email"
              className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A8BBF] transition-all"
            />
          </div>

          <div className="space-y-1">
            <input
              type="password"
              required
              value={senha}
              onChange={e => setSenha(e.target.value)}
              placeholder="Senha"
              className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A8BBF] transition-all"
            />
          </div>

          {erro && (
            <div className="bg-red-500/10 border border-red-500/20 py-2 px-4 rounded-lg">
              <p className="text-xs text-red-400 text-center">{erro}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl text-sm font-bold text-white transition-all hover:brightness-110 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-[#1A8BBF]/20"
            style={{ background: "linear-gradient(135deg, #1A8BBF 0%, #4DC8E8 100%)" }}
          >
            {loading ? "Processando..." : "Entrar na Plataforma"}
          </button>

          <div className="text-center">
            <Link
              to="/esqueceu-senha"
              className="text-xs text-white/35 hover:text-white/60 transition-colors"
            >
              Esqueceu a senha?
            </Link>
          </div>
        </form>

        {/* DIVIDER */}
        <div className="w-full my-8 flex items-center gap-3">
          <div className="flex-1 h-[1px] bg-white/10" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-white/30">Acesso Rápido</span>
          <div className="flex-1 h-[1px] bg-white/10" />
        </div>

        {/* USERS DE TESTE (STAGED USERS) */}
        <div className="w-full grid grid-cols-1 gap-2">
          {[
            { email: "ana@sirs.com", papel: "RH" },
            { email: "carlos@sirs.com", papel: "Gestor" },
            { email: "admin@sirs.com", papel: "Admin" },
          ].map(u => (
            <button
              key={u.email}
              type="button"
              onClick={() => {
                setEmail(u.email)
                setSenha("admin123")
              }}
              className="w-full flex justify-between items-center px-4 py-2.5 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/10 hover:border-white/20 transition-all group"
            >
              <span className="text-xs text-white/60 group-hover:text-white transition-colors">{u.email}</span>
              <span className="text-[10px] bg-[#1A8BBF]/20 text-[#4DC8E8] px-2 py-0.5 rounded-md font-bold uppercase">
                {u.papel}
              </span>
            </button>
          ))}
        </div>
</div>
      </div>
      </div>
  )
}
