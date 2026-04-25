export function ScoreBar({ score, label, showValue = true }) {
  const gradient =
    score >= 70 ? "linear-gradient(90deg, #1AAA80, #2EE8B4)" :
    score >= 50 ? "linear-gradient(90deg, #F59E0B, #FCD34D)" :
                  "linear-gradient(90deg, #EF4444, #FCA5A5)"

  const textColor =
    score >= 70 ? "#2EE8B4" :
    score >= 50 ? "#FCD34D" :
                  "#FCA5A5"

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-brand-pale/60">{label}</span>
        {showValue && (
          <span className="text-xs font-mono font-bold" style={{ color: textColor }}>
            {score}
            <span className="font-normal" style={{ color: "rgba(125,216,240,0.3)" }}>/100</span>
          </span>
        )}
      </div>
      <div
        className="w-full rounded-full h-2 overflow-hidden"
        style={{ background: "rgba(7, 17, 26, 0.5)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${Math.min(score, 100)}%`, background: gradient }}
        />
      </div>
    </div>
  )
}
