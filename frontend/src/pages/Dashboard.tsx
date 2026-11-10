import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart3, Bot, CheckCircle2, Clock, Film, FolderKanban, Image, LayoutDashboard,
  Plus, Scissors, Upload, Video,
} from 'lucide-react'
import { Card, EmptyState, ErrorNote, PageHeader, Spinner, Stat, StatusBadge, timecode } from '../components/ui'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import type { AnalyticsDetail, Project } from '../types'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<AnalyticsDetail | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [detail, projectList] = await Promise.all([api.analyticsDetail(), api.listProjects()])
        if (!alive) return
        setStats(detail)
        setProjects(projectList)
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : 'Could not load your dashboard.')
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  if (loading) return <Spinner label="Loading your studio…" />

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<LayoutDashboard size={18} />}
        title={`Welcome back, ${user?.name?.split(' ')[0] ?? 'creator'}`}
        subtitle="Your production numbers, straight from this application's own database."
        actions={
          <>
            <Link to="/app/projects" className="btn-ghost"><FolderKanban size={15} /> Projects</Link>
            <Link to="/app/projects" className="btn-primary"><Plus size={15} /> New project</Link>
          </>
        }
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Projects" value={stats?.projects ?? 0} icon={<FolderKanban size={16} />} />
        <Stat label="Videos" value={stats?.videos ?? 0}
              hint={`${stats?.videos_processed ?? 0} processed`} icon={<Video size={16} />} />
        <Stat label="Clips" value={stats?.clips ?? 0}
              hint={`${stats?.clips_ready ?? 0} ready to download`} icon={<Scissors size={16} />} />
        <Stat label="Thumbnails" value={stats?.thumbnails ?? 0} icon={<Image size={16} />} />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <p className="font-semibold text-slate-100">Clips created this week</p>
            <span className="chip">{timecode(stats?.total_clip_seconds ?? 0)} total</span>
          </div>
          <div className="flex h-40 items-end gap-2">
            {(stats?.activity ?? []).map((d) => {
              const max = Math.max(1, ...(stats?.activity ?? []).map((x) => x.value))
              return (
                <div key={d.label} className="flex flex-1 flex-col items-center gap-2">
                  <div className="flex w-full flex-1 items-end">
                    <div
                      className="w-full rounded-t-lg bg-gradient-to-t from-cyan-500/40 to-cyan-300/80 transition-all"
                      style={{ height: `${(d.value / max) * 100}%`, minHeight: d.value ? 6 : 2 }}
                      title={`${d.value} clips`}
                    />
                  </div>
                  <span className="text-[10px] uppercase tracking-wide text-slate-500">{d.label}</span>
                </div>
              )
            })}
          </div>
          <p className="mt-3 text-xs text-slate-500">{stats?.source_note}</p>
        </Card>

        <Card>
          <p className="mb-3 font-semibold text-slate-100">Agent activity</p>
          <div className="space-y-2.5 text-sm">
            <Row icon={<CheckCircle2 size={15} className="text-emerald-300" />} label="Tasks succeeded" value={stats?.tasks_succeeded ?? 0} />
            <Row icon={<Clock size={15} className="text-amber-300" />} label="Tasks failed" value={stats?.tasks_failed ?? 0} />
            <Row icon={<Film size={15} className="text-cyan-300" />} label="Video processed" value={`${Math.round(stats?.total_video_seconds ?? 0)}s`} />
            <Row icon={<BarChart3 size={15} className="text-violet-300" />} label="Storage used" value={`${stats?.storage_mb ?? 0} MB`} />
          </div>
          <Link to="/app/agents" className="mt-4 flex items-center gap-1.5 text-sm text-cyan-300 hover:underline">
            <Bot size={14} /> Open the agent control centre
          </Link>
        </Card>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="heading">Recent projects</h2>
          <Link to="/app/projects" className="text-sm text-cyan-300 hover:underline">View all</Link>
        </div>
        {projects.length === 0 ? (
          <EmptyState
            icon={<Upload size={26} />}
            title="No projects yet"
            body="Create a project, upload a long take, and the agents will find the moments worth clipping."
            action={<Link to="/app/projects" className="btn-primary"><Plus size={15} /> Create your first project</Link>}
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {projects.slice(0, 6).map((p) => (
              <Link key={p.id} to={`/app/projects`} className="card card-hover block p-4">
                <p className="truncate font-medium text-slate-100">{p.name}</p>
                <p className="mt-0.5 truncate text-xs text-slate-500">{p.description || 'No description'}</p>
                <div className="mt-3 flex items-center gap-2">
                  <StatusBadge status={p.status} />
                  <span className="chip">{p.video_count} videos</span>
                  <span className="chip">{p.clip_count} clips</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-muted">{icon}{label}</span>
      <span className="font-medium text-slate-100">{value}</span>
    </div>
  )
}
