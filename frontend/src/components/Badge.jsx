const palette = {
  green:  { bg: "rgba(26,170,128,0.18)",    text: "#2EE8B4",               border: "rgba(26,170,128,0.35)",   dot: "#1AAA80"  },
  amber:  { bg: "rgba(245,158,11,0.15)",    text: "#FCD34D",               border: "rgba(245,158,11,0.3)",    dot: "#F59E0B"  },
  red:    { bg: "rgba(239,68,68,0.15)",     text: "#FCA5A5",               border: "rgba(239,68,68,0.25)",    dot: "#EF4444"  },
  blue:   { bg: "rgba(26,139,191,0.2)",     text: "#4DC8E8",               border: "rgba(26,139,191,0.3)",    dot: "#1A8BBF"  },
  gray:   { bg: "rgba(125,216,240,0.08)",   text: "rgba(125,216,240,0.6)", border: "rgba(125,216,240,0.15)",  dot: "#7DD8F0"  },
  purple: { bg: "rgba(167,139,250,0.15)",   text: "#C4B5FD",               border: "rgba(167,139,250,0.25)",  dot: "#A78BFA"  },
}

export function Badge({ cor = "gray", children }) {
  const p = palette[cor] ?? palette.gray
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: p.bg, color: p.text, border: `1px solid ${p.border}` }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: p.dot }} />
      {children}
    </span>
  )
}
