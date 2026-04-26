import { Link, useLocation } from "react-router-dom"
import logo from "../assets/logo.png"

export function Layout({ children, usuario, onLogout }) {
  const loc = useLocation()

  const nav = [
    { path: "/",           label: "VAGAS",      papeis: null },
    { path: "/candidatos", label: "CANDIDATOS", papeis: null },
    { path: "/admin",      label: "ADMIN",      papeis: ["admin"] },
  ].filter(n => !n.papeis || n.papeis.includes(usuario?.papel))

  return (
    <div className="min-h-screen">
      <header
        className="sticky top-0 z-10 border-b"
        style={{
          background: "rgba(7, 17, 26, 0.88)",
          borderColor: "rgba(77, 200, 232, 0.12)",
          backdropFilter: "blur(18px)",
        }}
      >
        <div className="max-w-6xl mx-auto px-8 h-16 flex items-center justify-between">

          {/* Brand */}
          <div className="flex items-center gap-3">
            <img src={logo} alt="SIRS"
              className="h-10 w-auto object-contain rounded-lg flex-shrink-0" />
            <span className="hidden sm:inline text-xs font-medium"
              style={{ color: "rgba(125, 216, 240, 0.45)" }}>
              Recrutamento Inteligente
            </span>
          </div>

          {/* Nav + user */}
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1">
              {nav.map(n => (
                <Link
                  key={n.path}
                  to={n.path}
                  className={`px-4 py-2 rounded-lg text-xs font-bold tracking-widest transition-all ${
                    loc.pathname === n.path
                      ? "text-brand-black"
                      : "text-brand-pale/55 hover:text-brand-cloud hover:bg-brand-teal/30"
                  }`}
                  style={loc.pathname === n.path
                    ? { background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }
                    : undefined}
                >
                  {n.label}
                </Link>
              ))}
            </nav>

            {usuario && (
              <div className="flex items-center gap-3 pl-3 ml-1"
                style={{ borderLeft: "1px solid rgba(77, 200, 232, 0.15)" }}>
                <Link to="/perfil" className="flex items-center gap-2 group">
                  <div className="hidden sm:block text-right">
                    <p className="text-xs font-semibold text-brand-cloud leading-none group-hover:text-brand-sky transition-colors">
                      {usuario.nome}
                    </p>
                    <p className="text-xs text-brand-pale/45 mt-0.5 capitalize">{usuario.papel}</p>
                  </div>
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 group-hover:opacity-80 transition-opacity"
                    style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
                    <span className="text-xs font-bold text-brand-black">
                      {usuario.nome.charAt(0).toUpperCase()}
                    </span>
                  </div>
                </Link>
                <button onClick={onLogout}
                  className="text-xs text-brand-pale/45 hover:text-brand-sky font-medium transition-colors">
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
