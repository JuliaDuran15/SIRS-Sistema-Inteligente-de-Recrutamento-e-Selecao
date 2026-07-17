import { useState } from "react"

let _tid = 0

const _TRADUCOES = [
  [/value is not a valid email address.*period/i,    "E-mail inválido: domínio sem extensão válida (ex: nome@empresa.com)"],
  [/value is not a valid email address.*@-sign/i,    "E-mail inválido: domínio após o @ é inválido (ex: nome@empresa.com)"],
  [/value is not a valid email address/i,            "E-mail inválido"],
  [/field required/i,                                "Campo obrigatório"],
  [/string should have at most (\d+) character/i,    (m) => `Máximo de ${m[1]} caracteres`],
  [/string should have at least (\d+) character/i,   (m) => `Mínimo de ${m[1]} caracteres`],
  [/value is not a valid integer/i,                  "Valor deve ser um número inteiro"],
  [/value is not a valid number/i,                   "Valor deve ser numérico"],
]

function _traduzir(msg) {
  for (const [padrao, trad] of _TRADUCOES) {
    const m = msg.match(padrao)
    if (m) return typeof trad === "function" ? trad(m) : trad
  }
  return msg
}

/** Extrai mensagem legível de erros axios/FastAPI (string ou array Pydantic). */
export function extrairErro(err, fallback = "Erro inesperado") {
  const detail = err?.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) return detail.map(d => _traduzir(d.msg ?? String(d))).join("; ")
  return fallback
}

export function useToast(duracao = 5000) {
  const [toasts, setToasts] = useState([])

  function mostrarToast(msg, tipo = "info") {
    const id = ++_tid
    const texto = typeof msg === "string" ? msg : String(msg)
    setToasts(prev => [...prev, { id, msg: texto, tipo }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duracao)
  }

  return { toasts, mostrarToast }
}
