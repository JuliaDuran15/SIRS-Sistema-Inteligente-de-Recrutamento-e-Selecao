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
  <div className="auth-page flex min-h-screen w-screen items-center justify-center p-4 relative overflow-hidden">

    {/* Radial glow de fundo */}
    <div
      className="pointer-events-none absolute inset-0 flex items-center justify-center"
      aria-hidden="true"
    >
      <div className="h-[480px] w-[480px] rounded-full opacity-[0.18]"
        style={{ background: "radial-gradient(circle, #1A8BBF 0%, transparent 70%)" }} />
    </div>

    {/* Card */}
    <div className="relative w-full max-w-[400px] rounded-3xl p-8 shadow-2xl backdrop-blur-xl"
      style={{
        background: "rgba(14, 80, 104, 0.22)",
        border: "1px solid rgba(77, 200, 232, 0.18)",
        boxShadow: "0 8px 40px rgba(7,17,26,0.5), inset 0 1px 0 rgba(255,255,255,0.06)",
      }}>

      {/* Logo + Header */}
      <div className="flex flex-col items-center mb-8">
        <div className="mb-5 overflow-hidden rounded-2xl"
          style={{ background: "rgba(77,200,232,0.08)", border: "1px solid rgba(77,200,232,0.15)" }}>
          <img src={logo} alt="SIRS" className="h-16 w-auto object-contain p-2" />
        </div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Entrar no SIRS</h1>
        <p className="mt-1.5 text-sm text-white/45">Acesse sua conta para continuar</p>
      </div>

      {/* Formulário */}
      <form onSubmit={handleSubmit} className="w-full space-y-4">
        <input
          type="email"
          required
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="Email"
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3.5 text-sm text-white placeholder-white/30 transition-all focus:outline-none focus:ring-2 focus:ring-[#1A8BBF]/60"
        />

        <input
          type="password"
          required
          value={senha}
          onChange={e => setSenha(e.target.value)}
          placeholder="Senha"
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3.5 text-sm text-white placeholder-white/30 transition-all focus:outline-none focus:ring-2 focus:ring-[#1A8BBF]/60"
        />

        {erro && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-2.5">
            <p className="text-center text-xs text-red-400">{erro}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-1 w-full rounded-xl py-3.5 text-sm font-bold text-white shadow-lg transition-all hover:brightness-110 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            background: "linear-gradient(135deg, #1A8BBF 0%, #4DC8E8 100%)",
            boxShadow: "0 4px 14px rgba(26,139,191,0.35)",
          }}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round"/>
              </svg>
              Processando...
            </span>
          ) : "Entrar na Plataforma"}
        </button>

        <div className="text-center">
          <Link to="/esqueceu-senha" className="text-xs text-white/35 transition-colors hover:text-white/60">
            Esqueceu a senha?
          </Link>
        </div>
      </form>

      {/* Divider + Contas de teste (desativado em produção)
      <div className="my-7 flex w-full items-center gap-3">
        <div className="h-px flex-1 bg-white/10" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-white/25">Acesso Rápido</span>
        <div className="h-px flex-1 bg-white/10" />
      </div>
      <div className="w-full space-y-2">
        {[
          { email: "ana@sirs.com", papel: "RH" },
          { email: "carlos@sirs.com", papel: "Gestor" },
          { email: "admin@sirs.com", papel: "Admin" },
        ].map(u => (
          <button
            key={u.email}
            type="button"
            onClick={() => { setEmail(u.email); setSenha("admin123") }}
            className="group w-full flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-2.5 transition-all hover:border-white/15 hover:bg-white/8"
          >
            <span className="text-xs text-white/55 transition-colors group-hover:text-white/80">{u.email}</span>
            <span className="rounded-md bg-[#1A8BBF]/20 px-2 py-0.5 text-[10px] font-bold uppercase text-[#4DC8E8]">
              {u.papel}
            </span>
          </button>
        ))}
      </div>
      */}
    </div>
  </div>
)
}
