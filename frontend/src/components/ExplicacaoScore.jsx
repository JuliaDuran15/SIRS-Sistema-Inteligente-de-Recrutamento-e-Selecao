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

export function ExplicacaoScore({ explicacao, expandido, onToggle }) {
  if (!explicacao) return null
  const { componentes, sinais_estruturais: sinais } = explicacao
  const vaga_c  = componentes?.aderencia_vaga    ?? {}
  const mkt_c   = componentes?.aderencia_mercado ?? {}
  const skills  = sinais?.habilidades_em_comum   ?? []
  const anosExp = sinais?.anos_experiencia        ?? 0
  const nivEduc = sinais?.nivel_educacao          ?? 0

  return (
    <div>
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
                {anosExp > 0 && ` · ${anosExp} ${anosExp === 1 ? "ano" : "anos"} de experiência`}
                {nivEduc > 0 && ` · educação ${Math.round(nivEduc * 100)}%`}
              </p>
            </div>
          )}

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

          {skills.length > 0 && (
            <div className="space-y-1.5 pt-1 border-t" style={{ borderColor: "var(--b-ghost)" }}>
              <span className="text-xs text-brand-pale/35">
                {skills.length} {skills.length === 1 ? "skill do candidato" : "skills do candidato"} alinhadas ao perfil da vaga:
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

          {skills.length === 0 && anosExp === 0 && (
            <p className="text-xs text-brand-pale/25 italic">
              Nenhuma skill específica detectada — score baseado em similaridade semântica do texto.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
