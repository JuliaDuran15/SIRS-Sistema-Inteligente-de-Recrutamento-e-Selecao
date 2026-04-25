const estilos = {
  green  : "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  amber  : "bg-amber-50   text-amber-700   ring-1 ring-amber-200",
  red    : "bg-red-50     text-red-700     ring-1 ring-red-200",
  blue   : "bg-blue-50    text-blue-700    ring-1 ring-blue-200",
  gray   : "bg-slate-100  text-slate-500   ring-1 ring-slate-200",
  purple : "bg-violet-50  text-violet-700  ring-1 ring-violet-200",
}

const dots = {
  green  : "bg-emerald-500",
  amber  : "bg-amber-400",
  red    : "bg-red-400",
  blue   : "bg-blue-400",
  gray   : "bg-slate-400",
  purple : "bg-violet-500",
}

export function Badge({ cor = "gray", children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${estilos[cor]}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dots[cor]}`} />
      {children}
    </span>
  )
}
