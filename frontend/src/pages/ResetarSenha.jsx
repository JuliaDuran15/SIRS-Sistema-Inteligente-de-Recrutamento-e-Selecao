import { useState } from "react"
import { Link, useSearchParams, useNavigate } from "react-router-dom"
import { resetarSenha } from "../api"
import logo from "../assets/logo.png"

export function ResetarSenha() {
  const [params]              = useSearchParams()
  const navigate              = useNavigate()
  const token                 = params.get("token") ?? ""

  const [senhaNova, setSenha]   = useState("")
  const [confirmar, setConf]    = useState("")
  const [loading, setLoading]   = useState(false)
  const [erro, setErro]         = useState("")
  const [sucesso, setSucesso]   = useState(false)

  if (!token) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-brand-black p-4">
        <div className="text-center space-y-3">
          <p className="text-red-400 text-sm">Link inválido ou expirado.</p>
          <Link to="/esqueceu-senha"
            className="text-sm text-brand-sky hover:text-brand-pale transition-colors">
            Solicitar novo link
          </Link>
        </div>
      </div>
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErro("")
    if (senhaNova.length < 6) { setErro("A senha deve ter pelo menos 6 caracteres"); return }
    if (senhaNova !== confirmar) { setErro("As senhas não coincidem"); return }

    setLoading(true)
    try {
      await resetarSenha({ reset_token: token, senha_nova: senhaNova })
      setSucesso(true)
      setTimeout(() => navigate("/login"), 2500)
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Token inválido ou expirado")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-brand-black p-4">
      <div className="w-full max-w-[400px] rounded-3xl border border-brand-sky/20 bg-brand-teal/20 p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col items-center">

          <div className="flex flex-col items-center mb-8">
            <img src={logo} alt="SIRS" className="h-16 w-auto mb-2 object-contain" />
            <h1 className="text-xl font-bold text-white mt-2">Redefinir senha</h1>
            <p className="text-sm text-white/50 mt-1">Digite sua nova senha abaixo.</p>
          </div>

          {sucesso ? (
            <div className="w-full text-center space-y-3">
              <div className="bg-emerald-500/10 border border-emerald-500/20 px-4 py-4 rounded-xl">
                <p className="text-sm text-emerald-400 font-semibold">Senha redefinida!</p>
                <p className="text-xs text-emerald-400/70 mt-1">
                  Redirecionando para o login…
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="w-full space-y-4">
              <input
                type="password"
                required
                value={senhaNova}
                onChange={e => setSenha(e.target.value)}
                placeholder="Nova senha (mín. 6 caracteres)"
                className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A8BBF] transition-all"
              />
              <div>
                <input
                  type="password"
                  required
                  value={confirmar}
                  onChange={e => setConf(e.target.value)}
                  placeholder="Confirmar nova senha"
                  className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-2 focus:ring-[#1A8BBF] transition-all"
                />
                {confirmar && (
                  <p className={`text-xs mt-1.5 px-1 ${senhaNova === confirmar ? "text-emerald-400" : "text-red-400"}`}>
                    {senhaNova === confirmar ? "✓ As senhas coincidem" : "✗ As senhas não coincidem"}
                  </p>
                )}
              </div>

              {erro && (
                <div className="bg-red-500/10 border border-red-500/20 py-2 px-4 rounded-lg">
                  <p className="text-xs text-red-400 text-center">{erro}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || senhaNova !== confirmar}
                className="w-full py-3.5 rounded-xl text-sm font-bold text-white transition-all hover:brightness-110 disabled:opacity-50"
                style={{ background: "linear-gradient(135deg,#1A8BBF 0%,#4DC8E8 100%)" }}
              >
                {loading ? "Salvando..." : "Redefinir senha"}
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