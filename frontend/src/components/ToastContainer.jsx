const ESTILOS = {
  sucesso: {
    bg:     "linear-gradient(135deg, rgba(22,163,74,0.97), rgba(16,134,60,0.97))",
    color:  "#fff",
    border: "1px solid rgba(74,222,128,0.45)",
    shadow: "0 8px 32px rgba(22,163,74,0.35)",
    icon:   "✓",
  },
  aviso: {
    bg:     "linear-gradient(135deg, rgba(161,98,7,0.97), rgba(120,75,0,0.97))",
    color:  "#fef08a",
    border: "1px solid rgba(234,179,8,0.45)",
    shadow: "0 8px 32px rgba(161,98,7,0.30)",
    icon:   "⚠",
  },
  erro: {
    bg:     "linear-gradient(135deg, rgba(185,28,28,0.97), rgba(153,27,27,0.97))",
    color:  "#fff",
    border: "1px solid rgba(252,165,165,0.45)",
    shadow: "0 8px 32px rgba(185,28,28,0.35)",
    icon:   "✕",
  },
  info: {
    bg:     "linear-gradient(135deg, rgba(26,139,191,0.97), rgba(14,80,120,0.97))",
    color:  "#fff",
    border: "1px solid rgba(77,200,232,0.45)",
    shadow: "0 8px 32px rgba(26,139,191,0.30)",
    icon:   "i",
  },
}

const CSS = `
@keyframes toast-in {
  from { opacity: 0; transform: translateY(-20px) scale(0.95); }
  to   { opacity: 1; transform: translateY(0)     scale(1);    }
}
@keyframes toast-out {
  from { opacity: 1; transform: translateY(0)     scale(1);    max-height: 80px; margin-bottom: 0; }
  to   { opacity: 0; transform: translateY(-12px) scale(0.93); max-height: 0;    margin-bottom: -8px; }
}
.toast-enter { animation: toast-in  0.30s cubic-bezier(0.34,1.56,0.64,1) forwards; }
.toast-exit  { animation: toast-out 0.38s cubic-bezier(0.4,0,0.2,1)      forwards; }
`

export function ToastContainer({ toasts }) {
  if (!toasts.length) return null
  return (
    <>
      <style>{CSS}</style>
      <div
        className="fixed top-5 right-5 z-[9999] flex flex-col gap-2 items-end pointer-events-none"
        style={{ maxWidth: "min(380px, calc(100vw - 40px))" }}
      >
        {toasts.map(t => {
          const s = ESTILOS[t.tipo] ?? ESTILOS.info
          return (
            <div
              key={t.id}
              className={`flex items-start gap-3 px-4 py-3 rounded-2xl text-sm font-semibold pointer-events-auto w-full overflow-hidden ${t.saindo ? "toast-exit" : "toast-enter"}`}
              style={{
                background   : s.bg,
                color        : s.color,
                border       : s.border,
                boxShadow    : s.shadow,
                backdropFilter: "blur(12px)",
              }}
            >
              <span
                className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold mt-[1px]"
                style={{ background: "rgba(255,255,255,0.22)" }}
              >
                {s.icon}
              </span>
              <span className="leading-snug">{t.msg}</span>
            </div>
          )
        })}
      </div>
    </>
  )
}
