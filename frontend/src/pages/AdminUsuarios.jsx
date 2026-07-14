import { useState, useEffect } from "react"
import { getUsuarios, createUsuario, updateUsuario, deleteUsuario } from "../api"
import { IconSearch } from "../components/Icons"

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

// ── Modal criar ───────────────────────────────────────────────────────────────
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
    <Modal titulo="Novo usuário" onFechar={onFechar}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Campo label="Nome completo">
          <input value={form.nome} onChange={e => set("nome", e.target.value)}
            placeholder="Ex.: Ana Paula Ramos"
            className="w-full px-3 py-2.5 rounded-xl text-sm" />
        </Campo>
        <Campo label="Email">
          <input type="email" value={form.email} onChange={e => set("email", e.target.value)}
            placeholder="ana@empresa.com"
            className="w-full px-3 py-2.5 rounded-xl text-sm" />
        </Campo>
        <Campo label="Senha">
          <input type="password" value={form.senha} onChange={e => set("senha", e.target.value)}
            placeholder="Mínimo 6 caracteres"
            className="w-full px-3 py-2.5 rounded-xl text-sm" />
        </Campo>
        <SeletorPapel valor={form.papel} onChange={v => set("papel", v)} />

        {erro && <p className="text-xs text-red-400">{erro}</p>}

        <BotoesModal onCancelar={onFechar} salvando={salvando} label="Criar usuário" />
      </form>
    </Modal>
  )
}

