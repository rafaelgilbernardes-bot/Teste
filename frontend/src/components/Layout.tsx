import { NavLink, Outlet } from 'react-router-dom'

const nav = [
  { to: '/faturamento',   label: 'Faturamento' },
  { to: '/produtividade', label: 'Produtividade' },
  { to: '/rentabilidade', label: 'Rentabilidade' },
  { to: '/orcamento',     label: 'Orçado vs Realizado' },
  { to: '/alertas',       label: 'Alertas' },
  { to: '/contratos',     label: 'Contratos' },
  { to: '/relatorios',    label: 'Relatórios' },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar */}
      <header className="bg-brand-700 text-white shadow">
        <div className="max-w-screen-xl mx-auto px-4 py-3 flex items-center gap-6">
          <span className="font-bold text-lg tracking-tight">CFPazziniGil — BI</span>
          <nav className="flex gap-1 flex-wrap">
            {nav.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded text-sm transition ${
                    isActive
                      ? 'bg-white/20 font-semibold'
                      : 'hover:bg-white/10'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-screen-xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
