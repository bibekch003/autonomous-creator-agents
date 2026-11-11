import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  BarChart3, Bot, Film, FolderKanban, Image, LayoutDashboard, LogOut, Scissors,
  Settings as SettingsIcon, Sparkles, TextCursorInput, Video,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { cx } from './ui'

const videoScoped = (id: string | null, path: string) =>
  id ? `/app/videos/${id}/${path}` : '/app/projects'

export function Layout() {
  const { user, meta, logout } = useAuth()
  const navigate = useNavigate()
  const lastVideo = localStorage.getItem('aca:lastVideo')

  const primary = [
    { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/app/projects', label: 'My Projects', icon: FolderKanban },
    { to: lastVideo ? `/app/videos/${lastVideo}` : '/app/projects', label: 'Video Studio', icon: Video },
  ]
  const production = [
    { to: videoScoped(lastVideo, 'clips'), label: 'AI Clip Generator', icon: Scissors },
    { to: videoScoped(lastVideo, 'thumbnails'), label: 'Thumbnail Studio', icon: Image },
    { to: videoScoped(lastVideo, 'content'), label: 'Content Manager', icon: TextCursorInput },
  ]
  const system = [
    { to: '/app/agents', label: 'AI Agents', icon: Bot },
    { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/app/settings', label: 'Settings', icon: SettingsIcon },
  ]

  const onLogout = async () => {
    await logout()
    navigate('/login')
  }

  const NavGroup = ({ title, items }: { title: string; items: typeof primary }) => (
    <div className="mt-6">
      <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">{title}</p>
      <div className="space-y-1">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={label}
            to={to}
            className={({ isActive }) =>
              cx(
                'group flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition',
                isActive
                  ? 'bg-gradient-to-r from-cyan-400/15 to-violet-400/10 text-white ring-1 ring-cyan-400/25'
                  : 'text-slate-400 hover:bg-ink-750/70 hover:text-slate-100',
              )
            }
          >
            <Icon size={16} className="shrink-0" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 border-r border-ink-600/70 bg-ink-900/70 px-3 py-5 backdrop-blur lg:block">
        <div className="flex items-center gap-2.5 px-2">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-violet-500 text-ink-950">
            <Sparkles size={18} />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-white">Creator Agents</p>
            <p className="text-[11px] text-slate-500">v{meta?.version ?? '1.0.0'}</p>
          </div>
        </div>

        <NavGroup title="Workspace" items={primary} />
        <NavGroup title="Production" items={production} />
        <NavGroup title="System" items={system} />

        <div className="mt-8 rounded-xl border border-ink-600 bg-ink-850/70 p-3">
          <p className="truncate text-sm font-medium text-slate-200">{user?.name}</p>
          <p className="truncate text-xs text-slate-500">{user?.email}</p>
          <button onClick={onLogout} className="mt-2.5 flex items-center gap-1.5 text-xs text-slate-400 hover:text-rose-300">
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        {meta?.demo_mode && (
          <div className="border-b border-amber-400/25 bg-amber-400/10 px-5 py-2 text-xs text-amber-200 lg:px-8">
            <strong className="font-semibold">Demo mode.</strong> Everyone shares one account and
            no sign-in is needed. On a free hosting tier the database resets when the server
            restarts, so projects can disappear — that is the host, not a bug.
          </div>
        )}
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-ink-600/70 bg-ink-900/80 px-5 py-3 backdrop-blur lg:px-8">
          <div className="flex items-center gap-2 text-sm text-muted">
            <Film size={15} className="text-cyan-300" />
            <span className="hidden sm:inline">Your AI-powered creative production team</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="chip hidden md:inline">
              LLM: {meta?.engines.llm ?? '—'}
            </span>
            <span className="chip hidden md:inline">ASR: {meta?.engines.asr ?? '—'}</span>
            <button onClick={onLogout} className="btn-ghost !px-2.5 !py-1.5 lg:hidden" title="Sign out">
              <LogOut size={14} />
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-5 py-7 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
