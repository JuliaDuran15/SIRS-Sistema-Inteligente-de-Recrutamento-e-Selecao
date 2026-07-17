const ESTILOS = {
  sucesso: {
    bg:     "rgba(22,163,74,0.95)",
    color:  "#fff",
    border: "1px solid rgba(74,222,128,0.5)",
    icon:   "✓",
  },
  aviso: {
    bg:     "rgba(120,75,0,0.95)",
    color:  "#fef08a",
    border: "1px solid rgba(234,179,8,0.5)",
    icon:   "⚠",
  },
  erro: {
    bg:     "rgba(185,28,28,0.95)",
    color:  "#fff",
    border: "1px solid rgba(252,165,165,0.5)",
    icon:   "✕",
  },
  info: {
    bg:     "rgba(26,139,191,0.95)",
    color:  "#fff",
    border: "1px solid rgba(77,200,232,0.5)",
    icon:   "i",
  },
}

export function ToastContainer({ toasts }) {
  if (!toasts.length) return null
  return (
    <div className="fixed bottom-6 right-6 z-[70] flex flex-col gap-2 items-end pointer-events-none">
      {toasts.map(t => {
        const s = ESTILOS[t.tipo] ?? ESTILOS.info
        return (
          <div
            key={t.id}
            className="flex items-start gap-2 px-4 py-3 rounded-xl text-sm font-semibold shadow-lg pointer-events-auto max-w-sm"
            style={{ background: s.bg, color: s.color, border: s.border }}
          >
            <span
              className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold mt-[1px]"
              style={{ background: "rgba(255,255,255,0.2)" }}
            >
              {s.icon}
            </span>
            <span>{t.msg}</span>
          </div>
        )
      })}
    </div>
  )
}
