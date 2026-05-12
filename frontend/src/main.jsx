import React, { useState, useEffect } from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Layout }            from "./components/Layout"
import { Login }             from "./pages/Login"
import { Vagas }             from "./pages/Vagas"
import { VagaDetalhe }       from "./pages/VagaDetalhe"
import { KanbanVaga }        from "./pages/KanbanVaga"
import { Candidatos }        from "./pages/Candidatos"
import { EntrevistaDetalhe } from "./pages/EntrevistaDetalhe"
import { AdminUsuarios }     from "./pages/AdminUsuarios"
import { CandidatoDetalhe } from "./pages/CandidatoDetalhe"
import { Perfil }           from "./pages/Perfil"
import { Dashboard }        from "./pages/Dashboard"
import { EsqueceuSenha }   from "./pages/EsqueceuSenha"
import { ResetarSenha }    from "./pages/ResetarSenha"
import api                   from "./api"
import "./index.css"

function App() {
  const [usuario, setUsuario] = useState(() => {
    const salvo = localStorage.getItem("usuario")
    return salvo ? JSON.parse(salvo) : null
  })

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (token) api.defaults.headers.common["Authorization"] = `Bearer ${token}`
  }, [])

  function handleLogin(u) { setUsuario(u) }
  function handleLogout() {
    setUsuario(null)
    delete api.defaults.headers.common["Authorization"]
  }

  function Protegida({ children, apenasAdmin }) {
    if (!usuario) return <Navigate to="/login" replace />
    if (apenasAdmin && usuario.papel !== "admin") return <Navigate to="/" replace />
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
        <Route path="/esqueceu-senha" element={<EsqueceuSenha />} />
        <Route path="/resetar-senha"  element={<ResetarSenha />} />
        <Route path="/" element={
          <Protegida><Vagas usuario={usuario} /></Protegida>
        }/>
        <Route path="/vagas/:id" element={
          <Protegida><VagaDetalhe usuario={usuario} /></Protegida>
        }/>
        <Route path="/vagas/:id/kanban" element={
          <Protegida><KanbanVaga usuario={usuario} /></Protegida>
        }/>
        <Route path="/candidatos" element={
          <Protegida><Candidatos /></Protegida>
        }/>
        <Route path="/candidatos/:id" element={
          <Protegida><CandidatoDetalhe usuario={usuario} /></Protegida>
        }/>
        <Route path="/candidaturas/:candidaturaId/entrevistas" element={
          <Protegida><EntrevistaDetalhe usuario={usuario} /></Protegida>
        }/>
        <Route path="/dashboard" element={
          <Protegida><Dashboard /></Protegida>
        }/>
        <Route path="/admin" element={
          <Protegida apenasAdmin><AdminUsuarios /></Protegida>
        }/>
        <Route path="/perfil" element={
          <Protegida><Perfil usuario={usuario} /></Protegida>
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
