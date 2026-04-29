import { useState, useEffect, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import {
  getCandidatura,
  getEntrevistas,
  agendarEntrevista,
  registrarResultado,
  atualizarStatusCandidatura,
  uploadCurriculo,
  getCurriculo,
  editarAnotacoes,
} from "../api"
import { Badge } from "../components/Badge"
import { ScoreBar } from "../components/ScoreBar"

const TIPO_LABEL = { rh: "Entrevista RH", tecnica: "Entrevista Técnica" }
const STATUS_COR = { agendada: "blue", realizada: "green", cancelada: "red" }

const STATUS_COR_CAND = {
  novo: "gray", aguardando_processamento: "gray", processando_curriculo: "amber",
  triagem_pendente: "amber", aprovado_triagem: "green", reprovado_triagem: "red",
  entrevista_rh_agendada: "blue", entrevista_rh_realizada: "blue", reprovado_rh: "red",
  entrevista_tec_agendada: "blue", entrevista_tec_realizada: "blue", reprovado_tecnico: "red",
  decisao_pendente: "amber", contratado: "green", nao_aprovado: "red", banco_de_talentos: "purple",
}

const PROCESSANDO = new Set(["aguardando_processamento", "processando_curriculo"])

// ── Tag input ────────────────────────────────────────────────────────────────
function TagInput({ tags, onChange, placeholder }) {
  const [input, setInput] = useState("")
  function add() {
    const v = input.trim()
    if (v && !tags.includes(v)) onChange([...tags, v])
    setInput("")
  }
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add() } }}
          placeholder={placeholder}
          className="flex-1 px-3 py-2 rounded-xl text-sm"
        />
        <button type="button" onClick={add}
          className="px-3 py-2 rounded-xl text-xs font-bold text-brand-black"
          style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>+
        </button>
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map(t => (
            <span key={t} className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold"
              style={{ background: "rgba(26,139,191,0.18)", color: "#4DC8E8" }}>
              {t}
              <button type="button" onClick={() => onChange(tags.filter(x => x !== t))}
                className="opacity-60 hover:opacity-100 ml-0.5">×</button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Botão + modal visualizar conteúdo do currículo ───────────────────────────
function VerCurriculoBtn({ candidaturaId }) {
  const [aberto, setAberto]   = useState(false)
  const [texto, setTexto]     = useState(null)
  const [loading, setLoading] = useState(false)

  async function abrir() {
    setAberto(true)
    if (texto !== null) return
    setLoading(true)
    try {
      const r = await getCurriculo(candidaturaId)
      setTexto(r.data.texto_extraido ?? "(Texto não disponível)")
    } catch {
      setTexto("Erro ao carregar o conteúdo do currículo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button onClick={abrir}
        className="text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
        style={{ background: "rgba(26,139,191,0.14)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
        Ver currículo
      </button>

      {aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(7,17,26,0.8)", backdropFilter: "blur(4px)" }}>
          <div className="card-glass rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-5 border-b"
              style={{ borderColor: "var(--b-subtle)" }}>
              <h3 className="text-sm font-bold text-brand-cloud">Conteúdo extraído do currículo</h3>
              <button onClick={() => setAberto(false)}
                className="text-brand-pale/40 hover:text-brand-pale text-xl leading-none">×</button>
            </div>
            <div className="flex-1 overflow-auto p-5">
              {loading ? (
                <div className="flex items-center gap-2 text-brand-pale/45 text-sm">
                  <span className="w-4 h-4 border-2 rounded-full animate-spin"
                    style={{ borderColor: "var(--b-normal)", borderTopColor: "#4DC8E8" }} />
                  Carregando...
                </div>
              ) : (
                <pre className="text-xs text-brand-pale/70 leading-relaxed whitespace-pre-wrap font-mono">
                  {texto}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}


// ── Seção upload currículo ───────────────────────────────────────────────────
function UploadCurriculo({ candidaturaId, status, curriculo, podeUpload, onAtualizado }) {
  const [enviando, setEnviando]   = useState(false)
  const [erro, setErro]           = useState(null)
  const [arquivo, setArquivo]     = useState(null)
  const [drag, setDrag]           = useState(false)
  const inputRef                  = useRef(null)

  const jaProcessado  = curriculo?.score_curriculo != null
  // processando: status em fila OU texto já chegou mas score ainda não foi calculado
  const processando   = PROCESSANDO.has(status) ||
    (curriculo?.texto_extraido != null && curriculo?.score_curriculo == null)

  async function enviar(file) {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      setErro("Selecione um arquivo PDF"); return
    }
    setArquivo(file)
    setEnviando(true)
    setErro(null)
    try {
      const r = await uploadCurriculo(candidaturaId, file)
      onAtualizado(r.data)
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro no upload")
    } finally {
      setEnviando(false)
    }
  }

  function onDrop(e) {
    e.preventDefault(); setDrag(false)
    const f = e.dataTransfer.files[0]
    if (f) enviar(f)
  }

  if (processando) return (
    <div className="card-glass rounded-2xl p-6">
      <div className="flex items-center gap-3">
        <span className="w-5 h-5 border-2 rounded-full animate-spin flex-shrink-0"
          style={{ borderColor: "var(--b-normal)", borderTopColor: "#4DC8E8" }} />
        <div>
          <p className="text-sm font-bold text-brand-cloud">Processando currículo...</p>
          <p className="text-xs text-brand-pale/45 mt-0.5">A IA está extraindo texto e calculando scores. Aguarde.</p>
        </div>
      </div>
    </div>
  )

  if (jaProcessado) return (
    <div className="card-glass rounded-2xl p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">Currículo</h2>
        <span className="text-xs px-2.5 py-1 rounded-lg font-semibold"
          style={{ background: "rgba(26,170,128,0.18)", color: "#2EE8B4" }}>✓ Processado</span>
      </div>
      <ScoreBar score={curriculo.score_rh}       label="Aderência aos requisitos da vaga" />
      <ScoreBar score={curriculo.score_mercado}  label="Aderência ao mercado" />
      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-brand-pale/40">Score currículo</span>
        <span className="text-xl font-bold font-mono"
          style={{ color: curriculo.score_curriculo >= 70 ? "#2EE8B4" : curriculo.score_curriculo >= 50 ? "#FCD34D" : "#FCA5A5" }}>
          {curriculo.score_curriculo}
        </span>
      </div>
      {curriculo.processado_em && (
        <p className="text-xs text-brand-pale/30 font-mono">
          Processado em {new Date(curriculo.processado_em).toLocaleString("pt-BR")}
        </p>
      )}
      <div className="flex items-center gap-3 pt-1">
        <VerCurriculoBtn candidaturaId={candidaturaId} />
        {podeUpload && (
          <>
            <button onClick={() => inputRef.current?.click()}
              className="text-xs text-brand-pale/35 hover:text-brand-sky transition-colors">
              Substituir PDF ↑
            </button>
            <input ref={inputRef} type="file" accept=".pdf" className="hidden"
              onChange={e => e.target.files[0] && enviar(e.target.files[0])} />
          </>
        )}
      </div>
    </div>
  )

  // Sem currículo e sem permissão de upload → não mostrar nada
  if (!podeUpload) return null

  return (
    <div className="card-glass rounded-2xl p-5 space-y-3">
      <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">Enviar Currículo (PDF)</h2>

      <div
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => !enviando && inputRef.current?.click()}
        className="rounded-2xl p-8 text-center cursor-pointer transition-all"
        style={{
          border: `2px dashed ${drag ? "rgba(77,200,232,0.6)" : "var(--b-strong)"}`,
          background: drag ? "rgba(26,139,191,0.08)" : "var(--s-content)",
        }}
      >
        {enviando ? (
          <div className="flex flex-col items-center gap-2">
            <span className="w-8 h-8 border-2 rounded-full animate-spin"
              style={{ borderColor: "var(--b-normal)", borderTopColor: "#4DC8E8" }} />
            <p className="text-sm text-brand-pale/60">Enviando {arquivo?.name}...</p>
          </div>
        ) : (
          <>
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-3"
              style={{ background: "rgba(26,139,191,0.14)" }}>
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"
                style={{ color: "#4DC8E8" }}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-brand-pale/70">
              Arraste o PDF aqui ou <span style={{ color: "#4DC8E8" }}>clique para selecionar</span>
            </p>
            <p className="text-xs text-brand-pale/35 mt-1">Somente arquivos .pdf</p>
          </>
        )}
      </div>

      <input ref={inputRef} type="file" accept=".pdf" className="hidden"
        onChange={e => e.target.files[0] && enviar(e.target.files[0])} />

      {erro && <p className="text-xs text-red-400">{erro}</p>}
    </div>
  )
}

// ── Card entrevista ──────────────────────────────────────────────────────────
function CardEntrevista({ entrevista: initial, usuario, candidatura, onResultadoSalvo }) {
  const [entrevista, setEntrevista] = useState(initial)
  const [open, setOpen]             = useState(false)
  const [score, setScore]           = useState(entrevista.score_manual ?? "")
  const [anotacoes, setAnotacoes]   = useState(entrevista.anotacoes ?? "")
  const [fortes, setFortes]         = useState(entrevista.pontos_fortes ?? [])
  const [fracos, setFracos]         = useState(entrevista.pontos_fracos ?? [])
  const [salvando, setSalvando]     = useState(false)
  const [erro, setErro]             = useState(null)

  const vaga        = candidatura?.vaga
  const gestoresIds = vaga?.gestores_ids ?? []
  const ehGestorDaVaga = gestoresIds.includes(usuario?.id) || gestoresIds.includes(String(usuario?.id))

  // Pode registrar pela primeira vez (status = agendada)
  const podeRegistrar = entrevista.status === "agendada" && (
    usuario?.papel === "admin" ||
    (entrevista.tipo === "rh"      && usuario?.papel === "rh") ||
    (entrevista.tipo === "tecnica" && usuario?.papel === "gestor")
  )

  // Pode editar resultado completo (status = realizada)
  const podeEditarResultado = entrevista.status === "realizada" && (
    usuario?.papel === "admin" ||
    (entrevista.tipo === "rh"      && usuario?.papel === "rh") ||
    (entrevista.tipo === "tecnica" && usuario?.papel === "gestor" && ehGestorDaVaga)
  )

  function abrirFormEdicao() {
    setScore(entrevista.score_manual ?? "")
    setAnotacoes(entrevista.anotacoes ?? "")
    setFortes(entrevista.pontos_fortes ?? [])
    setFracos(entrevista.pontos_fracos ?? [])
    setErro(null)
    setOpen(true)
  }

  async function handleSalvar(e) {
    e.preventDefault()
    const s = parseFloat(score)
    if (isNaN(s) || s < 0 || s > 10) { setErro("Score deve ser entre 0 e 10"); return }
    if (!anotacoes.trim())            { setErro("Anotações são obrigatórias"); return }
    setSalvando(true); setErro(null)
    try {
      const r = await registrarResultado(entrevista.id, {
        score_manual : s,
        anotacoes,
        pontos_fortes: fortes,
        pontos_fracos: fracos,
      })
      setEntrevista(r.data)
      onResultadoSalvo(r.data)
      setOpen(false)
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro ao salvar resultado")
    } finally {
      setSalvando(false)
    }
  }

  const dtAgendada  = entrevista.agendada_para
    ? new Date(entrevista.agendada_para).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : null
  const dtRealizada = entrevista.realizada_em
    ? new Date(entrevista.realizada_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : null

  return (
    <div className="card-glass rounded-2xl p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-bold text-brand-cloud text-sm">{TIPO_LABEL[entrevista.tipo]}</p>
          {dtAgendada  && <p className="text-xs text-brand-pale/45 mt-0.5">Agendada: {dtAgendada}</p>}
          {dtRealizada && <p className="text-xs text-brand-mint/70 mt-0.5">Realizada: {dtRealizada}</p>}
        </div>
        <Badge cor={STATUS_COR[entrevista.status] ?? "gray"}>{entrevista.status}</Badge>
      </div>

      {entrevista.status === "realizada" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex-1 min-w-0">
              <ScoreBar score={(entrevista.score_manual ?? 0) * 10}
                label={`Score: ${entrevista.score_manual}/10`} />
            </div>
            {podeEditarResultado && !open && (
              <button onClick={abrirFormEdicao}
                className="flex-shrink-0 text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                style={{ background: "rgba(26,139,191,0.12)", border: "1px solid rgba(26,139,191,0.25)", color: "#4DC8E8" }}>
                Editar resultado
              </button>
            )}
          </div>

          {/* Anotações (somente leitura quando form fechado) */}
          <div>
            <p className="text-xs font-bold text-brand-pale/40 uppercase tracking-wider mb-1.5">Anotações</p>
            {!open && (
              entrevista.anotacoes ? (
                <div className="rounded-xl p-4 text-sm text-brand-pale/80 leading-relaxed whitespace-pre-wrap"
                  style={{ background: "var(--s-track)", border: "1px solid var(--b-subtle)" }}>
                  {entrevista.anotacoes}
                </div>
              ) : (
                <p className="text-xs text-brand-pale/35 italic">Sem anotações.</p>
              )
            )}

            {/* Histórico de edições */}
            {entrevista.historico_edicoes?.length > 0 && (
              <details className="mt-2">
                <summary className="text-xs text-brand-pale/30 cursor-pointer hover:text-brand-pale/50">
                  {entrevista.historico_edicoes.length} edição(ões) anterior(es)
                </summary>
                <div className="mt-2 space-y-2 pl-3 border-l"
                  style={{ borderColor: "var(--b-normal)" }}>
                  {[...entrevista.historico_edicoes].reverse().map((h, i) => (
                    <div key={i}>
                      <p className="text-xs text-brand-pale/30">
                        Alterado por <span className="text-brand-pale/50 font-semibold">{h.editado_por}</span>
                        {" · "}{new Date(h.editado_em).toLocaleString("pt-BR")}
                      </p>
                      <p className="text-xs text-brand-pale/45 mt-0.5 italic whitespace-pre-wrap line-clamp-3">
                        {h.texto_anterior || "(em branco)"}
                      </p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>

          {(entrevista.pontos_fortes?.length > 0 || entrevista.pontos_fracos?.length > 0) && (
            <div className="grid grid-cols-2 gap-3">
              {entrevista.pontos_fortes?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-brand-mint/70 uppercase tracking-wider mb-2">Pontos fortes</p>
                  <div className="flex flex-wrap gap-1.5">
                    {entrevista.pontos_fortes.map(t => (
                      <span key={t} className="px-2.5 py-1 rounded-lg text-xs font-semibold"
                        style={{ background: "rgba(26,170,128,0.18)", color: "#2EE8B4" }}>{t}</span>
                    ))}
                  </div>
                </div>
              )}
              {entrevista.pontos_fracos?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-red-400/70 uppercase tracking-wider mb-2">Pontos fracos</p>
                  <div className="flex flex-wrap gap-1.5">
                    {entrevista.pontos_fracos.map(t => (
                      <span key={t} className="px-2.5 py-1 rounded-lg text-xs font-semibold"
                        style={{ background: "rgba(252,165,165,0.15)", color: "#FCA5A5" }}>{t}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Botão "Registrar resultado" — somente para entrevistas agendadas */}
      {podeRegistrar && !open && (
        <button onClick={() => { setErro(null); setOpen(true) }}
          className="text-xs font-bold px-4 py-2 rounded-xl transition-all"
          style={{ background: "rgba(26,139,191,0.14)", border: "1px solid rgba(26,139,191,0.3)", color: "#4DC8E8" }}>
          Registrar resultado
        </button>
      )}

      {/* Form unificado — aparece para registro (agendada) e edição (realizada) */}
      {open && (
        <form onSubmit={handleSalvar}
          className="space-y-4 pt-4"
          style={{ borderTop: "1px solid var(--b-subtle)" }}>
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
              {entrevista.status === "realizada" ? "Editar resultado" : "Registrar resultado"}
            </p>
            <button type="button" onClick={() => setOpen(false)}
              className="text-brand-pale/35 hover:text-brand-pale transition-colors text-lg leading-none">×</button>
          </div>
          <div>
            <label className="block text-xs font-bold text-brand-pale/55 uppercase tracking-wider mb-2">
              Score (0–10)
            </label>
            <input type="number" min="0" max="10" step="0.1" value={score}
              onChange={e => setScore(e.target.value)}
              className="w-32 px-3 py-2 rounded-xl text-sm font-mono" required />
          </div>
          <div>
            <label className="block text-xs font-bold text-brand-pale/55 uppercase tracking-wider mb-2">
              Anotações
            </label>
            <textarea value={anotacoes} onChange={e => setAnotacoes(e.target.value)}
              rows={5} placeholder="Observações sobre o candidato..."
              className="w-full px-3 py-2 rounded-xl text-sm resize-y" required />
          </div>
          <div>
            <label className="block text-xs font-bold text-brand-mint/60 uppercase tracking-wider mb-2">
              Pontos fortes
            </label>
            <TagInput tags={fortes} onChange={setFortes}
              placeholder="ex: comunicação clara (Enter)" />
          </div>
          <div>
            <label className="block text-xs font-bold text-red-400/60 uppercase tracking-wider mb-2">
              Pontos fracos
            </label>
            <TagInput tags={fracos} onChange={setFracos}
              placeholder="ex: pouca experiência com Docker (Enter)" />
          </div>
          {erro && <p className="text-xs text-red-400">{erro}</p>}
          <div className="flex gap-3">
            <button type="submit" disabled={salvando}
              className="px-5 py-2.5 rounded-xl text-sm font-bold text-brand-black disabled:opacity-50"
              style={{ background: "linear-gradient(135deg, #1AAA80, #2EE8B4)" }}>
              {salvando ? "Salvando..." : "Salvar"}
            </button>
            <button type="button" onClick={() => setOpen(false)}
              className="px-4 py-2 rounded-xl text-xs text-brand-pale/45 hover:text-brand-pale transition-colors">
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

// ── Form agendar ─────────────────────────────────────────────────────────────
function FormAgendar({ candidaturaId, tipo, usuario, candidatura, onAgendado }) {
  const vaga            = candidatura?.vaga
  const gestoresIds     = vaga?.gestores_ids ?? []
  const rhsAutorizados  = vaga?.rhs_autorizados ?? []
  const ehGestorDaVaga  = gestoresIds.includes(String(usuario?.id))
  const ehRhAutorizado  = usuario?.papel === "admin" ||
    (usuario?.papel === "rh" && (rhsAutorizados.length === 0 || rhsAutorizados.includes(String(usuario?.id))))
  const podeAgendar     = ehRhAutorizado || (tipo === "tecnica" && usuario?.papel === "gestor" && ehGestorDaVaga)

  const [dt, setDt]       = useState("")
  const [ag, setAg]       = useState(false)
  const [erro, setErro]   = useState(null)

  if (!podeAgendar) return null

  async function handleAgendar(e) {
    e.preventDefault(); setAg(true); setErro(null)
    try {
      const r = await agendarEntrevista({
        candidatura_id : candidaturaId,
        tipo,
        agendada_para  : new Date(dt).toISOString(),
      })
      onAgendado(r.data)
      setDt("")
    } catch (err) {
      setErro(err.response?.data?.detail ?? "Erro ao agendar")
    } finally {
      setAg(false)
    }
  }

  return (
    <form onSubmit={handleAgendar} className="flex items-end gap-3 flex-wrap">
      <div>
        <label className="block text-xs font-bold text-brand-pale/45 uppercase tracking-wider mb-1">
          Data e hora
        </label>
        <input type="datetime-local" value={dt} onChange={e => setDt(e.target.value)}
          className="px-3 py-2 rounded-xl text-sm" required />
      </div>
      <button type="submit" disabled={ag}
        className="px-4 py-2 rounded-xl text-xs font-bold text-brand-black disabled:opacity-50"
        style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
        {ag ? "Agendando..." : `Agendar ${TIPO_LABEL[tipo]}`}
      </button>
      {erro && <p className="text-xs text-red-400 w-full">{erro}</p>}
    </form>
  )
}

// ── Página principal ─────────────────────────────────────────────────────────
export function EntrevistaDetalhe({ usuario }) {
  const { candidaturaId }             = useParams()
  const [candidatura, setCandidatura] = useState(null)
  const [entrevistas, setEntrevistas] = useState([])
  const [loading, setLoading]         = useState(true)
  const [decisaoErr, setDecisaoErr]   = useState(null)
  const pollingRef                    = useRef(null)

  async function carregar() {
    const [rc, re] = await Promise.all([
      getCandidatura(candidaturaId),
      getEntrevistas(candidaturaId),
    ])
    setCandidatura(rc.data)
    setEntrevistas(re.data)
    return rc.data
  }

  useEffect(() => {
    carregar().finally(() => setLoading(false))
  }, [candidaturaId])

  // Polling automático enquanto status é "processando"
  useEffect(() => {
    if (!candidatura) return
    if (PROCESSANDO.has(candidatura.status)) {
      pollingRef.current = setInterval(() => {
        getCandidatura(candidaturaId).then(r => {
          setCandidatura(r.data)
          if (!PROCESSANDO.has(r.data.status)) {
            clearInterval(pollingRef.current)
          }
        })
      }, 3000)
    } else {
      clearInterval(pollingRef.current)
    }
    return () => clearInterval(pollingRef.current)
  }, [candidatura?.status])

  function onAgendado(nova) {
    setEntrevistas(prev => [...prev, nova])
    setCandidatura(prev => ({
      ...prev,
      status: nova.tipo === "rh" ? "entrevista_rh_agendada" : "entrevista_tec_agendada",
    }))
  }

  function onResultadoSalvo(atualizada) {
    setEntrevistas(prev => prev.map(e => e.id === atualizada.id ? atualizada : e))
    setCandidatura(prev => ({
      ...prev,
      status: atualizada.tipo === "rh" ? "entrevista_rh_realizada" : "entrevista_tec_realizada",
    }))
  }

  async function tomarDecisao(novoStatus) {
    setDecisaoErr(null)
    try {
      const r = await atualizarStatusCandidatura(candidaturaId, novoStatus, usuario?.nome ?? "rh")
      setCandidatura(r.data)
    } catch (err) {
      setDecisaoErr(err.response?.data?.detail ?? "Erro ao atualizar status")
    }
  }

  if (loading) return (
    <div className="space-y-4">
      <div className="h-8 w-64 rounded-xl animate-pulse" style={{ background: "var(--s-skeleton)" }} />
      <div className="h-4 w-96 rounded animate-pulse" style={{ background: "rgba(14,80,104,0.2)" }} />
    </div>
  )

  if (!candidatura) return (
    <div className="text-center py-20">
      <p className="text-brand-pale/45">Candidatura não encontrada.</p>
      <Link to="/" className="text-sm text-brand-sky font-semibold mt-2 block">← Voltar</Link>
    </div>
  )

  const cand       = candidatura.candidato
  const vaga       = candidatura.vaga
  const status     = candidatura.status
  const curriculo  = candidatura.curriculo

  const rhFeita    = entrevistas.find(e => e.tipo === "rh"      && e.status === "realizada")
  const tecFeita   = entrevistas.find(e => e.tipo === "tecnica" && e.status === "realizada")
  const rhAgendada = entrevistas.find(e => e.tipo === "rh"      && e.status === "agendada")
  const tecAgendada= entrevistas.find(e => e.tipo === "tecnica" && e.status === "agendada")

  const vagaRhsAutorizados = vaga?.rhs_autorizados ?? []
  const vagaGestoresIds    = vaga?.gestores_ids ?? []
  const ehRhAutorizado     = usuario?.papel === "admin" ||
    (usuario?.papel === "rh" && (vagaRhsAutorizados.length === 0 || vagaRhsAutorizados.includes(String(usuario?.id))))
  const ehGestorDaVaga     = vagaGestoresIds.includes(String(usuario?.id))

  const podeAgendarRH  = !rhFeita && !rhAgendada && status === "aprovado_triagem" && ehRhAutorizado
  const podeAgendarTec = rhFeita && !tecFeita && !tecAgendada && status === "entrevista_rh_realizada" &&
    (ehRhAutorizado || (usuario?.papel === "gestor" && ehGestorDaVaga))
  // RH pode reprovar após entrevista de RH realizada (antes de agendar técnica)
  const podeReprovarRH = rhFeita && !tecAgendada && !tecFeita &&
    status === "entrevista_rh_realizada" && ehRhAutorizado
  // Gestor também pode tomar a decisão final nas suas vagas
  const podeDecisao    = status === "decisao_pendente" &&
    (ehRhAutorizado || (usuario?.papel === "gestor" && ehGestorDaVaga))

  const podeUpload         = ehRhAutorizado
  const podeMostrarCurriculo = podeUpload || curriculo != null

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Link to={vaga ? `/vagas/${candidatura.vaga_id}` : "/"}
        className="inline-flex items-center gap-1.5 text-sm text-brand-pale/45 hover:text-brand-sky transition-colors font-semibold">
        ← {vaga?.nome ?? "Voltar"}
      </Link>

      {/* Header candidato */}
      <div className="card-glass rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold text-brand-cloud">{cand?.nome ?? "Candidato"}</h1>
            <p className="text-sm text-brand-pale/45 mt-0.5 font-mono">{cand?.email}</p>
            {cand?.telefone && <p className="text-xs text-brand-pale/35 mt-0.5">{cand.telefone}</p>}
            {cand?.cidade && (
              <p className="text-xs text-brand-pale/30 mt-0.5">
                {cand.cidade}{cand.estado ? `, ${cand.estado}` : ""}
              </p>
            )}
          </div>
          <div className="text-right space-y-1">
            <Badge cor={STATUS_COR_CAND[status] ?? "gray"}>
              {status?.replace(/_/g, " ")}
            </Badge>
            {vaga && <p className="text-xs text-brand-pale/35 mt-1">{vaga.nome}</p>}
          </div>
        </div>

        {/* Formação */}
        {cand?.formacao?.length > 0 && (
          <div className="mt-4 pt-4" style={{ borderTop: "1px solid rgba(77,200,232,0.1)" }}>
            <p className="text-xs font-bold text-brand-pale/40 uppercase tracking-wider mb-3">Formação</p>
            <div className="space-y-1.5">
              {cand.formacao.map((f, i) => (
                <div key={i} className="flex items-center flex-wrap gap-x-2 text-sm">
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

      {/* Currículo — scores e upload para RH autorizado; só leitura para gestor */}
      {podeMostrarCurriculo && (
        <UploadCurriculo
          candidaturaId={candidaturaId}
          status={status}
          curriculo={curriculo}
          podeUpload={podeUpload}
          onAtualizado={c => setCandidatura(c)}
        />
      )}

      {/* Entrevistas existentes */}
      {entrevistas.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">Entrevistas</h2>
          {entrevistas.map(e => (
            <CardEntrevista key={e.id} entrevista={e} usuario={usuario}
              candidatura={candidatura}
              onResultadoSalvo={onResultadoSalvo} />
          ))}
        </div>
      )}

      {/* Agendar entrevista RH */}
      {podeAgendarRH && (
        <div className="card-glass rounded-2xl p-5 space-y-3">
          <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
            Agendar Entrevista RH
          </h2>
          <FormAgendar candidaturaId={candidaturaId} tipo="rh" usuario={usuario}
            candidatura={candidatura} onAgendado={onAgendado} />
        </div>
      )}

      {/* Decisão pós entrevista RH: agendar técnica ou reprovar */}
      {(podeAgendarTec || podeReprovarRH) && (
        <div className="card-glass rounded-2xl p-5 space-y-4">
          <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
            Decisão pós Entrevista RH
          </h2>
          {podeAgendarTec && (
            <div className="space-y-2">
              <p className="text-xs text-brand-pale/40">Aprovado — agendar entrevista técnica:</p>
              <FormAgendar candidaturaId={candidaturaId} tipo="tecnica" usuario={usuario}
                candidatura={candidatura} onAgendado={onAgendado} />
            </div>
          )}
          {podeReprovarRH && (
            <div className="flex items-center gap-4 pt-1"
              style={{ borderTop: podeAgendarTec ? "1px solid var(--b-subtle)" : "none" }}>
              {podeAgendarTec && <span className="text-xs text-brand-pale/30 flex-shrink-0">ou</span>}
              <button onClick={() => tomarDecisao("reprovado_rh")}
                className="px-4 py-2 rounded-xl text-sm font-bold"
                style={{ background: "rgba(252,165,165,0.12)", border: "1px solid rgba(252,165,165,0.25)", color: "#FCA5A5" }}>
                Reprovar entrevista RH
              </button>
            </div>
          )}
          {decisaoErr && <p className="text-xs text-red-400">{decisaoErr}</p>}
        </div>
      )}

      {/* Scores consolidados */}
      {(rhFeita || tecFeita) && (
        <div className="card-glass rounded-2xl p-5 space-y-3">
          <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">
            Scores das Entrevistas
          </h2>
          {rhFeita  && <ScoreBar score={(rhFeita.score_manual  ?? 0) * 10}
            label={`Entrevista RH: ${rhFeita.score_manual}/10`} />}
          {tecFeita && <ScoreBar score={(tecFeita.score_manual ?? 0) * 10}
            label={`Entrevista Técnica: ${tecFeita.score_manual}/10`} />}
        </div>
      )}

      {/* Decisão final — RH autorizado ou Gestor da vaga */}
      {podeDecisao && (
        <div className="card-glass rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-brand-pale/45 uppercase tracking-wider">Decisão Final</h2>
            <span className="text-xs text-brand-pale/30">
              {usuario?.papel === "gestor" ? "como gestor técnico" : "como analista de RH"}
            </span>
          </div>
          <div className="flex flex-wrap gap-3">
            <button onClick={() => tomarDecisao("contratado")}
              className="px-5 py-2.5 rounded-xl text-sm font-bold text-brand-black"
              style={{ background: "linear-gradient(135deg, #1AAA80, #2EE8B4)" }}>
              Contratar
            </button>
            <button onClick={() => tomarDecisao("nao_aprovado")}
              className="px-5 py-2.5 rounded-xl text-sm font-bold"
              style={{ background: "rgba(252,165,165,0.15)", border: "1px solid rgba(252,165,165,0.3)", color: "#FCA5A5" }}>
              Não aprovado
            </button>
            <button onClick={() => tomarDecisao("banco_de_talentos")}
              className="px-5 py-2.5 rounded-xl text-sm font-bold"
              style={{ background: "rgba(167,139,250,0.15)", border: "1px solid rgba(167,139,250,0.3)", color: "#A78BFA" }}>
              Banco de talentos
            </button>
          </div>
          {decisaoErr && <p className="text-xs text-red-400">{decisaoErr}</p>}
        </div>
      )}
    </div>
  )
}
