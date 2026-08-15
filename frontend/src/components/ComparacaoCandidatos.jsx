const NIVEL_LABEL = {
  0: "Estágio/Trainee", 1: "Júnior", 2: "Pleno",
  3: "Sênior", 4: "Lead/Staff", 5: "Gestão/Head", 6: "Direção/CxO",
}
const EDUC_LABEL = {
  0: "—", 1: "Técnico", 2: "Grad. incompleta",
  3: "Graduação", 4: "Pós/MBA", 5: "Mestrado", 6: "Doutorado",
}

function corScore(v) {
  if (v >= 70) return "var(--score-high)"
  if (v >= 50) return "var(--score-mid)"
  return "var(--score-low)"
}

function MiniBar({ valor, max = 100 }) {
  const cor = corScore(valor)
  return (
    <div className="flex items-center gap-2 mt-0.5">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--s-track)" }}>
        <div className="h-full rounded-full" style={{ width: `${(valor / max) * 100}%`, background: cor }} />
      </div>
      <span className="text-xs font-mono font-bold w-8 text-right flex-shrink-0" style={{ color: cor }}>
        {valor}
      </span>
    </div>
  )
}

function Celula({ children, destaque }) {
  return (
    <td className="px-4 py-3 align-top" style={destaque ? { background: "var(--b-ghost)" } : undefined}>
      {children}
    </td>
  )
}

function Label({ children }) {
  return (
    <td className="px-4 py-3 align-top w-36 flex-shrink-0">
      <span className="text-xs text-brand-pale/40 font-semibold">{children}</span>
    </td>
  )
}

function SecaoHeader({ children, cols }) {
  return (
    <tr style={{ borderTop: "1px solid var(--b-divider)" }}>
      <td colSpan={cols + 1} className="px-4 pt-5 pb-2">
        <span className="text-xs font-bold text-brand-pale/30 uppercase tracking-widest">{children}</span>
      </td>
    </tr>
  )
}

