import { useState, useEffect, useRef } from "react"
import { getConfig, updateConfig, verificarSenha } from "../api"
import { useToast } from "../hooks/useToast"
import { ToastContainer } from "../components/ToastContainer"

function ModalConfirmaSenha({ onConfirmar, onCancelar, verificando }) {
  const [senha,   setSenha]   = useState("")
  const [visivel, setVisivel] = useState(false)
  const inputRef              = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(7,17,26,0.75)", backdropFilter: "blur(6px)" }}
      onClick={e => e.target === e.currentTarget && onCancelar()}
    >
      <div
        className="rounded-2xl p-6 w-full max-w-sm mx-4"
        style={{
          background: "var(--s-header)",
          border    : "1px solid var(--b-card)",
          boxShadow : "0 24px 64px rgba(0,0,0,0.5)",
        }}
      >
        {/* Ícone */}
        <div
          className="w-11 h-11 rounded-full flex items-center justify-center mb-4"
          style={{ background: "rgba(26,139,191,0.15)", border: "1px solid rgba(77,200,232,0.25)" }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            stroke="var(--color-brand-sky)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
        </div>

        <h3 className="text-base font-bold mb-1" style={{ color: "var(--t-main)" }}>
          Confirme sua senha
        </h3>
        <p className="text-sm mb-5" style={{ color: "var(--t-sub)" }}>
          Para salvar as configurações, insira sua senha de acesso.
        </p>

        <form onSubmit={e => { e.preventDefault(); onConfirmar(senha) }} className="space-y-4">
          <div className="relative">
            <input
              ref={inputRef}
              type={visivel ? "text" : "password"}
              value={senha}
              onChange={e => setSenha(e.target.value)}
              placeholder="Sua senha"
              required
              autoComplete="current-password"
              className="w-full rounded-xl px-4 py-2.5 pr-10 text-sm font-medium outline-none transition-all"
              style={{
                background: "var(--s-chip-dark)",
                border    : "1px solid var(--b-normal)",
                color     : "var(--t-main)",
              }}
              onFocus={e => e.target.style.borderColor = "var(--color-brand-sky)"}
              onBlur={e  => e.target.style.borderColor = "var(--b-normal)"}
            />
            <button
              type="button"
              onClick={() => setVisivel(v => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 opacity-50 hover:opacity-100 transition-opacity"
              style={{ color: "var(--t-muted2)" }}
              tabIndex={-1}
            >
              {visivel ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              )}
            </button>
          </div>

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onCancelar}
              disabled={verificando}
              className="flex-1 py-2 rounded-xl text-sm font-semibold transition-all"
              style={{
                background: "var(--s-chip-dark)",
                border    : "1px solid var(--b-normal)",
                color     : "var(--t-muted2)",
              }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={verificando || !senha}
              className="flex-1 py-2 rounded-xl text-sm font-semibold transition-all disabled:opacity-50"
              style={{
                background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)",
                color     : "#07111A",
              }}
            >
              {verificando ? "Verificando…" : "Confirmar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function ConfigEmpresa() {
  const [nomeEmpresa,   setNomeEmpresa]   = useState("")
  const [carregando,    setCarregando]    = useState(true)
  const [salvando,      setSalvando]      = useState(false)
  const [verificando,   setVerificando]   = useState(false)
  const [modalAberto,   setModalAberto]   = useState(false)
  const { toasts, mostrarToast }          = useToast()

  const usuario = (() => {
    try { return JSON.parse(localStorage.getItem("usuario")) } catch { return null }
  })()

  useEffect(() => {
    getConfig()
      .then(r => setNomeEmpresa(r.data.nome_empresa))
      .catch(() => mostrarToast("Erro ao carregar configurações", "erro"))
      .finally(() => setCarregando(false))
  }, [])

  function pedirConfirmacao(e) {
    e.preventDefault()
    if (!nomeEmpresa.trim()) return
    setModalAberto(true)
  }

  async function confirmarComSenha(senha) {
    if (!usuario?.email) return
    setVerificando(true)
    try {
      await verificarSenha(usuario.email, senha)
    } catch {
      mostrarToast("Senha incorreta", "erro")
      setVerificando(false)
      return
    }
    setVerificando(false)
    setModalAberto(false)
    await _salvar()
  }

  async function _salvar() {
    setSalvando(true)
    try {
      const r = await updateConfig({ nome_empresa: nomeEmpresa.trim() })
      localStorage.setItem("config_nome_empresa", r.data.nome_empresa)
      window.dispatchEvent(new CustomEvent("config_empresa_atualizada", { detail: r.data.nome_empresa }))
      mostrarToast("Configurações salvas com sucesso", "sucesso")
    } catch {
      mostrarToast("Erro ao salvar configurações", "erro")
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <ToastContainer toasts={toasts} />

      {modalAberto && (
        <ModalConfirmaSenha
          onConfirmar={confirmarComSenha}
          onCancelar={() => setModalAberto(false)}
          verificando={verificando}
        />
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold" style={{ color: "var(--t-main)" }}>
          Configurações do sistema
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--t-sub)" }}>
          Personalize como o SIRS aparece para sua equipe.
        </p>
      </div>

      {/* Card */}
      <div className="card-glass rounded-2xl p-6">
        <h2 className="text-sm font-bold uppercase tracking-widest mb-5" style={{ color: "var(--t-faint2)" }}>
          Identidade da empresa
        </h2>

        {carregando ? (
          <div className="h-10 rounded-xl animate-pulse" style={{ background: "var(--s-chip-dark)" }} />
        ) : (
          <form onSubmit={pedirConfirmacao} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold mb-2" style={{ color: "var(--t-muted2)" }}>
                Nome da empresa
              </label>
              <input
                value={nomeEmpresa}
                onChange={e => setNomeEmpresa(e.target.value)}
                maxLength={200}
                placeholder="Ex: Acme Corp"
                required
                className="w-full rounded-xl px-4 py-2.5 text-sm font-medium outline-none transition-all"
                style={{
                  background: "var(--s-chip-dark)",
                  border    : "1px solid var(--b-normal)",
                  color     : "var(--t-main)",
                }}
                onFocus={e => e.target.style.borderColor = "var(--color-brand-sky)"}
                onBlur={e  => e.target.style.borderColor = "var(--b-normal)"}
              />
              <p className="text-xs mt-1.5" style={{ color: "var(--t-faint2)" }}>
                Aparece na barra lateral e em e-mails enviados pelo sistema.
              </p>
            </div>

            <div className="pt-1 flex justify-end">
              <button
                type="submit"
                disabled={salvando || !nomeEmpresa.trim()}
                className="btn-primary px-5 py-2 rounded-xl text-sm font-semibold transition-all disabled:opacity-50"
              >
                {salvando ? "Salvando…" : "Salvar"}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Preview */}
      {!carregando && nomeEmpresa.trim() && (
        <div className="mt-4 rounded-2xl p-4" style={{ background: "var(--s-chip-dark)", border: "1px solid var(--b-subtle)" }}>
          <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--t-faint2)" }}>
            Pré-visualização na sidebar
          </p>
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-sm flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)", color: "#07111A" }}
            >
              {nomeEmpresa.trim().charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-bold leading-tight" style={{ color: "var(--color-brand-sky)" }}>
                {nomeEmpresa.trim()}
              </p>
              <p className="text-xs leading-tight" style={{ color: "var(--t-sub)" }}>
                Recrutamento Inteligente
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
