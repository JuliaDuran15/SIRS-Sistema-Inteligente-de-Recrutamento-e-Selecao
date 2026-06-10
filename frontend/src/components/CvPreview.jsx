import { useState, useEffect, useRef } from "react"
import { getCurriculoPdf } from "../api"

/**
 * Painel de preview inline do currículo.
 *
 * Se `temPdf` for true, busca o PDF via API (com autenticação),
 * cria um object URL e exibe em <iframe>.
 * Caso contrário (webhook / texto apenas), exibe o texto extraído.
 *
 * Props:
 *   candidaturaId  — id da candidatura
 *   temPdf         — boolean: arquivo_pdf != null
 *   textoExtraido  — string: texto_extraido do currículo
 */
export function CvPreview({ candidaturaId, temPdf, textoExtraido }) {
  const [aberto, setAberto]     = useState(false)
  const [modo, setModo]         = useState(temPdf ? "pdf" : "texto")
  const [pdfUrl, setPdfUrl]     = useState(null)
  const [carregando, setCarreg] = useState(false)
  const [erro, setErro]         = useState(null)
  const urlRef                  = useRef(null)

  // Carrega o PDF quando o painel é aberto pela primeira vez em modo pdf
  useEffect(() => {
    if (!aberto || modo !== "pdf" || pdfUrl || !temPdf) return
    setCarreg(true)
    setErro(null)
    getCurriculoPdf(candidaturaId)
      .then(r => {
        const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }))
        urlRef.current = url
        setPdfUrl(url)
      })
      .catch(() => setErro("Não foi possível carregar o PDF."))
      .finally(() => setCarreg(false))
  }, [aberto, modo, pdfUrl, temPdf, candidaturaId])

  // Revoga o object URL quando o componente desmonta
  useEffect(() => {
    return () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current) }
  }, [])

  if (!textoExtraido && !temPdf) return null

  return (
    <div>
      <button
        onClick={() => setAberto(v => !v)}
        className="flex items-center gap-1.5 text-xs font-semibold transition-colors"
        style={{ color: aberto ? "#4DC8E8" : "var(--t-muted2)" }}
      >
        <span style={{ fontSize: "10px" }}>{aberto ? "▾" : "▸"}</span>
        {aberto ? "Fechar currículo" : "Ver currículo"}
      </button>

      {aberto && (
        <div className="mt-2 rounded-xl overflow-hidden"
          style={{ border: "1px solid var(--b-card)" }}>

          {/* Barra de controles */}
          <div className="flex items-center justify-between px-3 py-2 border-b"
            style={{ background: "var(--s-content)", borderColor: "var(--b-subtle)" }}>

            {/* Tabs pdf/texto */}
            <div className="flex gap-1">
              {temPdf && (
                <button
                  onClick={() => setModo("pdf")}
                  className="px-3 py-1 rounded-lg text-xs font-semibold transition-all"
                  style={modo === "pdf"
                    ? { background: "rgba(26,139,191,0.2)", color: "#4DC8E8" }
                    : { color: "var(--t-muted2)" }}>
                  PDF original
                </button>
              )}
              {textoExtraido && (
                <button
                  onClick={() => setModo("texto")}
                  className="px-3 py-1 rounded-lg text-xs font-semibold transition-all"
                  style={modo === "texto"
                    ? { background: "rgba(26,139,191,0.2)", color: "#4DC8E8" }
                    : { color: "var(--t-muted2)" }}>
                  Texto extraído
                </button>
              )}
            </div>

            <button
              onClick={() => setAberto(false)}
              className="text-brand-pale/30 hover:text-brand-pale transition-colors text-base leading-none"
            >
              ×
            </button>
          </div>

          {/* Conteúdo */}
          {modo === "pdf" ? (
            carregando ? (
              <div className="flex items-center justify-center gap-2 py-10"
                style={{ background: "var(--s-content)" }}>
                <span className="w-4 h-4 border-2 rounded-full animate-spin"
                  style={{ borderColor: "var(--b-normal)", borderTopColor: "#4DC8E8" }} />
                <span className="text-xs text-brand-pale/40">Carregando PDF...</span>
              </div>
            ) : erro ? (
              <div className="py-8 text-center" style={{ background: "var(--s-content)" }}>
                <p className="text-xs text-red-400">{erro}</p>
              </div>
            ) : pdfUrl ? (
              <iframe
                src={pdfUrl}
                title="Currículo"
                className="w-full"
                style={{ height: "600px", border: "none", background: "#fff" }}
              />
            ) : null
          ) : (
            <div
              className="overflow-y-auto p-4"
              style={{
                maxHeight     : "500px",
                background    : "var(--s-content)",
                whiteSpace    : "pre-wrap",
                fontFamily    : "var(--font-mono)",
                fontSize      : "12px",
                lineHeight    : "1.7",
                color         : "var(--t-muted2)",
                wordBreak     : "break-word",
              }}
            >
              {textoExtraido || "Texto não disponível."}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
