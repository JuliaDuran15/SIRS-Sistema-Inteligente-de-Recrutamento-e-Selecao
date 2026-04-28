export function ScoreBar({ score, label, showValue = true }) {
  const tier     = score >= 70 ? "high" : score >= 50 ? "mid" : "low"
  const gradient = `var(--score-${tier}-grad)`
  const textColor= `var(--score-${tier})`

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-brand-pale/60">{label}</span>
        {showValue && (
          <span className="text-xs font-mono font-bold" style={{ color: textColor }}>
            {score}
            <span className="font-normal" style={{ color: "var(--t-score)" }}>/100</span>
          </span>
        )}
      </div>
      <div className="w-full rounded-full h-2 overflow-hidden" style={{ background: "var(--s-track)" }}>
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${Math.min(score, 100)}%`, background: gradient }}
        />
      </div>
    </div>
  )
}
