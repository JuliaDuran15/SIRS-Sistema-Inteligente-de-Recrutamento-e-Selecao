import { useState, useEffect } from "react"
import { getUsuarios, createUsuario, deleteUsuario } from "../api"

const PAPEL_COR   = { rh: "blue", gestor: "purple", admin: "amber" }
const PAPEL_LABEL = { rh: "RH", gestor: "Gestor técnico", admin: "Admin" }

function BadgeRole({ papel }) {
  const cores = {
    blue  : { background: "rgba(26,139,191,0.18)",  color: "#4DC8E8" },
    purple: { background: "rgba(167,139,250,0.18)", color: "#A78BFA" },
    amber : { background: "rgba(252,211,77,0.18)",  color: "#FCD34D" },
  }
  return (
    <span className="px-2.5 py-1 rounded-lg text-xs font-bold"
      style={cores[PAPEL_COR[papel]] ?? cores.blue}>
      {PAPEL_LABEL[papel] ?? papel}
    </span>
  )
}

function ModalNovoUsuario({ onSalvo, onFechar }) {
  const [form, setForm]     = useState({ nome: "", email: "", senha: "", papel: "rh" })
  const [erro, setErro]     = useState(null)
  const [salvando, setSalv] = useState(false)

  function set(campo, valor) { setForm(f => ({ ...f, [campo]: valor })) }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.nome.trim() || !form.email.trim() || !form.senha.trim()) {
      setErro("Preencha todos os campos"); return
    }
    setSalv(true); setErro(null)
    try {
      const r = await createUsuario(form)
      onSalvo(r.data)
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro ao criar usuário")
    } finally {
      setSalv(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(7,17,26,0.75)", backdropFilter: "blur(4px)" }}>
      <div className="card-glass rounded-2xl p-6 w-full max-w-md space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-brand-cloud">Novo usuário</h2>
          <button onClick={onFechar}
            className="text-brand-pale/40 hover:text-brand-pale transition-colors text-lg leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
              Nome completo
            </label>
            <input value={form.nome} onChange={e => set("nome", e.target.value)}
              placeholder="Ex.: Ana Paula Ramos"
              className="w-full px-3 py-2.5 rounded-xl text-sm" />
          </div>
          <div>
            <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
              Email
            </label>
            <input type="email" value={form.email} onChange={e => set("email", e.target.value)}
              placeholder="ana@empresa.com"
              className="w-full px-3 py-2.5 rounded-xl text-sm" />
          </div>
          <div>
            <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
              Senha
            </label>
            <input type="password" value={form.senha} onChange={e => set("senha", e.target.value)}
              placeholder="Mínimo 6 caracteres"
              className="w-full px-3 py-2.5 rounded-xl text-sm" />
          </div>
          <div>
            <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
              Papel
            </label>
            <div className="flex gap-2">
              {["rh", "gestor"].map(p => (
                <button key={p} type="button"
                  onClick={() => set("papel", p)}
                  className="flex-1 py-2.5 rounded-xl text-xs font-bold transition-all"
                  style={form.papel === p
                    ? { background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)", color: "#07111A" }
                    : { background: "var(--s-chip)", color: "var(--t-muted2)",
                        border: "1px solid rgba(77,200,232,0.15)" }}>
                  {PAPEL_LABEL[p]}
                </button>
              ))}
            </div>
          </div>

          {erro && <p className="text-xs text-red-400">{erro}</p>}

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onFechar}
              className="flex-1 py-2.5 rounded-xl text-xs font-bold text-brand-pale/50 transition-colors hover:text-brand-pale"
              style={{ border: "1px solid rgba(77,200,232,0.15)" }}>
              Cancelar
            </button>
            <button type="submit" disabled={salvando}
              className="flex-1 py-2.5 rounded-xl text-xs font-bold text-brand-black disabled:opacity-50"
              style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
              {salvando ? "Criando..." : "Criar usuário"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function AdminUsuarios() {
  const [usuarios, setUsuarios]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [modal, setModal]         = useState(false)
  const [deletando, setDeletando] = useState(null)
  const [erro, setErro]           = useState(null)

  useEffect(() => {
    getUsuarios()
      .then(r => setUsuarios(r.data))
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(u) {
    if (!confirm(`Desativar ${u.nome}? O usuário perderá acesso ao sistema.`)) return
    setDeletando(u.id)
    setErro(null)
    try {
      await deleteUsuario(u.id)
      setUsuarios(prev => prev.filter(x => x.id !== u.id))
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro ao desativar usuário")
    } finally {
      setDeletando(null)
    }
  }

  function onSalvo(novo) {
    setUsuarios(prev => [...prev, novo])
    setModal(false)
  }

  const porPapel = papeis => usuarios.filter(u => papeis.includes(u.papel))

  if (loading) return (
    <div className="space-y-4">
      {[1,2,3].map(i => (
        <div key={i} className="h-16 rounded-2xl animate-pulse"
          style={{ background: "var(--s-skeleton)" }} />
      ))}
    </div>
  )

  return (
    <div className="space-y-6">
      {modal && <ModalNovoUsuario onSalvo={onSalvo} onFechar={() => setModal(false)} />}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-brand-cloud">Gerenciar Usuários</h1>
          <p className="text-sm text-brand-pale/45 mt-0.5">
            {usuarios.length} {usuarios.length === 1 ? "usuário ativo" : "usuários ativos"}
          </p>
        </div>
        <button onClick={() => setModal(true)}
          className="px-4 py-2.5 rounded-xl text-sm font-bold text-brand-black"
          style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
          + Novo usuário
        </button>
      </div>

      {erro && (
        <div className="px-4 py-3 rounded-xl text-sm text-red-400"
          style={{ background: "rgba(252,165,165,0.1)", border: "1px solid rgba(252,165,165,0.2)" }}>
          {erro}
        </div>
      )}

      {/* Tabela RH */}
      <Secao titulo="RH" usuarios={porPapel(["rh"])}
        onDelete={handleDelete} deletando={deletando} />

      {/* Tabela Gestores */}
      <Secao titulo="Gestores Técnicos" usuarios={porPapel(["gestor"])}
        onDelete={handleDelete} deletando={deletando} />

      {/* Tabela Admin (só leitura) */}
      <Secao titulo="Administradores" usuarios={porPapel(["admin"])}
        onDelete={handleDelete} deletando={deletando} soLeitura />
    </div>
  )
}

function Secao({ titulo, usuarios, onDelete, deletando, soLeitura }) {
  if (usuarios.length === 0) return null

  return (
    <div>
      <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-3">{titulo}</h2>
      <div className="space-y-2">
        {usuarios.map(u => (
          <div key={u.id} className="card-glass rounded-2xl px-5 py-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
                <span className="text-sm font-bold text-brand-black">
                  {u.nome.charAt(0).toUpperCase()}
                </span>
              </div>
              <div>
                <p className="text-sm font-semibold text-brand-cloud">{u.nome}</p>
                <p className="text-xs text-brand-pale/40 font-mono mt-0.5">{u.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <BadgeRole papel={u.papel} />
              {!soLeitura && (
                <button
                  onClick={() => onDelete(u)}
                  disabled={deletando === u.id}
                  className="text-xs text-brand-pale/30 hover:text-red-400 transition-colors disabled:opacity-40 font-medium"
                >
                  {deletando === u.id ? "..." : "Desativar"}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
