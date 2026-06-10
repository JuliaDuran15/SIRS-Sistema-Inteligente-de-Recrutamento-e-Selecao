import { createContext, useContext, useState } from "react"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(() => {
    try { return JSON.parse(localStorage.getItem("usuario")) } catch { return null }
  })

  function login(token, userData) {
    localStorage.setItem("token", token)
    localStorage.setItem("usuario", JSON.stringify(userData))
    setUsuario(userData)
  }

  function logout() {
    localStorage.removeItem("token")
    localStorage.removeItem("usuario")
    setUsuario(null)
  }

  return (
    <AuthContext.Provider value={{ usuario, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext)
