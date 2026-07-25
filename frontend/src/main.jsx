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
import { Auditoria }       from "./pages/Auditoria"
import { ConfigEmpresa }  from "./pages/ConfigEmpresa"
import api, { getConfig }   from "./api"
import "./index.css"

function Protegida({ children, apenasAdmin, apenasAdminOuRH, usuario, onLogout }) {
  if (!usuario) return <Navigate to="/login" replace />
  if (apenasAdmin && usuario.papel !== "admin") return <Navigate to="/" replace />
  if (apenasAdminOuRH && usuario.papel !== "admin" && usuario.papel !== "rh") return <Navigate to="/" replace />
  return <Layout usuario={usuario} onLogout={onLogout}>{children}</Layout>
}

export function App() {
  const [usuario, setUsuario] = useState(() => {
    const salvo = localStorage.getItem("usuario")
    return salvo ? JSON.parse(salvo) : null
  })

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (token) {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`
      getConfig()
        .then(r => {
          const nome = r.data.nome_empresa
          localStorage.setItem("config_nome_empresa", nome)
          window.dispatchEvent(new CustomEvent("config_empresa_atualizada", { detail: nome }))
        })
        .catch(() => {})
    }
  }, [usuario])

  function handleLogin(u) { setUsuario(u) }
  function handleLogout() {
    setUsuario(null)
    delete api.defaults.headers.common["Authorization"]
  }

  const p = { usuario, onLogout: handleLogout }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={
          usuario ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />
        }/>
        <Route path="/esqueceu-senha" element={<EsqueceuSenha />} />
        <Route path="/resetar-senha"  element={<ResetarSenha />} />
        <Route path="/" element={
          <Protegida {...p}><Vagas usuario={usuario} /></Protegida>
        }/>
        <Route path="/vagas/:id" element={
          <Protegida {...p}><VagaDetalhe usuario={usuario} /></Protegida>
        }/>
        <Route path="/vagas/:id/kanban" element={
          <Protegida {...p}><KanbanVaga usuario={usuario} /></Protegida>
        }/>
        <Route path="/candidatos" element={
          <Protegida {...p}><Candidatos /></Protegida>
        }/>
        <Route path="/candidatos/:id" element={
          <Protegida {...p}><CandidatoDetalhe usuario={usuario} /></Protegida>
        }/>
        <Route path="/candidaturas/:candidaturaId/entrevistas" element={
          <Protegida {...p}><EntrevistaDetalhe usuario={usuario} /></Protegida>
        }/>
        <Route path="/dashboard" element={
          <Protegida {...p}><Dashboard /></Protegida>
        }/>
        <Route path="/admin" element={
          <Protegida {...p} apenasAdmin><AdminUsuarios /></Protegida>
        }/>
        <Route path="/auditoria" element={
          <Protegida {...p} apenasAdminOuRH><Auditoria usuario={usuario} /></Protegida>
        }/>
        <Route path="/configuracoes" element={
          <Protegida {...p} apenasAdmin><ConfigEmpresa /></Protegida>
        }/>
        <Route path="/perfil" element={
          <Protegida {...p}><Perfil usuario={usuario} /></Protegida>
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
