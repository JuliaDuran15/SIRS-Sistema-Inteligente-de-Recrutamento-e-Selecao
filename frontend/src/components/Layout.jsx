import { useState, useEffect } from "react"
import { Link, useLocation } from "react-router-dom"
import logo from "../assets/logo.png"
import {
  IconBriefcase, IconUsers, IconBarChart, IconCog, IconActivity,
  IconLogOut, IconSun, IconMoon, IconMenu, IconSettings,
} from "./Icons"

function useNomeEmpresa() {
  const [nome, setNome] = useState(() => localStorage.getItem("config_nome_empresa") || "SIRS")
  useEffect(() => {
    function atualizar(e) { setNome(e.detail) }
    window.addEventListener("config_empresa_atualizada", atualizar)
    return () => window.removeEventListener("config_empresa_atualizada", atualizar)
  }, [])
  return nome
}

const SIDEBAR_W = 240

// Retorna a raiz de seção à qual um pathname pertence
function getSectionRoot(path) {
  if (path.startsWith("/candidatos"))     return "/candidatos"
  if (path.startsWith("/dashboard"))      return "/dashboard"
  if (path.startsWith("/admin"))          return "/admin"
  if (path.startsWith("/auditoria"))      return "/auditoria"
  if (path.startsWith("/configuracoes"))  return "/configuracoes"
  return "/"   // Vagas: /, /vagas/*, /candidaturas/*
}

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

// eslint-disable-next-line no-unused-vars
function NavItem({ path, to, label, Icon, active, light }) {
  const activeStyle = light ? {
    background  : "rgba(18, 112, 168, 0.13)",
    color       : "#0D4F7A",
    borderLeft  : "2px solid #1270A8",
    padding     : "10px 12px 10px 10px",
    boxShadow   : "0 1px 6px rgba(18,112,168,0.10)",
  } : {
    background  : "linear-gradient(135deg, rgba(26,139,191,0.25), rgba(77,200,232,0.08))",
    color       : "#4DC8E8",
    borderLeft  : "2px solid #4DC8E8",
    padding     : "10px 12px 10px 10px",
    boxShadow   : "0 1px 8px rgba(26,139,191,0.12)",
  }

  const inactiveStyle = {
    color      : "var(--t-muted2)",
    borderLeft : "2px solid transparent",
    padding    : "10px 12px 10px 10px",
  }

  const iconColor = active
    ? (light ? "#1270A8" : "#4DC8E8")
    : "var(--t-faint2)"

  return (
    <Link
      to={to ?? path}
      className={`flex items-center gap-3 rounded-xl text-sm font-semibold transition-all duration-200 group${!active ? (light ? " hover:bg-black/5" : " hover:bg-white/5") : ""}`}
      style={active ? activeStyle : inactiveStyle}
    >
      <span
        className="flex-shrink-0 transition-all duration-200"
        style={{ color: iconColor }}
      >
        <Icon size={17} />
      </span>
      <span className={active ? "" : "group-hover:text-brand-cloud transition-colors duration-200"}>
        {label}
      </span>
    </Link>
  )
}

