import { useState, useEffect, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import {
  getCandidato,
  getCandidaturasPorCandidato,
  uploadCurriculo,
  uploadCurriculoTexto,
  getVagas,
  createCandidatura,
  deleteCandidatura,
  updateCandidato,
  alterarEmailCandidato,
} from "../api"
import { Badge } from "../components/Badge"
import { ScoreBar } from "../components/ScoreBar"
import { CvPreview } from "../components/CvPreview"
import { ExplicacaoScore } from "../components/ExplicacaoScore"
import { ToastContainer } from "../components/ToastContainer"
import { useToast, extrairErro } from "../hooks/useToast"

const STATUS_COR = {
  novo: "gray", aguardando_processamento: "gray", processando_curriculo: "amber",
  triagem_pendente: "amber", aprovado_triagem: "green", reprovado_triagem: "red",
  entrevista_rh_agendada: "blue", entrevista_rh_realizada: "blue", reprovado_rh: "red",
  entrevista_tec_agendada: "blue", entrevista_tec_realizada: "blue", reprovado_tecnico: "red",
  decisao_pendente: "amber", contratado: "green", nao_aprovado: "red", banco_de_talentos: "purple",
}

const LABEL_STATUS = {
  novo: "Novo", aguardando_processamento: "Processando", processando_curriculo: "Processando",
  triagem_pendente: "Triagem pendente", aprovado_triagem: "Ag. Entrevista RH",
  reprovado_triagem: "Reprovado triagem",
  entrevista_rh_agendada: "Entrevista RH", entrevista_rh_realizada: "Ag. Entrevista Téc.",
  reprovado_rh: "Reprovado RH",
  entrevista_tec_agendada: "Entrevista Téc.", entrevista_tec_realizada: "Ag. decisão",
  reprovado_tecnico: "Reprovado Téc.",
  decisao_pendente: "Decisão pendente", contratado: "Contratado",
  nao_aprovado: "Não aprovado", banco_de_talentos: "Banco de talentos",
}

function UploadMini({ candidaturaId, curriculo, onUpload }) {
  const ref                     = useRef(null)
  const [modo, setModo]         = useState("pdf")   // "pdf" | "texto"
  const [texto, setTexto]       = useState("")
  const [uploading, setUploading] = useState(false)
  const [err, setErr]           = useState(null)

  async function handleFile(file) {
    if (!file?.name?.toLowerCase().endsWith(".pdf")) { setErr("Apenas PDF"); return }
    setUploading(true); setErr(null)
    try {
      const r = await uploadCurriculo(candidaturaId, file)
      onUpload(r.data)
    } catch (e) {
      setErr(e.response?.data?.detail ?? "Erro no upload")
    } finally { setUploading(false) }
  }

  async function handleTexto() {
    if (!texto.trim()) return
    setUploading(true); setErr(null)
    try {
      const r = await uploadCurriculoTexto(candidaturaId, texto.trim())
      onUpload(r.data)
      setTexto("")
    } catch (e) {
      setErr(e.response?.data?.detail ?? "Erro ao enviar texto")
    } finally { setUploading(false) }
  }

  const jaProcessado = curriculo?.score_curriculo != null

  return (
    <div className="space-y-2">
      {jaProcessado && (
        <ScoreBar score={curriculo.score_curriculo} label={`Score: ${curriculo.score_curriculo}`} />
      )}

      {/* Toggle PDF / Texto */}
      <div className="flex items-center gap-1.5">
        {jaProcessado && (
          <span className="text-xs text-brand-pale/35 mr-1">Substituir:</span>
        )}
        {["pdf", "texto"].map(m => (
          <button key={m} type="button" onClick={() => { setModo(m); setErr(null) }}
            className="px-2.5 py-1 rounded-lg text-xs font-semibold transition-all"
            style={modo === m
              ? { background: "rgba(26,139,191,0.25)", color: "#4DC8E8", border: "1px solid rgba(26,139,191,0.4)" }
              : { background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}>
            {m === "pdf" ? "PDF" : "Texto"}
          </button>
        ))}
      </div>

      {modo === "pdf" ? (
        <div>
          <button onClick={() => !uploading && ref.current?.click()} disabled={uploading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all disabled:opacity-50"
            style={{ background: "rgba(26,139,191,0.14)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
            {uploading
              ? <><span className="w-3 h-3 border-2 rounded-full animate-spin"
                  style={{ borderColor: "var(--b-normal)", borderTopColor: "#4DC8E8" }} /> Enviando...</>
              : jaProcessado ? "↑ Trocar PDF" : "↑ Enviar PDF"}
          </button>
          <input ref={ref} type="file" accept=".pdf" className="hidden"
            onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
        </div>
      ) : (
        <div className="space-y-2">
          <textarea value={texto} onChange={e => setTexto(e.target.value)}
            rows={4} placeholder="Cole o currículo em texto livre..."
            className="w-full rounded-xl px-3 py-2 text-sm resize-y" />
          <button onClick={handleTexto} disabled={uploading || !texto.trim()}
            className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all disabled:opacity-50"
            style={{ background: "rgba(26,139,191,0.14)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
            {uploading ? "Enviando..." : "Enviar texto"}
          </button>
        </div>
      )}

      {err && <p className="text-xs text-red-400">{err}</p>}
    </div>
  )
}

export function CandidatoDetalhe({ usuario }) {
  const { id }                            = useParams()
  const [candidato, setCandidato]         = useState(null)
  const [candidaturas, setCandidaturas]   = useState([])
  const [vagas, setVagas]                 = useState([])
  const [loading, setLoading]             = useState(true)
  const [novaVagaId, setNovaVagaId]         = useState("")
  const [vinculando, setVinculando]         = useState(false)
  const [confirmDesvincular, setConfirm]    = useState(null)  // candidatura_id a confirmar
  const { toasts, mostrarToast }            = useToast()
  const [desvinculando, setDesvinculando]   = useState(false)
  const [expandidos, setExpandidos]       = useState(new Set())
  const [editando, setEditando]           = useState(false)
  const [formEdit, setFormEdit]           = useState({})
  const [formacoesEdit, setFormacoesEdit] = useState([])
  const [salvando, setSalvando]           = useState(false)
  const [erroEdit, setErroEdit]           = useState(null)

  const toggleExpandido = (id) => setExpandidos(prev => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })

  const podeGerenciar = usuario?.papel === "rh" || usuario?.papel === "admin"
  const isAdmin       = usuario?.papel === "admin"

  // ── Estado do modal de alteração de e-mail ──────────────────────────────
  const [modalEmail, setModalEmail]     = useState(false)
  const [novoEmail, setNovoEmail]       = useState("")
  const [salvandoEmail, setSalvandoEmail] = useState(false)
  const [erroEmail, setErroEmail]       = useState(null)

  async function handleAlterarEmail(e) {
    e.preventDefault()
    if (!novoEmail.trim()) return
    setSalvandoEmail(true); setErroEmail(null)
    try {
      const r = await alterarEmailCandidato(id, novoEmail.trim())
      setCandidato(r.data)
      setModalEmail(false)
      setNovoEmail("")
      mostrarToast("E-mail alterado com sucesso", "sucesso")
    } catch (err) {
      setErroEmail(err.response?.data?.detail ?? "Erro ao alterar e-mail")
    } finally {
      setSalvandoEmail(false)
    }
  }

  function abrirEdicao() {
    setFormEdit({
      nome: candidato.nome ?? "",
      telefone: candidato.telefone ?? "",
      cidade: candidato.cidade ?? "",
      estado: candidato.estado ?? "",
      linkedin_url: candidato.linkedin_url ?? "",
      portfolio_url: candidato.portfolio_url ?? "",
    })
    setFormacoesEdit((candidato.formacao ?? []).map(f => ({ ...f, ano_conclusao: f.ano_conclusao ?? "" })))
    setErroEdit(null)
    setEditando(true)
  }

  function addFormacaoEdit() {
    setFormacoesEdit(f => [...f, { curso: "", instituicao: "", nivel: "graduacao", status: "concluido", ano_conclusao: "" }])
  }
  function updateFormacaoEdit(i, key, val) {
    setFormacoesEdit(f => f.map((item, idx) => idx === i ? { ...item, [key]: val } : item))
  }
  function removeFormacaoEdit(i) {
    setFormacoesEdit(f => f.filter((_, idx) => idx !== i))
  }

  async function handleSalvarEdicao(e) {
    e.preventDefault()
    setSalvando(true); setErroEdit(null)
    try {
      const payload = {
        nome: formEdit.nome || undefined,
        telefone: formEdit.telefone || undefined,
        cidade: formEdit.cidade || undefined,
        estado: formEdit.estado || undefined,
        linkedin_url: formEdit.linkedin_url || null,
        portfolio_url: formEdit.portfolio_url || null,
        formacao: formacoesEdit
          .filter(f => f.curso.trim() && f.instituicao.trim())
          .map(f => ({ ...f, ano_conclusao: f.ano_conclusao ? parseInt(f.ano_conclusao) : null })),
      }
      const r = await updateCandidato(id, payload)
      setCandidato(r.data)
      setEditando(false)
    } catch (err) {
      setErroEdit(err.response?.data?.detail ?? "Erro ao salvar")
    } finally {
      setSalvando(false)
    }
  }

  useEffect(() => {
    Promise.all([
      getCandidato(id),
      getCandidaturasPorCandidato(id),
      getVagas(),
    ]).then(([rc, rcand, rv]) => {
      setCandidato(rc.data)
      setCandidaturas(rcand.data)
      setVagas(rv.data)
    }).finally(() => setLoading(false))
  }, [id])

  function onUpload(candidaturaAtualizada) {
    setCandidaturas(prev =>
      prev.map(c => c.id === candidaturaAtualizada.id ? candidaturaAtualizada : c)
    )
  }

  async function handleVincular(e) {
    e.preventDefault()
    if (!novaVagaId) return
    setVinculando(true)
    try {
      const r = await createCandidatura({ candidato_id: id, vaga_id: novaVagaId })
      setCandidaturas(prev => [...prev, r.data])
      setNovaVagaId("")
    } catch (err) {
      mostrarToast(extrairErro(err, "Erro ao vincular candidatura"), "erro")
    } finally {
      setVinculando(false)
    }
  }

  async function handleDesvincular() {
    if (!confirmDesvincular) return
    setDesvinculando(true)
    try {
      await deleteCandidatura(confirmDesvincular)
      setCandidaturas(prev => prev.filter(c => c.id !== confirmDesvincular))
      setConfirm(null)
    } catch (err) {
      alert(err.response?.data?.detail ?? "Erro ao desvincular")
    } finally {
      setDesvinculando(false)
    }
  }

  const vagasVinculadas = new Set(candidaturas.map(c => c.vaga_id))
  const vagasDisponiveis = vagas.filter(v => !vagasVinculadas.has(v.id) && v.status !== "fechada")

  if (loading) return (
    <div className="space-y-4">
      <div className="h-8 w-64 rounded-xl animate-pulse" style={{ background: "var(--s-skeleton)" }} />
      <div className="h-4 w-96 rounded animate-pulse" style={{ background: "rgba(14,80,104,0.2)" }} />
    </div>
  )

  if (!candidato) return (
    <div className="text-center py-20">
      <p className="text-brand-pale/45">Candidato não encontrado.</p>
      <Link to="/candidatos" className="text-sm text-brand-sky font-semibold mt-2 block">← Candidatos</Link>
    </div>
  )

  return (
    <div className="space-y-6">
      <Link to="/candidatos"
        className="inline-flex items-center gap-1.5 text-sm text-brand-pale/45 hover:text-brand-sky transition-colors font-semibold">
        ← Candidatos
      </Link>

      {/* Perfil */}
      <div className="card-glass rounded-2xl p-6">
        {!editando ? (
          <>
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0"
                style={{ background: candidato.origem === "externo"
                  ? "linear-gradient(135deg,#1A8BBF,#4DC8E8)"
                  : "linear-gradient(135deg,#1AAA80,#2EE8B4)" }}>
                <span className="text-xl font-bold text-brand-black">
                  {candidato.nome.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-xl font-bold text-brand-cloud">{candidato.nome}</h1>
                <div className="flex items-center gap-2 mt-0.5">
                  <p className="text-sm text-brand-pale/45 font-mono">{candidato.email}</p>
                  {isAdmin && (
                    <button
                      onClick={() => { setNovoEmail(candidato.email); setErroEmail(null); setModalEmail(true) }}
                      title="Alterar e-mail (admin)"
                      className="text-xs px-1.5 py-0.5 rounded-md transition-all"
                      style={{ background: "rgba(251,191,36,0.12)", border: "1px solid rgba(251,191,36,0.25)", color: "#fbbf24" }}
                    >
                      ✎
                    </button>
                  )}
                </div>
                {candidato.telefone && (
                  <p className="text-xs text-brand-pale/35 mt-0.5">{candidato.telefone}</p>
                )}
                {candidato.cidade && (
                  <p className="text-xs text-brand-pale/30 mt-0.5">
                    {candidato.cidade}{candidato.estado ? `, ${candidato.estado}` : ""}
                  </p>
                )}
                {(candidato.linkedin_url || candidato.portfolio_url) && (
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {candidato.linkedin_url && (
                      <a href={candidato.linkedin_url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all hover:opacity-80"
                        style={{ background: "rgba(10,102,194,0.18)", border: "1px solid rgba(10,102,194,0.35)", color: "#60a5fa" }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                        </svg>
                        LinkedIn
                      </a>
                    )}
                    {candidato.portfolio_url && (
                      <a href={candidato.portfolio_url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all hover:opacity-80"
                        style={{ background: "rgba(77,200,232,0.12)", border: "1px solid rgba(77,200,232,0.28)", color: "#4DC8E8" }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
                          <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
                        </svg>
                        Portfólio
                      </a>
                    )}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Badge cor={candidato.origem === "externo" ? "blue" : "green"}>
                  {candidato.origem}
                </Badge>
                {podeGerenciar && (
                  <button onClick={abrirEdicao}
                    className="text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                    style={{ background: "rgba(26,139,191,0.12)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
                    Editar
                  </button>
                )}
              </div>
            </div>

            {candidato.formacao?.length > 0 && (
              <div className="mt-4 pt-4" style={{ borderTop: "1px solid rgba(77,200,232,0.1)" }}>
                <p className="text-xs font-bold text-brand-pale/40 uppercase tracking-wider mb-3">Formação</p>
                <div className="space-y-1.5">
                  {candidato.formacao.map((f, i) => (
                    <div key={i} className="flex flex-wrap items-center gap-x-2 text-sm">
                      <span className="text-brand-pale/70 font-semibold">{f.curso}</span>
                      <span className="text-brand-pale/30">·</span>
                      <span className="text-brand-pale/45">{f.instituicao}</span>
                      {f.ano_conclusao && (
                        <span className="text-brand-pale/30 font-mono text-xs">· {f.ano_conclusao}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <form onSubmit={handleSalvarEdicao} className="space-y-4">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-bold text-brand-cloud">Editar candidato</h2>
              <button type="button" onClick={() => setEditando(false)}
                className="text-brand-pale/35 hover:text-brand-pale text-xl leading-none transition-colors">×</button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {[
                ["nome",     "Nome completo", "text"],
                ["telefone", "Telefone",       "text"],
                ["cidade",   "Cidade",         "text"],
                ["estado",   "Estado (UF)",    "text"],
              ].map(([key, label, type]) => (
                <div key={key}>
                  <label className="block text-xs font-bold text-brand-pale/55 uppercase tracking-wider mb-1.5">{label}</label>
                  <input type={type} value={formEdit[key] ?? ""} maxLength={key === "estado" ? 2 : undefined}
                    onChange={e => setFormEdit(f => ({ ...f, [key]: e.target.value }))}
                    className="w-full rounded-xl px-3 py-2.5 text-sm transition-all" />
                </div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-brand-pale/55 uppercase tracking-wider mb-1.5">LinkedIn</label>
                <input type="url" value={formEdit.linkedin_url ?? ""} placeholder="https://linkedin.com/in/..."
                  onChange={e => setFormEdit(f => ({ ...f, linkedin_url: e.target.value }))}
                  className="w-full rounded-xl px-3 py-2.5 text-sm transition-all" />
              </div>
              <div>
                <label className="block text-xs font-bold text-brand-pale/55 uppercase tracking-wider mb-1.5">Portfólio</label>
                <input type="url" value={formEdit.portfolio_url ?? ""} placeholder="https://..."
                  onChange={e => setFormEdit(f => ({ ...f, portfolio_url: e.target.value }))}
                  className="w-full rounded-xl px-3 py-2.5 text-sm transition-all" />
              </div>
            </div>

            {/* Formação */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-bold text-brand-pale/55 uppercase tracking-wider">Formação acadêmica</label>
                <button type="button" onClick={addFormacaoEdit}
                  className="text-xs font-bold px-2.5 py-1 rounded-lg transition-all"
                  style={{ background: "rgba(26,139,191,0.14)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
                  + Adicionar
                </button>
              </div>
              {formacoesEdit.length === 0 && (
                <p className="text-xs text-brand-pale/30 italic">Nenhuma formação.</p>
              )}
              <div className="space-y-2">
                {formacoesEdit.map((f, i) => (
                  <div key={i} className="rounded-xl p-3 space-y-2"
                    style={{ background: "rgba(14,80,104,0.18)", border: "1px solid rgba(77,200,232,0.1)" }}>
                    <div className="grid grid-cols-2 gap-2">
                      <input value={f.curso} onChange={e => updateFormacaoEdit(i, "curso", e.target.value)}
                        placeholder="Curso" className="w-full rounded-xl px-3 py-2 text-sm" />
                      <input value={f.instituicao} onChange={e => updateFormacaoEdit(i, "instituicao", e.target.value)}
                        placeholder="Instituição" className="w-full rounded-xl px-3 py-2 text-sm" />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <select value={f.nivel} onChange={e => updateFormacaoEdit(i, "nivel", e.target.value)}
                        className="w-full rounded-xl px-3 py-2 text-sm">
                        <option value="tecnico">Técnico</option>
                        <option value="graduacao">Graduação</option>
                        <option value="pos_graduacao">Pós-graduação</option>
                        <option value="mestrado">Mestrado</option>
                        <option value="doutorado">Doutorado</option>
                      </select>
                      <select value={f.status} onChange={e => updateFormacaoEdit(i, "status", e.target.value)}
                        className="w-full rounded-xl px-3 py-2 text-sm">
                        <option value="concluido">Concluído</option>
                        <option value="em_andamento">Em andamento</option>
                        <option value="trancado">Trancado</option>
                      </select>
                      <input value={f.ano_conclusao} onChange={e => updateFormacaoEdit(i, "ano_conclusao", e.target.value)}
                        placeholder="Ano" type="number" min="1950" max="2030"
                        className="w-full rounded-xl px-3 py-2 text-sm" />
                    </div>
                    <button type="button" onClick={() => removeFormacaoEdit(i)}
                      className="text-xs text-red-400/60 hover:text-red-400 transition-colors">Remover</button>
                  </div>
                ))}
              </div>
            </div>

            {erroEdit && <p className="text-xs text-red-400">{erroEdit}</p>}
            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={salvando}
                className="px-5 py-2.5 rounded-xl text-sm font-bold text-brand-black disabled:opacity-50"
                style={{ background: "linear-gradient(135deg,#1A8BBF,#4DC8E8)" }}>
                {salvando ? "Salvando..." : "Salvar"}
              </button>
              <button type="button" onClick={() => setEditando(false)}
                className="px-4 py-2 rounded-xl text-xs text-brand-pale/45 hover:text-brand-pale transition-colors">
                Cancelar
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Candidaturas */}
      <div>
        <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-3">
          Candidaturas ({candidaturas.length})
        </h2>

        {candidaturas.length === 0 ? (
          <div className="text-center py-10 rounded-2xl border-2 border-dashed"
            style={{ borderColor: "var(--b-card)" }}>
            <p className="text-sm text-brand-pale/40">Nenhuma candidatura ainda.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {candidaturas.map(c => (
              <div key={c.id} className="card-glass rounded-2xl p-4">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <p className="font-semibold text-brand-cloud text-sm">
                      {c.vaga?.nome ?? "Vaga"}
                    </p>
                    <p className="text-xs text-brand-pale/35 mt-0.5 font-mono">
                      {new Date(c.criado_em).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge cor={STATUS_COR[c.status] ?? "gray"}>
                      {LABEL_STATUS[c.status] ?? c.status?.replace(/_/g, " ")}
                    </Badge>
                    <Link to={`/candidaturas/${c.id}/entrevistas`}
                      className="text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                      style={{ background: "rgba(26,139,191,0.12)",
                               border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
                      Ver detalhes →
                    </Link>
                    {usuario?.papel === "admin" && (
                      <button
                        onClick={() => setConfirm(c.id)}
                        className="text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                        style={{ background: "rgba(252,165,165,0.08)", border: "1px solid rgba(252,165,165,0.2)", color: "#FCA5A5" }}>
                        Desvincular
                      </button>
                    )}
                  </div>
                </div>

                {/* Aviso de re-submissão via webhook */}
                {c.historico?.some(h => h.tipo === "resubmissao_duplicata") && (
                  <div className="mt-3 px-3 py-2 rounded-xl text-xs font-semibold"
                    style={{ background: "rgba(161,98,7,0.15)", color: "#fbbf24", border: "1px solid rgba(234,179,8,0.3)" }}>
                    ⚠ Re-submissão detectada via webhook — este candidato já tinha candidatura para esta vaga. Nenhuma alteração foi feita.
                  </div>
                )}

                {/* Score curricular se já processado */}
                {c.curriculo?.score_curriculo != null && (
                  <div className="mt-3 pt-3 space-y-2.5" style={{ borderTop: "1px solid rgba(77,200,232,0.08)" }}>
                    {c.curriculo.score_rh != null ? (
                      <>
                        <ScoreBar score={c.curriculo.score_rh}      label="Aderência aos requisitos da vaga" />
                        <ScoreBar score={c.curriculo.score_mercado}  label="Aderência ao mercado" />
                        <ExplicacaoScore
                          explicacao={c.curriculo.explicacao}
                          expandido={expandidos.has(c.id)}
                          onToggle={() => toggleExpandido(c.id)}
                        />
                      </>
                    ) : (
                      <ScoreBar score={c.curriculo.score_curriculo}
                        label={`Score currículo: ${c.curriculo.score_curriculo}`} />
                    )}
                  </div>
                )}

                {/* Preview do CV */}
                {(c.curriculo?.arquivo_pdf || c.curriculo?.texto_extraido) && (
                  <div className="mt-3 pt-3" style={{ borderTop: "1px solid rgba(77,200,232,0.08)" }}>
                    <CvPreview
                      candidaturaId={c.id}
                      temPdf={!!c.curriculo?.arquivo_pdf}
                      textoExtraido={c.curriculo?.texto_extraido}
                    />
                  </div>
                )}

                {/* Upload de CV para RH/Admin */}
                {podeGerenciar && (
                  <div className="mt-3 pt-3" style={{ borderTop: "1px solid rgba(77,200,232,0.08)" }}>
                    <UploadMini
                      candidaturaId={c.id}
                      curriculo={c.curriculo}
                      onUpload={onUpload}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Vincular a nova vaga */}
      {podeGerenciar && vagasDisponiveis.length > 0 && (
        <div className="card-glass rounded-2xl p-5 space-y-3">
          <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
            Vincular a outra vaga
          </h2>
          <form onSubmit={handleVincular} className="flex items-end gap-3 flex-wrap">
            <div className="flex-1 min-w-40">
              <select value={novaVagaId} onChange={e => setNovaVagaId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl text-sm">
                <option value="">Selecione uma vaga…</option>
                {vagasDisponiveis.map(v => (
                  <option key={v.id} value={v.id}>{v.nome}</option>
                ))}
              </select>
            </div>
            <button type="submit" disabled={!novaVagaId || vinculando}
              className="px-4 py-2 rounded-xl text-xs font-bold text-brand-black disabled:opacity-50"
              style={{ background: "linear-gradient(135deg,#1A8BBF,#4DC8E8)" }}>
              {vinculando ? "Vinculando…" : "Vincular"}
            </button>
          </form>
        </div>
      )}

      {/* Modal de confirmação de desvínculo */}
      {confirmDesvincular && (
        <div className="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(7,17,26,0.75)", backdropFilter: "blur(4px)" }}>
          <div className="card-glass rounded-2xl p-6 w-full max-w-sm space-y-4"
            style={{ border: "1px solid rgba(252,165,165,0.25)" }}>
            <h2 className="text-base font-bold text-red-300">Desvincular candidatura?</h2>
            <p className="text-sm text-brand-pale/60 leading-relaxed">
              Esta ação remove permanentemente o vínculo do candidato com a vaga,
              incluindo currículo processado e todas as entrevistas associadas.
              <br /><br />
              <span className="font-semibold text-brand-pale/80">Não pode ser desfeita.</span>
            </p>
            <div className="flex gap-3 pt-1">
              <button
                onClick={handleDesvincular}
                disabled={desvinculando}
                className="px-5 py-2.5 rounded-xl text-sm font-bold disabled:opacity-50 transition-all"
                style={{ background: "rgba(252,165,165,0.18)", border: "1px solid rgba(252,165,165,0.35)", color: "#FCA5A5" }}>
                {desvinculando ? "Removendo..." : "Sim, desvincular"}
              </button>
              <button
                onClick={() => setConfirm(null)}
                disabled={desvinculando}
                className="px-4 py-2 rounded-xl text-xs text-brand-pale/45 hover:text-brand-pale transition-colors">
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Modal de alteração de e-mail (apenas admin) */}
      {modalEmail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.55)" }}
          onClick={e => e.target === e.currentTarget && setModalEmail(false)}>
          <div className="rounded-2xl p-6 w-full max-w-sm shadow-2xl"
            style={{ background: "var(--s-card)", border: "1px solid var(--b-card)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-brand-cloud">Alterar e-mail do candidato</h3>
              <button onClick={() => setModalEmail(false)}
                className="text-brand-pale/35 hover:text-brand-pale text-xl leading-none transition-colors">×</button>
            </div>
            <p className="text-xs text-brand-pale/40 mb-4">
              Esta ação fica registrada na auditoria. O e-mail é usado como identificador único do candidato.
            </p>
            <form onSubmit={handleAlterarEmail} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1.5">
                  Novo e-mail
                </label>
                <input
                  type="email"
                  value={novoEmail}
                  onChange={e => setNovoEmail(e.target.value)}
                  required
                  autoFocus
                  className="w-full rounded-xl px-3 py-2.5 text-sm font-mono"
                  placeholder="novo@email.com"
                />
              </div>
              {erroEmail && (
                <p className="text-xs font-semibold rounded-lg px-3 py-2"
                  style={{ background: "rgba(239,68,68,0.12)", color: "#f87171" }}>
                  {erroEmail}
                </p>
              )}
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setModalEmail(false)}
                  className="flex-1 py-2 rounded-xl text-xs font-bold transition-all"
                  style={{ background: "var(--s-chip)", color: "var(--t-muted2)", border: "1px solid var(--b-subtle)" }}>
                  Cancelar
                </button>
                <button type="submit" disabled={salvandoEmail || !novoEmail.trim()}
                  className="flex-1 py-2 rounded-xl text-xs font-bold transition-all disabled:opacity-50"
                  style={{ background: "rgba(251,191,36,0.15)", border: "1px solid rgba(251,191,36,0.35)", color: "#fbbf24" }}>
                  {salvandoEmail ? "Salvando…" : "Confirmar alteração"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ToastContainer toasts={toasts} />
    </div>
  )
}