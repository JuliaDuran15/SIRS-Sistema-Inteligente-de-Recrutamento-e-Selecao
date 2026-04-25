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

export default api
