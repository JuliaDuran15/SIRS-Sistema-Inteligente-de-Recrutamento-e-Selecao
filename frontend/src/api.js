import axios from "axios"

const api = axios.create({
  baseURL: "/api",
})

// Injeta o token JWT em todas as requisições autenticadas
api.interceptors.request.use(config => {
  const token = localStorage.getItem("token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const loginUsuario = (email, senha) =>
  api.post("/auth/token", new URLSearchParams({ username: email, password: senha }), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  })

export const getVagas         = ()          => api.get("/vagas/")
export const createVaga       = (data)      => api.post("/vagas/", data)
export const getVaga          = (id)        => api.get(`/vagas/${id}`)
export const updatePesos      = (id, data)  => api.patch(`/vagas/${id}/pesos`, data)
export const updateVagaStatus = (id, status)=> api.patch(`/vagas/${id}/status`, null, { params: { status } })
export const updateVagaInfo        = (id, data) => api.patch(`/vagas/${id}/requisitos`, data)
export const updateGestores        = (id, ids)  => api.patch(`/vagas/${id}/gestores`, { gestores_ids: ids })
export const updateRhsAutorizados  = (id, ids)  => api.patch(`/vagas/${id}/rhs-autorizados`, { rhs_autorizados: ids })
export const analisarMercado  = (id)        => api.post(`/vagas/${id}/analisar-mercado`)
export const rerankarVaga     = (id)        => api.post(`/vagas/${id}/rerankar`)
export const exportarVaga     = (id)        => api.get(`/vagas/${id}/exportar`, { responseType: "blob" })

export const getCandidatos    = (params)      => api.get("/candidatos/", { params })
export const createCandidato  = (data)        => api.post("/candidatos/", data)
export const getCandidato     = (id)          => api.get(`/candidatos/${id}`)
export const updateCandidato  = (id, data)    => api.patch(`/candidatos/${id}`, data)

export const getCandidaturas    = (vagaId)      => api.get(`/candidaturas/?vaga_id=${vagaId}`)
export const getCandidaturasPorCandidato = (cid)=> api.get(`/candidaturas/?candidato_id=${cid}`)
export const createCandidatura  = (data)        => api.post("/candidaturas/", data)
export const getCandidatura     = (id)          => api.get(`/candidaturas/${id}`)
export const deleteCandidatura  = (id)          => api.delete(`/candidaturas/${id}`)
export const getCurriculo          = (candidaturaId)       => api.get(`/candidaturas/${candidaturaId}/curriculo`)
export const getCurriculoPdf       = (candidaturaId)       => api.get(`/candidaturas/${candidaturaId}/curriculo/pdf`, { responseType: "blob" })
export const uploadCurriculoTexto  = (candidaturaId, texto)=> api.post(`/candidaturas/${candidaturaId}/curriculo/texto`, { texto })
export const atualizarStatusCandidatura = (id, novoStatus, ator) =>
  api.patch(`/candidaturas/${id}/status?novo_status=${novoStatus}&ator=${encodeURIComponent(ator)}`)
export const triagemEmLote = (candidatura_ids, novo_status, ator) =>
  api.post("/candidaturas/triagem-em-lote", { candidatura_ids, novo_status, ator })

export const getEntrevistas     = (candidaturaId) => api.get(`/entrevistas/candidatura/${candidaturaId}`)
export const agendarEntrevista  = (data)           => api.post("/entrevistas/", data)
export const registrarResultado = (id, data)       => api.patch(`/entrevistas/${id}/resultado`, data)
export const editarAnotacoes    = (id, anotacoes)  => api.patch(`/entrevistas/${id}/anotacoes`, { anotacoes })
export const resumirTranscricao = (id, transcricao)=> api.post(`/entrevistas/${id}/resumir-transcricao`, { transcricao })

export const getUsuarios    = ()         => api.get("/usuarios/")
export const createUsuario  = (data)     => api.post("/usuarios/", data)
export const updateUsuario  = (id, data) => api.patch(`/usuarios/${id}`, data)
export const deleteUsuario  = (id)       => api.delete(`/usuarios/${id}`)
export const getAnalyticsResumo  = ()         => api.get("/analytics/resumo")
export const getAnalyticsFunil   = (vaga_id)  => api.get("/analytics/funil",  vaga_id ? { params: { vaga_id } } : {})
export const getAnalyticsScores  = (vaga_id)  => api.get("/analytics/scores", { params: { vaga_id } })
export const getAuditoria        = (params)   => api.get("/analytics/auditoria", { params })

export const alterarSenha   = (data)     => api.patch("/auth/senha", data)
export const esqueceuSenha  = (email)    => api.post("/auth/esqueceu-senha", { email })
export const resetarSenha   = (data)     => api.post("/auth/resetar-senha", data)

export const uploadCurriculo = (candidaturaId, arquivo) => {
  const form = new FormData()
  form.append("arquivo", arquivo)
  return api.post(`/candidaturas/${candidaturaId}/curriculo`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  })
}

export default api
