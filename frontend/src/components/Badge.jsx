const COR = ["green", "amber", "red", "blue", "gray", "purple"]

export function Badge({ cor = "gray", children }) {
  const c = COR.includes(cor) ? cor : "gray"
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold"
      style={{
        background : `var(--badge-${c}-bg)`,
        color      : `var(--badge-${c}-text)`,
        border     : `1px solid var(--badge-${c}-border)`,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: `var(--badge-${c}-dot)` }}
      />
      {children}
    </span>
  )
}
