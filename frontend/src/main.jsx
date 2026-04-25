import React, { useState, useEffect } from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Layout }      from "./components/Layout"
import { Login }       from "./pages/Login"
import { Vagas }       from "./pages/Vagas"
import { VagaDetalhe } from "./pages/VagaDetalhe"
import { Candidatos }  from "./pages/Candidatos"
import api             from "./api"
import "./index.css"

function App() {
  const [usuario, setUsuario] = useState(() => {
    // Recupera o usuário do localStorage na inicialização
    const salvo = localStorage.getItem("usuario")
    return salvo ? JSON.parse(salvo) : null
  })

  useEffect(() => {
    // Restaura o token nas requisições se já estava logado
    const token = localStorage.getItem("token")
    if (token) {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`
    }
  }, [])

  function handleLogin(u) {
    setUsuario(u)
  }

  function handleLogout() {
    setUsuario(null)
    delete api.defaults.headers.common["Authorization"]
  }

  // Rota protegida — redireciona para login se não autenticado
  function Protegida({ children }) {
    if (!usuario) return <Navigate to="/login" replace />
    return (
      <Layout usuario={usuario} onLogout={handleLogout}>
        {children}
      </Layout>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={
          usuario ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />
        }/>
        <Route path="/" element={
          <Protegida><Vagas /></Protegida>
        }/>
        <Route path="/vagas/:id" element={
          <Protegida><VagaDetalhe /></Protegida>
        }/>
        <Route path="/candidatos" element={
          <Protegida><Candidatos /></Protegida>
        }/>
        <Route path="*" element={<Navigate to="/" replace />}/>
      </Routes>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)