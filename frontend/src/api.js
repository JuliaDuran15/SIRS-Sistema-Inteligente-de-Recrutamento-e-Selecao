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

export const getVagas        = ()         => api.get("/vagas/")
export const createVaga      = (data)     => api.post("/vagas/", data)
export const getVaga         = (id)       => api.get(`/vagas/${id}`)
export const updatePesos     = (id, data) => api.patch(`/vagas/${id}/pesos`, data)
export const analisarMercado = (id)       => api.post(`/vagas/${id}/analisar-mercado`)

export const getCandidatos   = ()         => api.get("/candidatos/")
export const createCandidato = (data)     => api.post("/candidatos/", data)
export const getCandidato    = (id)       => api.get(`/candidatos/${id}`)

export const getCandidaturas    = (vagaId) => api.get(`/candidaturas/?vaga_id=${vagaId}`)
export const createCandidatura  = (data)   => api.post("/candidaturas/", data)
export const getCandidatura     = (id)     => api.get(`/candidaturas/${id}`)
export const atualizarStatusCandidatura = (id, novoStatus, ator) =>
  api.patch(`/candidaturas/${id}/status?novo_status=${novoStatus}&ator=${encodeURIComponent(ator)}`)

export const getEntrevistas     = (candidaturaId) => api.get(`/entrevistas/candidatura/${candidaturaId}`)
export const agendarEntrevista  = (data)           => api.post("/entrevistas/", data)
export const registrarResultado = (id, data)       => api.patch(`/entrevistas/${id}/resultado`, data)

export const getUsuarios    = ()         => api.get("/usuarios/")
export const createUsuario  = (data)     => api.post("/usuarios/", data)
export const deleteUsuario  = (id)       => api.delete(`/usuarios/${id}`)

export const uploadCurriculo = (candidaturaId, arquivo) => {
  const form = new FormData()
  form.append("arquivo", arquivo)
  return api.post(`/candidaturas/${candidaturaId}/curriculo`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  })
}

export default api
