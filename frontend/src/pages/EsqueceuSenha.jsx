import { useState } from "react"
import { Link } from "react-router-dom"
import { esqueceuSenha } from "../api"
import logo from "../assets/logo.png"

export function EsqueceuSenha() {
  const [email, setEmail]       = useState("")
  const [loading, setLoading]   = useState(false)
  const [erro, setErro]         = useState("")
  const [resetUrl, setResetUrl] = useState(null) // preenchido quando SMTP não configurado
  const [enviado, setEnviado]   = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setErro("")
    setLoading(true)
    try {
      const r = await esqueceuSenha(email)
      if (r.data.reset_url) {
        // SMTP não configurado — exibe link diretamente (modo dev/interno)
        setResetUrl(r.data.reset_url)
      } else {
        setEnviado(true)
      }
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Email não encontrado")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page flex h-screen w-screen items-center justify-center p-4">
      <div className="w-full max-w-[400px] rounded-3xl border border-brand-sky/20 bg-brand-teal/20 p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col items-center">

          <div className="flex flex-col items-center mb-8">
            <img src={logo} alt="SIRS" className="h-16 w-auto mb-2 object-contain" />
            <h1 className="text-xl font-bold text-white mt-2">Esqueceu a senha?</h1>
            <p className="text-sm text-white/50 mt-1 text-center">
              Informe seu e-mail para receber o link de redefinição.
            </p>
          </div>

          {enviado ? (
            <div className="w-full space-y-4 text-center">
              <div className="bg-emerald-500/10 border border-emerald-500/20 px-4 py-4 rounded-xl">
                <p className="text-sm text-emerald-400 font-semibold">E-mail enviado!</p>
                <p className="text-xs text-emerald-400/70 mt-1">
                  Verifique sua caixa de entrada e clique no link para redefinir sua senha.
                  O link expira em 1 hora.
                </p>
              </div>
              <Link to="/login"
                className="block text-sm text-white/40 hover:text-white/70 transition-colors">
                ← Voltar ao login
              </Link>
            </div>
          ) : resetUrl ? (
            /* Modo dev/interno: SMTP não configurado, exibe link direto */
            <div className="w-full space-y-4">
              <div className="bg-amber-500/10 border border-amber-500/20 px-4 py-4 rounded-xl space-y-3">
                <p className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                  Modo dev — SMTP não configurado
                </p>
                <p className="text-xs text-amber-400/70">
                  Em produção este link seria enviado por e-mail. Clique para redefinir a senha:
                </p>
                <Link
                  to={`/resetar-senha?token=${new URL(resetUrl).searchParams.get("token")}`}
                  className="block w-full py-2.5 rounded-xl text-center text-xs font-bold text-brand-black"
                  style={{ background: "linear-gradient(135deg,#1A8BBF,#4DC8E8)" }}
                >
                  Ir para redefinição de senha
                </Link>
              </div>
              <Link to="/login"
                className="block text-center text-sm text-white/40 hover:text-white/70 transition-colors">
                ← Voltar ao login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="w-full space-y-4">
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A8BBF] transition-all"
              />

              {erro && (
                <div className="bg-red-500/10 border border-red-500/20 py-2 px-4 rounded-lg">
                  <p className="text-xs text-red-400 text-center">{erro}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 rounded-xl text-sm font-bold text-white transition-all hover:brightness-110 disabled:opacity-50"
                style={{ background: "linear-gradient(135deg,#1A8BBF 0%,#4DC8E8 100%)" }}
              >
                {loading ? "Enviando..." : "Enviar link de redefinição"}
              </button>

              <Link to="/login"
                className="block text-center text-sm text-white/40 hover:text-white/70 transition-colors">
                ← Voltar ao login
              </Link>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
