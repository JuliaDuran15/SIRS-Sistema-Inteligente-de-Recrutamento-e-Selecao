import { useState, useEffect, useRef } from "react"
import { Link, useLocation } from "react-router-dom"
import logo from "../assets/logo.png"

function useTheme() {
  const [light, setLight] = useState(
    () => localStorage.getItem("theme") === "light"
  )
  useEffect(() => {
    if (light) {
      document.documentElement.classList.add("light")
      localStorage.setItem("theme", "light")
    } else {
      document.documentElement.classList.remove("light")
      localStorage.setItem("theme", "dark")
    }
  }, [light])
  return [light, setLight]
}

export function Layout({ children, usuario, onLogout }) {
  const loc              = useLocation()
  const [light, setLight] = useTheme()
  const [menuAberto, setMenuAberto] = useState(false)
  const menuRef          = useRef(null)

  const nav = [
    { path: "/",           label: "Vagas"      },
    { path: "/candidatos", label: "Candidatos" },
    { path: "/dashboard",  label: "Dashboard"  },
    ...(usuario?.papel === "admin" ? [{ path: "/admin", label: "Usuários" }] : []),
  ]

  // Fecha ao clicar fora
  useEffect(() => {
    function onClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuAberto(false)
      }
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [])

  // Fecha ao navegar
  useEffect(() => { setMenuAberto(false) }, [loc.pathname])

  const navLinkClass = (path) =>
    `block px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
      loc.pathname === path
        ? "text-brand-black"
        : "text-brand-pale/70 hover:text-brand-cloud hover:bg-white/5"
    }`

  const navLinkStyle = (path) =>
    loc.pathname === path
      ? { background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }
      : undefined

  return (
    <div className="min-h-screen">
      <header
        className="sticky top-0 z-20 border-b"
        style={{
          background    : "var(--s-header)",
          borderColor   : "var(--b-card)",
          backdropFilter: "blur(18px)",
        }}
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between gap-4">

          {/* Brand */}
          <Link to="/" className="flex items-center gap-2.5 flex-shrink-0">
            <img src={logo} alt="SIRS"
              className="h-9 w-auto object-contain rounded-lg" />
            <span className="text-xs font-medium leading-tight"
              style={{ color: "var(--t-sub)" }}>
              Recrutamento<br />Inteligente
            </span>
          </Link>

          {/* Nav desktop — visível a partir de 860px */}
          <nav className="hidden min-[860px]:flex items-center gap-0.5">
            {nav.map(n => (
              <Link key={n.path} to={n.path}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold tracking-wider transition-all whitespace-nowrap ${
                  loc.pathname === n.path
                    ? "text-brand-black"
                    : "text-brand-pale/55 hover:text-brand-cloud hover:bg-brand-teal/30"
                }`}
                style={loc.pathname === n.path
                  ? { background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }
                  : undefined}>
                {n.label.toUpperCase()}
              </Link>
            ))}
          </nav>

          {/* Ações direita */}
          <div className="flex items-center gap-2 flex-shrink-0">

            {/* Tema */}
            <button
              onClick={() => setLight(v => !v)}
              title={light ? "Tema escuro" : "Tema claro"}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
              style={{ background: "var(--s-pill)", border: "1px solid var(--b-subtle)" }}>
              {light ? "🌙" : "☀️"}
            </button>

            {/* Usuário */}
            {usuario && (
              <div className="flex items-center gap-2 pl-2 hidden min-[860px]:flex"
                style={{ borderLeft: "1px solid var(--b-normal)" }}>
                <Link to="/perfil" className="flex items-center gap-2 group">
                  <div className="hidden lg:block text-right">
                    <p className="text-xs font-semibold text-brand-cloud leading-none group-hover:text-brand-sky transition-colors">
                      {usuario.nome}
                    </p>
                    <p className="text-xs text-brand-pale/45 mt-0.5 capitalize">{usuario.papel}</p>
                  </div>
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
                    <span className="text-xs font-bold text-brand-black">
                      {usuario.nome.charAt(0).toUpperCase()}
                    </span>
                  </div>
                </Link>
                <button onClick={onLogout}
                  className="text-xs text-brand-pale/40 hover:text-brand-sky font-medium transition-colors">
                  Sair
                </button>
              </div>
            )}

            <div className="relative min-[860px]:hidden" ref={menuRef}>
              <button
                onClick={() => setMenuAberto(v => !v)}
                className="w-9 h-9 rounded-xl flex flex-col items-center justify-center gap-1.5 transition-all"
                style={{
                  background: menuAberto ? "rgba(26,139,191,0.2)" : "var(--s-pill)",
                  border    : "1px solid var(--b-normal)",
                }}>
                <span className="block w-4 h-0.5 rounded-full transition-all"
                  style={{
                    background: "var(--color-brand-sky)",
                    transform : menuAberto ? "translateY(4px) rotate(45deg)" : "none",
                  }} />
                <span className="block w-4 h-0.5 rounded-full transition-all"
                  style={{
                    background: "var(--color-brand-sky)",
                    opacity   : menuAberto ? 0 : 1,
                  }} />
                <span className="block w-4 h-0.5 rounded-full transition-all"
                  style={{
                    background: "var(--color-brand-sky)",
                    transform : menuAberto ? "translateY(-8px) rotate(-45deg)" : "none",
                  }} />
              </button>

              {/* Dropdown */}
              {menuAberto && (
                <div
                  className="absolute right-0 top-full mt-2 w-56 rounded-2xl py-2 z-30 shadow-xl"
                  style={{
                    background  : "var(--s-header)",
                    border      : "1px solid var(--b-card)",
                    backdropFilter: "blur(24px)",
                  }}>

                  {/* Links de nav */}
                  <div className="px-2 pb-2 border-b" style={{ borderColor: "var(--b-subtle)" }}>
                    {nav.map(n => (
                      <Link key={n.path} to={n.path}
                        className={navLinkClass(n.path)}
                        style={navLinkStyle(n.path)}>
                        {n.label}
                      </Link>
                    ))}
                  </div>

                  {/* Usuário */}
                  {usuario && (
                    <div className="px-2 pt-2 space-y-1">
                      <Link to="/perfil" className="flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all hover:bg-white/5">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}>
                          <span className="text-xs font-bold text-brand-black">
                            {usuario.nome.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-brand-cloud truncate">{usuario.nome}</p>
                          <p className="text-xs text-brand-pale/45 capitalize">{usuario.papel}</p>
                        </div>
                      </Link>
                      <button onClick={onLogout}
                        className="w-full text-left px-4 py-2.5 rounded-xl text-sm font-semibold transition-all hover:bg-white/5"
                        style={{ color: "#FCA5A5" }}>
                        Sair
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-8 py-10">
        {children}
      </main>
    </div>
  )
}