// ── Modal editar ──────────────────────────────────────────────────────────────
function ModalEditarUsuario({ usuario, onSalvo, onFechar }) {
  const [form, setForm]     = useState({
    nome : usuario.nome,
    email: usuario.email,
    papel: usuario.papel,
    senha: "",
  })
  const [erro, setErro]     = useState(null)
  const [salvando, setSalv] = useState(false)

  function set(campo, valor) { setForm(f => ({ ...f, [campo]: valor })) }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.nome.trim() || !form.email.trim()) {
      setErro("Nome e e-mail são obrigatórios"); return
    }
    setSalv(true); setErro(null)
    try {
      const payload = {
        nome : form.nome,
        email: form.email,
        papel: form.papel,
        ...(form.senha.trim() ? { senha: form.senha } : {}),
      }
      const r = await updateUsuario(usuario.id, payload)
      onSalvo(r.data)
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro ao salvar")
    } finally {
      setSalv(false)
    }
  }

  return (
    <Modal titulo={`Editar — ${usuario.nome}`} onFechar={onFechar}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Campo label="Nome completo">
          <input value={form.nome} onChange={e => set("nome", e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl text-sm" />
        </Campo>
        <Campo label="Email">
          <input type="email" value={form.email} onChange={e => set("email", e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl text-sm" />
        </Campo>
        <Campo label="Nova senha" sub="Deixe em branco para manter a atual">
          <input type="password" value={form.senha} onChange={e => set("senha", e.target.value)}
            placeholder="••••••••"
            className="w-full px-3 py-2.5 rounded-xl text-sm" />
        </Campo>
        {/* Admin não pode mudar o próprio papel */}
        {usuario.papel !== "admin" && (
          <SeletorPapel valor={form.papel} onChange={v => set("papel", v)} />
        )}

        {erro && <p className="text-xs text-red-400">{erro}</p>}

        <BotoesModal onCancelar={onFechar} salvando={salvando} label="Salvar alterações" />
      </form>
    </Modal>
  )
}

// ── Componentes auxiliares ────────────────────────────────────────────────────
function Modal({ titulo, onFechar, children }) {
  return (
    <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(7,17,26,0.75)", backdropFilter: "blur(4px)" }}>
      <div className="card-glass rounded-2xl p-6 w-full max-w-md space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-brand-cloud">{titulo}</h2>
          <button onClick={onFechar}
            className="text-brand-pale/40 hover:text-brand-pale transition-colors text-xl leading-none">×</button>
        </div>
        {children}
      </div>
    </div>
  )
}

function Campo({ label, sub, children }) {
  return (
    <div>
      <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1">
        {label}
      </label>
      {sub && <p className="text-xs text-brand-pale/30 mb-1.5">{sub}</p>}
      {children}
    </div>
  )
}

function SeletorPapel({ valor, onChange }) {
  return (
    <Campo label="Papel">
      <div className="flex gap-2">
        {["rh", "gestor"].map(p => (
          <button key={p} type="button"
            onClick={() => onChange(p)}
            className="flex-1 py-2.5 rounded-xl text-xs font-bold transition-all"
            style={valor === p
              ? { background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)", color: "#07111A" }
              : { background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid rgba(77,200,232,0.15)" }}>
            {PAPEL_LABEL[p]}
          </button>
        ))}
      </div>
    </Campo>
  )
}

function BotoesModal({ onCancelar, salvando, label }) {
  return (
    <div className="flex gap-3 pt-1">
      <button type="button" onClick={onCancelar}
        className="flex-1 py-2.5 rounded-xl text-xs font-bold text-brand-pale/50 hover:text-brand-pale transition-colors"
        style={{ border: "1px solid rgba(77,200,232,0.15)" }}>
        Cancelar
      </button>
      <button type="submit" disabled={salvando}
        className="flex-1 py-2.5 rounded-xl text-xs font-bold text-brand-black disabled:opacity-50"
        style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
        {salvando ? "Salvando..." : label}
      </button>
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────
export function AdminUsuarios() {
  const [usuarios, setUsuarios]     = useState([])
  const [loading, setLoading]       = useState(true)
  const [modalNovo, setModalNovo]   = useState(false)
  const [editando, setEditando]     = useState(null)
  const [deletando, setDeletando]   = useState(null)
  const [erro, setErro]             = useState(null)
  const [busca, setBusca]           = useState("")

  useEffect(() => {
    getUsuarios()
      .then(r => setUsuarios(r.data))
      .finally(() => setLoading(false))
  }, [])

  async function handleDelete(u) {
    if (!confirm(`Desativar ${u.nome}? O usuário perderá acesso ao sistema.`)) return
    setDeletando(u.id); setErro(null)
    try {
      await deleteUsuario(u.id)
      setUsuarios(prev => prev.filter(x => x.id !== u.id))
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro ao desativar usuário")
    } finally {
      setDeletando(null)
    }
  }

  function onSalvoNovo(novo) {
    setUsuarios(prev => [...prev, novo])
    setModalNovo(false)
  }

  function onSalvoEdicao(atualizado) {
    setUsuarios(prev => prev.map(u => u.id === atualizado.id ? atualizado : u))
    setEditando(null)
  }

  const usuariosFiltrados = busca.trim()
    ? usuarios.filter(u => {
        const q = busca.toLowerCase()
        return u.nome.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
      })
    : usuarios

  const porPapel = papeis => usuariosFiltrados.filter(u => papeis.includes(u.papel))

  if (loading) return (
    <div className="space-y-4">
      {[1,2,3].map(i => (
        <div key={i} className="h-16 rounded-2xl animate-pulse" style={{ background: "var(--s-skeleton)" }} />
      ))}
    </div>
  )

  return (
    <div className="space-y-6">
      {modalNovo && <ModalNovoUsuario onSalvo={onSalvoNovo} onFechar={() => setModalNovo(false)} />}
      {editando  && <ModalEditarUsuario usuario={editando} onSalvo={onSalvoEdicao} onFechar={() => setEditando(null)} />}

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-brand-cloud">Gerenciar Usuários</h1>
          <p className="text-sm text-brand-pale/45 mt-0.5">
            {busca
              ? `${usuariosFiltrados.length} resultado${usuariosFiltrados.length !== 1 ? "s" : ""} para "${busca}"`
              : `${usuarios.length} ${usuarios.length === 1 ? "usuário ativo" : "usuários ativos"}`}
          </p>
        </div>
        <button onClick={() => setModalNovo(true)}
          className="px-4 py-2.5 rounded-xl text-sm font-bold text-brand-black flex-shrink-0"
          style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
          + Novo usuário
        </button>
      </div>

      {/* Busca */}
      <div className="relative">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 flex items-center text-brand-pale/35 pointer-events-none">
          <IconSearch size={15} />
        </span>
        <input
          value={busca}
          onChange={e => setBusca(e.target.value)}
          placeholder="Buscar por nome ou e-mail…"
          className="w-full rounded-xl pl-9 pr-9 py-2.5 text-sm transition-all"
        />
        {busca && (
          <button
            onClick={() => setBusca("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-pale/35 hover:text-brand-pale transition-colors text-lg leading-none">
            ×
          </button>
        )}
      </div>

      {erro && (
        <div className="px-4 py-3 rounded-xl text-sm text-red-400"
          style={{ background: "rgba(252,165,165,0.1)", border: "1px solid rgba(252,165,165,0.2)" }}>
          {erro}
        </div>
      )}

      {busca && usuariosFiltrados.length === 0 ? (
        <div className="text-center py-16 rounded-2xl border-2 border-dashed"
          style={{ borderColor: "var(--b-card)" }}>
          <p className="text-sm text-brand-pale/45 font-semibold">
            Nenhum usuário encontrado para "{busca}"
          </p>
          <button onClick={() => setBusca("")}
            className="mt-2 text-xs text-brand-sky hover:underline">
            Limpar busca
          </button>
        </div>
      ) : (
        <>
          <Secao titulo="RH" usuarios={porPapel(["rh"])}
            onEdit={setEditando} onDelete={handleDelete} deletando={deletando} />

          <Secao titulo="Gestores Técnicos" usuarios={porPapel(["gestor"])}
            onEdit={setEditando} onDelete={handleDelete} deletando={deletando} />

          <Secao titulo="Administradores" usuarios={porPapel(["admin"])}
            onEdit={setEditando} onDelete={handleDelete} deletando={deletando} soLeitura />
        </>
      )}
    </div>
  )
}

function Secao({ titulo, usuarios, onEdit, onDelete, deletando, soLeitura }) {
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
                <>
                  <button
                    onClick={() => onEdit(u)}
                    className="text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-all"
                    style={{ background: "rgba(26,139,191,0.12)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
                    Editar
                  </button>
                  <button
                    onClick={() => onDelete(u)}
                    disabled={deletando === u.id}
                    className="text-xs text-brand-pale/30 hover:text-red-400 transition-colors disabled:opacity-40 font-medium">
                    {deletando === u.id ? "..." : "Desativar"}
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
