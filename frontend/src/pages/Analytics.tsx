import { useEffect, useState } from 'react'
import { BarChart3, CheckCircle2, Clock, HardDrive, Scissors, Video } from 'lucide-react'
import {
  Card, EmptyState, ErrorNote, PageHeader, Spinner, Stat, StatusBadge, timecode,
} from '../components/ui'
import { api } from '../services/api'
import type { AnalyticsDetail } from '../types'

export default function Analytics() {
  const [data, setData] = useState<AnalyticsDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    ;(async () => {
      try {
        setData(await api.analyticsDetail())
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load analytics.')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <Spinner label="Loading analytics…" />
  if (!data) return <ErrorNote>{error || 'No analytics available.'}</ErrorNote>

  const maxActivity = Math.max(1, ...data.activity.map((a) => a.value))
  const totalPlatform = Math.max(1, data.by_platform.reduce((sum, p) => sum + p.value, 0))

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<BarChart3 size={18} />}
        title="Analytics"
        subtitle="Production statistics from this application's own database."
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      <div className="mb-4 rounded-xl border border-cyan-400/25 bg-cyan-400/5 px-4 py-3 text-sm text-cyan-100">
        {data.source_note}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Videos processed" value={data.videos_processed} hint={`${data.videos} uploaded`} icon={<Video size={16} />} />
        <Stat label="Clips ready" value={data.clips_ready} hint={`${data.clips} created`} icon={<Scissors size={16} />} />
        <Stat label="Agent tasks" value={`${data.tasks_succeeded}✓ / ${data.tasks_failed}✕`} icon={<CheckCircle2 size={16} />} />
        <Stat label="Storage" value={`${data.storage_mb} MB`} icon={<HardDrive size={16} />} />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <p className="mb-4 font-semibold text-slate-100">Clips per day (last 7 days)</p>
          <div className="flex h-44 items-end gap-2">
            {data.activity.map((d) => (
              <div key={d.label} className="flex flex-1 flex-col items-center gap-2">
                <div className="flex w-full flex-1 items-end">
                  <div className="w-full rounded-t-lg bg-gradient-to-t from-violet-500/40 to-cyan-300/80"
                       style={{ height: `${(d.value / maxActivity) * 100}%`, minHeight: d.value ? 6 : 2 }}
                       title={`${d.value} clips`} />
                </div>
                <span className="text-[10px] uppercase tracking-wide text-slate-500">{d.label}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <p className="mb-4 font-semibold text-slate-100">By platform</p>
          {data.by_platform.length === 0 ? (
            <p className="text-sm text-muted">No clips yet.</p>
          ) : (
            <div className="space-y-3">
              {data.by_platform.map((p) => (
                <div key={p.label}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-slate-300">{p.label.replace(/_/g, ' ')}</span>
                    <span className="text-slate-500">{p.value}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
                    <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-violet-400"
                         style={{ width: `${(p.value / totalPlatform) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="mt-5 space-y-2 border-t border-ink-600/70 pt-4 text-sm">
            <div className="flex justify-between">
              <span className="flex items-center gap-2 text-muted"><Clock size={14} /> Video time</span>
              <span className="text-slate-200">{timecode(data.total_video_seconds)}</span>
            </div>
            <div className="flex justify-between">
              <span className="flex items-center gap-2 text-muted"><Scissors size={14} /> Clip time</span>
              <span className="text-slate-200">{timecode(data.total_clip_seconds)}</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-6">
        <h2 className="heading mb-3">Recent clips</h2>
        {data.recent.length === 0 ? (
          <EmptyState title="Nothing produced yet" body="Clips you render will appear here with their status and duration." />
        ) : (
          <Card className="!p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-600/70 text-left text-xs uppercase tracking-wider text-slate-500">
                    <th className="px-4 py-2.5 font-medium">Title</th>
                    <th className="px-4 py-2.5 font-medium">Platform</th>
                    <th className="px-4 py-2.5 font-medium">Duration</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                    <th className="px-4 py-2.5 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent.map((c) => (
                    <tr key={c.id} className="border-b border-ink-700/60 last:border-0">
                      <td className="px-4 py-2.5 text-slate-200">{c.title}</td>
                      <td className="px-4 py-2.5 text-muted">{c.platform.replace(/_/g, ' ')}</td>
                      <td className="px-4 py-2.5 text-muted">{c.duration_s}s</td>
                      <td className="px-4 py-2.5"><StatusBadge status={c.status} /></td>
                      <td className="px-4 py-2.5 text-slate-500">{new Date(c.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
