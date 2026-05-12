import { useState, useEffect, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import {
  getCandidato,
  getCandidaturasPorCandidato,
  uploadCurriculo,
  getVagas,
  createCandidatura,
} from "../api"
import { Badge } from "../components/Badge"
import { ScoreBar } from "../components/ScoreBar"
import { CvPreview } from "../components/CvPreview"

const STATUS_COR = {
  novo: "gray", aguardando_processamento: "gray", processando_curriculo: "amber",
  triagem_pendente: "amber", aprovado_triagem: "green", reprovado_triagem: "red",
  entrevista_rh_agendada: "blue", entrevista_rh_realizada: "blue", reprovado_rh: "red",
  entrevista_tec_agendada: "blue", entrevista_tec_realizada: "blue", reprovado_tecnico: "red",
  decisao_pendente: "amber", contratado: "green", nao_aprovado: "red", banco_de_talentos: "purple",
}

function UploadMini({ candidaturaId, curriculo, onUpload }) {
  const ref = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [err, setErr] = useState(null)

  async function handleFile(file) {
    if (!file?.name?.toLowerCase().endsWith(".pdf")) { setErr("Apenas PDF"); return }
    setUploading(true); setErr(null)
    try {
      const r = await uploadCurriculo(candidaturaId, file)
      onUpload(r.data)
    } catch (e) {
      setErr(e.response?.data?.detail ?? "Erro no upload")
    } finally {
      setUploading(false)
    }
  }

  if (curriculo?.score_curriculo != null) {
    return (
      <div className="space-y-1.5">
        <ScoreBar score={curriculo.score_curriculo} label={`Score: ${curriculo.score_curriculo}`} />
        <button onClick={() => ref.current?.click()}
          className="text-xs text-brand-pale/35 hover:text-brand-sky transition-colors">
          Substituir PDF
        </button>
        <input ref={ref} type="file" accept=".pdf" className="hidden"
          onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
      </div>
    )
  }

  return (
    <div>
      <button
        onClick={() => !uploading && ref.current?.click()}
        disabled={uploading}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all disabled:opacity-50"
        style={{ background: "rgba(26,139,191,0.14)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
        {uploading
          ? <><span className="w-3 h-3 border-2 rounded-full animate-spin"
              style={{ borderColor: "var(--b-normal)", borderTopColor: "#4DC8E8" }} /> Enviando...</>
          : "↑ Enviar CV"}
      </button>
      <input ref={ref} type="file" accept=".pdf" className="hidden"
        onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
      {err && <p className="text-xs text-red-400 mt-1">{err}</p>}
    </div>
  )
}

export function CandidatoDetalhe({ usuario }) {
  const { id }                            = useParams()
  const [candidato, setCandidato]         = useState(null)
  const [candidaturas, setCandidaturas]   = useState([])
  const [vagas, setVagas]                 = useState([])
  const [loading, setLoading]             = useState(true)
  const [novaVagaId, setNovaVagaId]       = useState("")
  const [vinculando, setVinculando]       = useState(false)
  const [erroVinculo, setErroVinculo]     = useState(null)

  const podeGerenciar = usuario?.papel === "rh" || usuario?.papel === "admin"

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
    setVinculando(true); setErroVinculo(null)
    try {
      const r = await createCandidatura({ candidato_id: id, vaga_id: novaVagaId })
      setCandidaturas(prev => [...prev, r.data])
      setNovaVagaId("")
    } catch (err) {
      setErroVinculo(err.response?.data?.detail ?? "Erro ao vincular")
    } finally {
      setVinculando(false)
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
            <p className="text-sm text-brand-pale/45 font-mono mt-0.5">{candidato.email}</p>
            {candidato.telefone && (
              <p className="text-xs text-brand-pale/35 mt-0.5">{candidato.telefone}</p>
            )}
            {candidato.cidade && (
              <p className="text-xs text-brand-pale/30 mt-0.5">
                {candidato.cidade}{candidato.estado ? `, ${candidato.estado}` : ""}
              </p>
            )}
          </div>
          <Badge cor={candidato.origem === "externo" ? "blue" : "green"}>
            {candidato.origem}
          </Badge>
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
                  <div className="flex items-center gap-2">
                    <Badge cor={STATUS_COR[c.status] ?? "gray"}>
                      {c.status?.replace(/_/g, " ")}
                    </Badge>
                    <Link to={`/candidaturas/${c.id}/entrevistas`}
                      className="text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                      style={{ background: "rgba(26,139,191,0.12)",
                               border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
                      Ver detalhes →
                    </Link>
                  </div>
                </div>

                {/* Score curricular se já processado */}
                {c.curriculo?.score_curriculo != null && (
                  <div className="mt-3 pt-3" style={{ borderTop: "1px solid rgba(77,200,232,0.08)" }}>
                    <ScoreBar score={c.curriculo.score_curriculo}
                      label={`Score currículo: ${c.curriculo.score_curriculo}`} />
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
          {erroVinculo && <p className="text-xs text-red-400">{erroVinculo}</p>}
        </div>
      )}
    </div>
  )
}