export function ComparacaoCandidatos({ candidaturas, rankMap, onClose }) {
  const skillsVaga = new Set()
  candidaturas.forEach(c => {
    const comuns = c.curriculo?.explicacao?.sinais_estruturais?.habilidades_em_comum ?? []
    comuns.forEach(s => skillsVaga.add(s))
  })

  const todasHabilidades = new Set()
  candidaturas.forEach(c => {
    const skills = c.curriculo?.explicacao?.sinais_estruturais?.habilidades ?? []
    skills.forEach(s => todasHabilidades.add(s))
  })

  const skillsSorted = [...todasHabilidades].sort((a, b) => {
    const aV = skillsVaga.has(a), bV = skillsVaga.has(b)
    if (aV !== bV) return aV ? -1 : 1
    return a.localeCompare(b)
  })

  const skillsComuns = skillsSorted.filter(s => skillsVaga.has(s))
  const skillsExtras = skillsSorted.filter(s => !skillsVaga.has(s))
  const ncols = candidaturas.length

  return (
    <div
      className="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(7,17,26,0.7)", backdropFilter: "blur(6px)" }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full overflow-auto rounded-2xl"
        style={{
          maxWidth: ncols === 2 ? "680px" : "920px",
          maxHeight: "90vh",
          background: "var(--color-brand-teal)",
          border: "1px solid var(--b-card)",
          boxShadow: "0 24px 80px rgba(0,0,0,0.35)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 sticky top-0 z-10"
          style={{
            background: "var(--color-brand-teal)",
            borderBottom: "1px solid var(--b-divider)",
          }}
        >
          <div>
            <h2 className="text-base font-bold text-brand-cloud">Comparação de candidatos</h2>
            <p className="text-xs text-brand-pale/35 mt-0.5">
              {ncols} candidatos · scores calculados pela IA para esta vaga
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-brand-pale/40 hover:text-brand-cloud transition-colors text-lg"
            style={{ background: "var(--s-chip)" }}
          >
            ×
          </button>
        </div>

        {/* Tabela */}
        <div className="px-2 pb-6 overflow-x-auto">
          <table className="w-full border-collapse">
            <colgroup>
              <col style={{ width: "144px" }} />
              {candidaturas.map(c => <col key={c.id} />)}
            </colgroup>

            <thead>
              <tr>
                <td className="px-4 py-4" />
                {candidaturas.map((c, i) => {
                  const rank  = rankMap[c.id]
                  const score = c.curriculo?.score_curriculo ?? c.score_total ?? null
                  const rankColors = [
                    { bg: "linear-gradient(135deg,#1AAA80,#2EE8B4)", text: "#07111A" },
                    { bg: "linear-gradient(135deg,#1A8BBF,#4DC8E8)", text: "#07111A" },
                    { bg: "var(--b-strong)",                         text: "var(--color-brand-sky)" },
                  ]
                  const rc = rankColors[i] ?? rankColors[2]

                  return (
                    <td key={c.id} className="px-4 py-4 align-top">
                      <div className="flex items-start gap-3">
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold mt-0.5"
                          style={{ background: rc.bg, color: rc.text }}
                        >
                          {rank != null ? rank : i + 1}
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-brand-cloud text-sm leading-tight truncate">
                            {c.candidato?.nome ?? "—"}
                          </p>
                          <p className="text-xs text-brand-pale/35 font-mono mt-0.5 truncate">
                            {c.candidato?.email}
                          </p>
                          {score !== null && (
                            <p
                              className="text-2xl font-bold font-mono mt-2 leading-none"
                              style={{ color: corScore(score) }}
                            >
                              {score}
                              <span className="text-xs text-brand-pale/30 font-normal"> /100</span>
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                  )
                })}
              </tr>
            </thead>

            <tbody>
              <SecaoHeader cols={ncols}>Scores</SecaoHeader>

              <tr>
                <Label>Aderência à vaga</Label>
                {candidaturas.map(c => {
                  const v = c.curriculo?.score_rh ?? null
                  return (
                    <Celula key={c.id}>
                      {v !== null
                        ? <MiniBar valor={v} />
                        : <span className="text-xs text-brand-pale/25">—</span>}
                    </Celula>
                  )
                })}
              </tr>

              <tr>
                <Label>Aderência ao mercado</Label>
                {candidaturas.map(c => {
                  const v = c.curriculo?.score_mercado ?? null
                  return (
                    <Celula key={c.id}>
                      {v !== null
                        ? <MiniBar valor={v} />
                        : <span className="text-xs text-brand-pale/25">—</span>}
                    </Celula>
                  )
                })}
              </tr>

              <SecaoHeader cols={ncols}>Features estruturais</SecaoHeader>

              <tr>
                <Label>Experiência</Label>
                {candidaturas.map(c => {
                  const anos = c.curriculo?.explicacao?.sinais_estruturais?.anos_experiencia ?? null
                  return (
                    <Celula key={c.id}>
                      <span className="text-sm font-mono font-bold text-brand-cloud">
                        {anos !== null ? `${anos.toFixed(1)} anos` : "—"}
                      </span>
                    </Celula>
                  )
                })}
              </tr>

              <tr>
                <Label>Senioridade</Label>
                {candidaturas.map(c => {
                  const nivel = c.curriculo?.explicacao?.sinais_estruturais?.nivel_senioridade ?? null
                  return (
                    <Celula key={c.id}>
                      <span className="text-sm text-brand-pale/80">
                        {nivel !== null ? NIVEL_LABEL[nivel] ?? `nível ${nivel}` : "—"}
                      </span>
                    </Celula>
                  )
                })}
              </tr>

              <tr>
                <Label>Educação</Label>
                {candidaturas.map(c => {
                  const educ = c.curriculo?.explicacao?.sinais_estruturais?.nivel_educacao ?? null
                  return (
                    <Celula key={c.id}>
                      <span className="text-sm text-brand-pale/80">
                        {educ !== null ? EDUC_LABEL[educ] ?? `nível ${educ}` : "—"}
                      </span>
                    </Celula>
                  )
                })}
              </tr>

              {skillsComuns.length > 0 && (
                <>
                  <SecaoHeader cols={ncols}>
                    Skills em comum com a vaga ({skillsComuns.length})
                  </SecaoHeader>
                  {skillsComuns.map(skill => (
                    <tr key={skill}>
                      <Label>
                        <span className="font-mono text-brand-emerald">{skill}</span>
                      </Label>
                      {candidaturas.map(c => {
                        const comuns    = new Set(c.curriculo?.explicacao?.sinais_estruturais?.habilidades_em_comum ?? [])
                        const todasSkls = new Set(c.curriculo?.explicacao?.sinais_estruturais?.habilidades ?? [])
                        const temComum  = comuns.has(skill)
                        const temSkill  = todasSkls.has(skill)
                        return (
                          <Celula key={c.id} destaque={temComum}>
                            {temComum
                              ? <span className="text-sm font-bold text-brand-emerald">✓</span>
                              : temSkill
                                ? <span className="text-xs text-brand-pale/40">tem</span>
                                : <span className="text-xs text-brand-pale/20">—</span>}
                          </Celula>
                        )
                      })}
                    </tr>
                  ))}
                </>
              )}

              {skillsExtras.length > 0 && (
                <>
                  <SecaoHeader cols={ncols}>Outras skills detectadas</SecaoHeader>
                  {skillsExtras.map(skill => (
                    <tr key={skill}>
                      <Label>
                        <span className="font-mono text-brand-pale/55">{skill}</span>
                      </Label>
                      {candidaturas.map(c => {
                        const todasSkls = new Set(c.curriculo?.explicacao?.sinais_estruturais?.habilidades ?? [])
                        const tem = todasSkls.has(skill)
                        return (
                          <Celula key={c.id}>
                            {tem
                              ? <span className="text-sm text-brand-pale/60">✓</span>
                              : <span className="text-xs text-brand-pale/20">—</span>}
                          </Celula>
                        )
                      })}
                    </tr>
                  ))}
                </>
              )}

              {skillsComuns.length === 0 && skillsExtras.length === 0 && (
                <tr>
                  <td colSpan={ncols + 1} className="px-4 py-4 text-center">
                    <span className="text-xs text-brand-pale/25 italic">
                      Nenhuma skill estrutural detectada — scores baseados em similaridade semântica.
                    </span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
