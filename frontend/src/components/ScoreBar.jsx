export function ScoreBar({ score, label, showValue = true }) {
  const gradient =
    score >= 70 ? "linear-gradient(90deg, #34d399, #10b981)" :
    score >= 50 ? "linear-gradient(90deg, #fbbf24, #f59e0b)" :
                  "linear-gradient(90deg, #f87171, #ef4444)"

  const textCor =
    score >= 70 ? "text-emerald-600" :
    score >= 50 ? "text-amber-600"   :
                  "text-red-500"

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        {showValue && (
          <span className={`text-xs font-mono font-bold ${textCor}`}>
            {score}
            <span className="text-slate-300 font-normal">/100</span>
          </span>
        )}
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${Math.min(score, 100)}%`, background: gradient }}
        />
      </div>
    </div>
  )
}
