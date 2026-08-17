const LABELS_SENIORIDADE = ["estágio", "júnior", "pleno", "sênior", "lead", "gestão", "direção"]
const LABELS_EDUCACAO    = ["", "técnico", "grad. incompleta", "graduação", "pós/MBA", "mestrado", "doutorado"]

function MiniBar({ valor, cor }) {
  return (
    <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--s-track)" }}>
      <div className="h-full rounded-full transition-all" style={{ width: `${valor}%`, background: cor }} />
    </div>
  )
}

function corComp(cls) {
  return cls === "excelente" ? "#2EE8B4" : cls === "bom" ? "#4DC8E8" :
         cls === "regular"   ? "#FCD34D" : "#FCA5A5"
}

function SinalChip({ label }) {
  return (
    <span className="text-xs px-2 py-1 rounded-lg"
      style={{
        background: "rgba(77,200,232,0.07)",
        color: "rgba(125,216,240,0.65)",
        border: "1px solid rgba(77,200,232,0.12)",
      }}>
      {label}
    </span>
  )
}

export function ExplicacaoScore({ explicacao, expandido, onToggle }) {
  if (!explicacao) return null
  const { componentes, sinais_estruturais: sinais, alerta_nome: alertaNome } = explicacao
  const vaga_c   = componentes?.aderencia_vaga    ?? {}
  const mkt_c    = componentes?.aderencia_mercado ?? {}
  const skills   = sinais?.habilidades_em_comum ?? []
  const ausentes = sinais?.habilidades_ausentes  ?? []
  const anosExp  = sinais?.anos_experiencia       ?? 0
  const nivSen   = sinais?.nivel_senioridade      ?? 0
  const nivEduc  = sinais?.nivel_educacao         ?? 0
  const bonus    = explicacao?.bonus_estrutural   ?? 0

  const temSinais = anosExp > 0 || nivSen > 0 || nivEduc > 0

  return (
    <div className="space-y-2">
      {alertaNome?.match === false && (
        <div className="alerta-nome-cv flex items-start gap-2.5 px-3 py-2.5 rounded-xl"
          style={{ background: "rgba(252,193,60,0.08)", border: "1px solid rgba(252,193,60,0.35)" }}>
          <span className="alerta-nome-cv__icone text-amber-400 text-base leading-none mt-0.5 flex-shrink-0">⚠</span>
          <div className="min-w-0">
            <p className="alerta-nome-cv__titulo text-xs font-bold text-amber-400">CV pode não pertencer a este candidato</p>
            <p className="alerta-nome-cv__corpo text-xs text-amber-300/70 mt-0.5 leading-relaxed">
              Nome cadastrado <span className="font-mono font-semibold">{alertaNome.nome_cadastrado}</span> não
              foi encontrado no início do documento
              {alertaNome.tokens_ausentes?.length > 0 && (
                <> (ausentes: <span className="font-mono">{alertaNome.tokens_ausentes.join(", ")}</span>)</>
              )}.
              Confira se o arquivo enviado é o CV correto.
            </p>
          </div>
        </div>
      )}

      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-xs transition-colors mt-1"
        style={{ color: "var(--t-faint2)" }}
        onMouseEnter={e => e.currentTarget.style.color = "var(--t-muted2)"}
        onMouseLeave={e => e.currentTarget.style.color = "var(--t-faint2)"}
      >
        <span>{expandido ? "▾" : "▸"}</span>
        <span>Ver detalhes do score</span>
      </button>

      {expandido && (
        <div className="mt-2 rounded-xl p-3 space-y-3"
          style={{ background: "var(--s-content)", border: "1px solid var(--b-ghost)" }}>

          {/* Aderência à vaga */}
          {vaga_c.score != null && (
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-brand-pale/50">Aderência aos requisitos da vaga</span>
                <span className="text-xs font-mono font-bold" style={{ color: corComp(vaga_c.classificacao) }}>
                  {vaga_c.score}/100
                  <span className="text-brand-pale/30 font-normal ml-1">· peso {vaga_c.peso}</span>
                </span>
              </div>
              <MiniBar valor={vaga_c.score} cor={corComp(vaga_c.classificacao)} />
              <p className="text-xs text-brand-pale/30">
                Contribui com <strong style={{ color: corComp(vaga_c.classificacao) }}>{vaga_c.contribuicao} pts</strong> no score final
              </p>
            </div>
          )}

          {/* Aderência ao mercado */}
          {mkt_c.score != null && (
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-brand-pale/50">Aderência ao mercado de trabalho</span>
                <span className="text-xs font-mono font-bold" style={{ color: corComp(mkt_c.classificacao) }}>
                  {mkt_c.score}/100
                  <span className="text-brand-pale/30 font-normal ml-1">· peso {mkt_c.peso}</span>
                </span>
              </div>
              <MiniBar valor={mkt_c.score} cor={corComp(mkt_c.classificacao)} />
              <p className="text-xs text-brand-pale/30">
                Contribui com <strong style={{ color: corComp(mkt_c.classificacao) }}>{mkt_c.contribuicao} pts</strong> no score final
                · compara skills do CV com demanda real de vagas do mercado
              </p>
            </div>
          )}

          {/* Bônus estrutural */}
          {bonus !== 0 && (
            <div className="flex items-center justify-between text-xs pt-1 border-t"
              style={{ borderColor: "var(--b-ghost)" }}>
              <span style={{ color: "rgba(125,216,240,0.4)" }}>Bônus estrutural</span>
              <span className="font-mono font-bold"
                style={{ color: bonus > 0 ? "#2EE8B4" : "#FCA5A5" }}>
                {bonus > 0 ? "+" : ""}{bonus} pts
              </span>
            </div>
          )}

          {/* Perfil detectado */}
          {temSinais && (
            <div className="space-y-1.5 pt-2 border-t" style={{ borderColor: "var(--b-ghost)" }}>
              <span className="text-xs" style={{ color: "rgba(125,216,240,0.3)" }}>Perfil detectado</span>
              <div className="flex flex-wrap gap-1.5">
                {anosExp > 0 && (
                  <SinalChip label={`${anosExp} ${anosExp === 1 ? "ano" : "anos"} de exp.`} />
                )}
                {nivSen > 0 && (
                  <SinalChip label={LABELS_SENIORIDADE[nivSen]} />
                )}
                {nivEduc > 0 && (
                  <SinalChip label={LABELS_EDUCACAO[nivEduc]} />
                )}
              </div>
            </div>
          )}

          {/* Skills em comum */}
          {skills.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t" style={{ borderColor: "var(--b-ghost)" }}>
              <span className="text-xs" style={{ color: "rgba(125,216,240,0.3)" }}>
                {skills.length} {skills.length === 1 ? "skill" : "skills"} alinhadas ao perfil da vaga
              </span>
              <div className="flex flex-wrap gap-1.5">
                {skills.map(s => (
                  <span key={s} className="text-xs px-2 py-0.5 rounded-lg font-mono"
                    style={{ background: "rgba(26,170,128,0.12)", color: "#2EE8B4" }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Skills faltantes */}
          {ausentes.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t" style={{ borderColor: "var(--b-ghost)" }}>
              <span className="text-xs" style={{ color: "rgba(125,216,240,0.3)" }}>
                {ausentes.length} {ausentes.length === 1 ? "skill exigida" : "skills exigidas"} não encontradas no CV
              </span>
              <div className="flex flex-wrap gap-1.5">
                {ausentes.map(s => (
                  <span key={s} className="text-xs px-2 py-0.5 rounded-lg font-mono"
                    style={{
                      background: "rgba(252,165,165,0.07)",
                      color: "rgba(252,165,165,0.45)",
                      border: "1px solid rgba(252,165,165,0.12)",
                    }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {skills.length === 0 && ausentes.length === 0 && !temSinais && (
            <p className="text-xs italic" style={{ color: "rgba(125,216,240,0.2)" }}>
              Nenhuma skill específica detectada — score baseado em similaridade semântica do texto.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
