import { useState } from "react"
import { alterarSenha } from "../api"

const PAPEL_LABEL = { rh: "RH", gestor: "Gestor técnico", admin: "Administrador" }
const PAPEL_COR   = {
  rh    : { background: "rgba(26,139,191,0.18)",  color: "#4DC8E8" },
  gestor: { background: "rgba(167,139,250,0.18)", color: "#A78BFA" },
  admin : { background: "rgba(252,211,77,0.18)",  color: "#FCD34D" },
}

export function Perfil({ usuario }) {
  const [senhaAtual, setSenhaAtual]   = useState("")
  const [senhaNova, setSenhaNova]     = useState("")
  const [confirmar, setConfirmar]     = useState("")
  const [salvando, setSalvando]       = useState(false)
  const [erro, setErro]               = useState(null)
  const [sucesso, setSucesso]         = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setErro(null)
    setSucesso(false)

    if (senhaNova.length < 6) {
      setErro("A nova senha deve ter pelo menos 6 caracteres")
      return
    }
    if (senhaNova !== confirmar) {
      setErro("A confirmação não coincide com a nova senha")
      return
    }

    setSalvando(true)
    try {
      await alterarSenha({ senha_atual: senhaAtual, senha_nova: senhaNova })
      setSucesso(true)
      setSenhaAtual("")
      setSenhaNova("")
      setConfirmar("")
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro ao alterar senha")
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="max-w-lg space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-brand-cloud">Meu perfil</h1>
        <p className="text-sm text-brand-pale/45 mt-0.5">Informações da conta e segurança</p>
      </div>

      {/* Card de identidade */}
      <div className="card-glass rounded-2xl p-6">
        <div className="flex items-center gap-4">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}
          >
            <span className="text-xl font-bold text-brand-black">
              {usuario?.nome?.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-base font-bold text-brand-cloud truncate">{usuario?.nome}</p>
            <p className="text-sm text-brand-pale/45 font-mono mt-0.5 truncate">{usuario?.email}</p>
            <span
              className="inline-block mt-2 px-2.5 py-1 rounded-lg text-xs font-bold"
              style={PAPEL_COR[usuario?.papel] ?? PAPEL_COR.rh}
            >
              {PAPEL_LABEL[usuario?.papel] ?? usuario?.papel}
            </span>
          </div>
        </div>
      </div>

      {/* Formulário de senha */}
      <div className="card-glass rounded-2xl p-6 space-y-5">
        <h2 className="text-sm font-bold text-brand-cloud">Alterar senha</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
              Senha atual
            </label>
            <input
              type="password"
              value={senhaAtual}
              onChange={e => setSenhaAtual(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2.5 rounded-xl text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
              Nova senha
            </label>
            <input
              type="password"
              value={senhaNova}
              onChange={e => { setSenhaNova(e.target.value); setSucesso(false) }}
              placeholder="Mínimo 6 caracteres"
              className="w-full px-3 py-2.5 rounded-xl text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
              Confirmar nova senha
            </label>
            <input
              type="password"
              value={confirmar}
              onChange={e => { setConfirmar(e.target.value); setSucesso(false) }}
              placeholder="Repita a nova senha"
              className="w-full px-3 py-2.5 rounded-xl text-sm"
              required
            />
            {/* indicador de match em tempo real */}
            {confirmar && (
              <p className={`text-xs mt-1.5 ${senhaNova === confirmar ? "text-brand-mint" : "text-red-400"}`}>
                {senhaNova === confirmar ? "✓ As senhas coincidem" : "✗ As senhas não coincidem"}
              </p>
            )}
          </div>

          {erro    && (
            <div className="px-4 py-3 rounded-xl text-sm text-red-400"
              style={{ background: "rgba(252,165,165,0.1)", border: "1px solid rgba(252,165,165,0.2)" }}>
              {erro}
            </div>
          )}
          {sucesso && (
            <div className="px-4 py-3 rounded-xl text-sm text-brand-mint"
              style={{ background: "rgba(46,232,180,0.08)", border: "1px solid rgba(46,232,180,0.2)" }}>
              Senha alterada com sucesso.
            </div>
          )}

          <button
            type="submit"
            disabled={salvando || senhaNova !== confirmar}
            className="w-full py-2.5 rounded-xl text-sm font-bold text-brand-black disabled:opacity-40 transition-opacity"
            style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}
          >
            {salvando ? "Salvando..." : "Alterar senha"}
          </button>
        </form>
      </div>
    </div>
  )
}
