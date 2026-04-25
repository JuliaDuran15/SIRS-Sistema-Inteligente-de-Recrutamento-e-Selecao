import { Link, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"

const nav = [
  { path: "/",           label: "Vagas"      },
  { path: "/candidatos", label: "Candidatos" },
]

export function Layout({ children }) {
  const loc      = useLocation()
  const navigate = useNavigate()
  const { usuario, logout } = useAuth()

  function handleLogout() {
    logout()
    navigate("/login")
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-8 h-16 flex items-center justify-between">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)" }}>
              <span className="text-white font-mono text-sm font-bold">S</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 text-sm tracking-tight">SIRS</span>
              <span className="hidden sm:inline text-slate-300">·</span>
              <span className="hidden sm:inline text-slate-400 text-xs font-medium">
                Recrutamento Inteligente
              </span>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <nav className="flex items-center gap-1">
              {nav.map(n => (
                <Link key={n.path} to={n.path}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                    loc.pathname === n.path
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
                  }`}>
                  {n.label}
                </Link>
              ))}
            </nav>

            {usuario && (
              <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
                <div className="hidden sm:block text-right">
                  <p className="text-xs font-semibold text-slate-700 leading-none">{usuario.nome}</p>
                  <p className="text-xs text-slate-400 mt-0.5 capitalize">{usuario.papel}</p>
                </div>
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm"
                  style={{ background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)" }}>
                  <span className="text-white text-xs font-bold">
                    {usuario.nome.charAt(0).toUpperCase()}
                  </span>
                </div>
                <button onClick={handleLogout}
                  className="text-xs text-slate-400 hover:text-indigo-600 transition-colors font-medium">
                  Sair
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-10">
        {children}
      </main>
    </div>
  )
}