function SidebarContent({ nav, usuario, onLogout, light, setLight, currentSection, lastPaths, nomeEmpresa }) {
  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Logo */}
      <div className="px-5 py-5 border-b flex-shrink-0" style={{ borderColor: "var(--b-subtle)" }}>
        <Link to="/" className="flex items-center gap-3 group">
          <img src={logo} alt="SIRS" className="h-9 w-auto object-contain rounded-lg flex-shrink-0 transition-opacity group-hover:opacity-90" />
          <div className="min-w-0">
            <p className="text-sm font-bold text-brand-cloud leading-tight truncate">{nomeEmpresa}</p>
            <p className="text-xs leading-tight" style={{ color: "var(--t-sub)" }}>
              Recrutamento Inteligente
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 pt-4 space-y-0.5 overflow-y-auto">
        <p
          className="text-[10px] font-bold uppercase tracking-[0.12em] px-3 mb-3"
          style={{ color: "var(--t-faint2)" }}
        >
          Menu
        </p>
        {nav.map(n => {
          const isActive = currentSection === n.path
          return (
            <NavItem
              key={n.path}
              {...n}
              to={isActive ? n.path : (lastPaths[n.path] ?? n.path)}
              active={isActive}
              light={light}
            />
          )
        })}
      </nav>

      {/* Bottom actions */}
      <div className="p-3 border-t space-y-0.5 flex-shrink-0" style={{ borderColor: "var(--b-subtle)" }}>

        {/* Theme toggle */}
        <button
          onClick={() => setLight(v => !v)}
          className="w-full flex items-center gap-3 rounded-xl text-sm font-semibold transition-all hover:bg-white/5"
          style={{ color: "var(--t-muted2)", borderLeft: "2px solid transparent", padding: "10px 12px 10px 10px" }}
        >
          <span className="flex-shrink-0" style={{ color: "var(--t-faint2)" }}>
            {light ? <IconMoon size={17} /> : <IconSun size={17} />}
          </span>
          {light ? "Tema escuro" : "Tema claro"}
        </button>

        {/* User info */}
        {usuario && (
          <>
            <Link
              to="/perfil"
              className="w-full flex items-center gap-3 rounded-xl text-sm font-semibold transition-all hover:bg-white/5 group"
              style={{ color: "var(--t-muted2)", borderLeft: "2px solid transparent", padding: "10px 12px 10px 10px" }}
            >
              <div className="flex-shrink-0 relative">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center"
                  style={{
                    background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)",
                    boxShadow: "0 0 0 2px rgba(77,200,232,0.25)",
                  }}
                >
                  <span className="text-xs font-bold" style={{ color: "#07111A" }}>
                    {usuario.nome.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span
                  className="absolute bottom-0 right-0 w-2 h-2 rounded-full border border-current"
                  style={{ background: "#2EE8B4", borderColor: "var(--s-header)" }}
                />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-brand-cloud truncate group-hover:text-brand-sky transition-colors">
                  {usuario.nome}
                </p>
                <p className="text-xs capitalize leading-tight" style={{ color: "var(--t-sub)" }}>
                  {usuario.papel}
                </p>
              </div>
            </Link>
            <button
              onClick={onLogout}
              className="btn-sidebar-logout w-full flex items-center gap-3 rounded-xl text-sm font-semibold transition-all hover:bg-red-500/10"
              style={{ borderLeft: "2px solid transparent", padding: "10px 12px 10px 10px" }}
            >
              <span className="flex-shrink-0">
                <IconLogOut size={17} />
              </span>
              Sair da conta
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export function Layout({ children, usuario, onLogout }) {
  const loc                       = useLocation()
  const [light, setLight]         = useTheme()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [lastPaths, setLastPaths] = useState({})
  const nomeEmpresa               = useNomeEmpresa()

  // Mantém o último caminho visitado por seção de navegação
  useEffect(() => {
    const root = getSectionRoot(loc.pathname)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLastPaths(prev => ({ ...prev, [root]: loc.pathname }))
  }, [loc.pathname])

  const nav = [
    { path: "/",           label: "Vagas",      Icon: IconBriefcase },
    { path: "/candidatos", label: "Candidatos", Icon: IconUsers      },
    { path: "/dashboard",  label: "Dashboard",  Icon: IconBarChart   },
    ...(usuario?.papel === "admin"
      ? [
          { path: "/admin",         label: "Usuários",      Icon: IconCog      },
          { path: "/auditoria",     label: "Auditoria",     Icon: IconActivity },
          { path: "/configuracoes", label: "Configurações", Icon: IconSettings },
        ]
      : usuario?.papel === "rh"
      ? [
          { path: "/auditoria", label: "Histórico", Icon: IconActivity },
        ]
      : []),
  ]

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMobileOpen(false) }, [loc.pathname])

  const currentSection = getSectionRoot(loc.pathname)
  const sidebarProps = { nav, usuario, onLogout, light, setLight, currentSection, lastPaths, nomeEmpresa }

  return (
    <div className="min-h-screen flex">

      {/* Desktop sidebar — fixed */}
      <aside
        className="hidden lg:flex flex-col fixed top-0 left-0 h-screen z-[60]"
        style={{
          width          : SIDEBAR_W,
          background     : light
            ? "var(--s-header)"
            : "linear-gradient(180deg, var(--s-header) 0%, rgba(7,17,26,0.9) 100%)",
          borderRight    : "1px solid var(--b-card)",
          backdropFilter : "blur(24px)",
        }}
      >
        <SidebarContent {...sidebarProps} />
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden"
          style={{ background: "rgba(7,17,26,0.75)", backdropFilter: "blur(4px)" }}
          onClick={() => setMobileOpen(false)}
        >
          <aside
            className="h-full flex flex-col"
            style={{
              width      : SIDEBAR_W,
              background : "var(--s-header)",
              borderRight: "1px solid var(--b-card)",
            }}
            onClick={e => e.stopPropagation()}
          >
            <SidebarContent {...sidebarProps} />
          </aside>
        </div>
      )}

      {/* Main content — pushed right by sidebar on desktop */}
      <div className="sidebar-layout-main flex-1 min-w-0 flex flex-col">

        {/* Mobile topbar */}
        <header
          className="lg:hidden sticky top-0 z-20 h-14 flex items-center px-4 gap-3 border-b flex-shrink-0"
          style={{
            background    : "var(--s-header)",
            borderColor   : "var(--b-card)",
            backdropFilter: "blur(18px)",
          }}
        >
          <button
            onClick={() => setMobileOpen(true)}
            className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{
              background: "var(--s-pill)",
              border    : "1px solid var(--b-normal)",
              color     : "var(--color-brand-sky)",
            }}
          >
            <IconMenu size={18} />
          </button>
          <Link to="/" className="flex items-center gap-2">
            <img src={logo} alt="SIRS" className="h-8 w-auto object-contain rounded-lg" />
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setLight(v => !v)}
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{
                background: "var(--s-pill)",
                border    : "1px solid var(--b-subtle)",
                color     : "var(--color-brand-sky)",
              }}
            >
              {light ? <IconMoon size={14} /> : <IconSun size={14} />}
            </button>
            {usuario && (
              <Link
                to="/perfil"
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: "linear-gradient(135deg, #1A8BBF, #4DC8E8)" }}
              >
                <span className="text-xs font-bold" style={{ color: "#07111A" }}>
                  {usuario.nome.charAt(0).toUpperCase()}
                </span>
              </Link>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-8 py-8 lg:py-10">
          <div className="page-enter">
            {children}
          </div>
        </main>

      </div>
    </div>
  )
}
