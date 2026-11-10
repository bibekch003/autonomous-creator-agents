import { useEffect, useState } from 'react'
import {
  Bot, CheckCircle2, ChevronDown, Play, RefreshCw, ShieldQuestion, XCircle,
} from 'lucide-react'
import {
  Badge, Button, Card, ErrorNote, Field, Input, PageHeader, Progress, Spinner, StatusBadge,
} from '../components/ui'
import { api } from '../services/api'
import type { AgentInfo, AgentTask } from '../types'

export default function Agents() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const [comment, setComment] = useState('')

  const load = async () => {
    try {
      const [a, t] = await Promise.all([api.listAgents(), api.listTasks(30)])
      setAgents(a)
      setTasks(t)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the agents.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const run = async (name: string) => {
    setBusy(name)
    setError('')
    try {
      const params: Record<string, unknown> = {}
      if (name === 'community') {
        if (!comment.trim()) {
          setError('Type a comment first — the Community agent drafts a reply to it.')
          setBusy('')
          return
        }
        params.comment = comment
      }
      const task = await api.runAgent({ agent: name, params })
      setOpen(task.id)
      if (name === 'community') setComment('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The agent could not run.')
    } finally {
      setBusy('')
    }
  }

  const decide = async (task: AgentTask, approve: boolean) => {
    setBusy(task.id)
    try {
      await api.approveTask(task.id, approve, approve ? 'Approved in the control centre.' : 'Rejected.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record the decision.')
    } finally {
      setBusy('')
    }
  }

  if (loading) return <Spinner label="Loading the control centre…" />

  const pending = tasks.filter((t) => t.status === 'awaiting_approval')

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<Bot size={18} />}
        title="AI Agents Control Centre"
        subtitle="Six specialised agents and one orchestrator. Every run is logged with its inputs, output and errors."
        actions={<Button variant="ghost" onClick={load}><RefreshCw size={15} /> Refresh</Button>}
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      {pending.length > 0 && (
        <Card className="mb-5 !border-amber-400/30">
          <p className="mb-1 flex items-center gap-2 font-semibold text-amber-200">
            <ShieldQuestion size={16} /> Waiting for your approval ({pending.length})
          </p>
          <p className="mb-3 text-sm text-muted">
            These drafts are never published automatically. Review the output, then approve or reject.
          </p>
          <div className="space-y-3">
            {pending.map((t) => (
              <div key={t.id} className="rounded-xl border border-ink-600 bg-ink-850/60 p-3.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge tone="violet">{t.agent}</Badge>
                    <span className="text-xs text-slate-500">{new Date(t.created_at).toLocaleString()}</span>
                  </div>
                  <div className="flex gap-2">
                    <Button className="!px-3 !py-1.5 text-xs" onClick={() => decide(t, true)} loading={busy === t.id}>
                      <CheckCircle2 size={13} /> Approve
                    </Button>
                    <Button variant="danger" className="!px-3 !py-1.5 text-xs" onClick={() => decide(t, false)}>
                      <XCircle size={13} /> Reject
                    </Button>
                  </div>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-200">
                  {String((t.output_data as { draft?: string }).draft ?? '—')}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {agents.map((a) => (
          <Card key={a.name} hover className="flex flex-col">
            <div className="flex items-start justify-between gap-2">
              <p className="font-semibold text-slate-100">{a.title}</p>
              {a.requires_approval && <Badge tone="amber">approval</Badge>}
            </div>
            <p className="mt-1.5 flex-1 text-sm leading-relaxed text-muted">{a.description}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {a.capabilities.slice(0, 3).map((c) => <span key={c} className="chip">{c}</span>)}
            </div>
            <div className="mt-3 space-y-2">
              {a.name === 'community' && (
                <Field label="Comment to reply to">
                  <Input value={comment} onChange={(e) => setComment(e.target.value)}
                         placeholder="How did you measure this?" />
                </Field>
              )}
              <Button variant="ghost" className="w-full" onClick={() => run(a.name)} loading={busy === a.name}>
                <Play size={14} /> Run agent
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-7">
        <h2 className="heading mb-3">Execution log</h2>
        {tasks.length === 0 ? (
          <Card><p className="text-sm text-muted">No agent has run yet.</p></Card>
        ) : (
          <div className="space-y-2">
            {tasks.map((t) => (
              <Card key={t.id} className="!p-0 overflow-hidden">
                <button
                  onClick={() => setOpen(open === t.id ? null : t.id)}
                  className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 text-left hover:bg-ink-750/40"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <ChevronDown size={15} className={`shrink-0 text-slate-500 transition ${open === t.id ? 'rotate-180' : ''}`} />
                    <span className="font-medium text-slate-100">{t.agent}</span>
                    <span className="chip">{t.task_type}</span>
                    {t.attempts > 1 && <span className="chip">attempt {t.attempts}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="hidden text-xs text-slate-500 sm:inline">
                      {new Date(t.created_at).toLocaleTimeString()}
                    </span>
                    <StatusBadge status={t.status} />
                  </div>
                </button>

                {open === t.id && (
                  <div className="border-t border-ink-600/70 bg-ink-850/40 px-4 py-3.5">
                    <Progress value={t.progress} />
                    {t.error && <div className="mt-3"><ErrorNote>{t.error}</ErrorNote></div>}
                    <div className="mt-3 space-y-1.5">
                      {t.logs.map((log) => (
                        <div key={log.id} className="flex gap-2 font-mono text-xs">
                          <span className="shrink-0 text-slate-600">
                            {new Date(log.created_at).toLocaleTimeString()}
                          </span>
                          <span className={
                            log.level === 'error' ? 'text-rose-300'
                              : log.level === 'warning' ? 'text-amber-300' : 'text-slate-300'
                          }>
                            {log.message}
                          </span>
                        </div>
                      ))}
                      {t.logs.length === 0 && <p className="text-xs text-slate-500">No log entries.</p>}
                    </div>
                    {Object.keys(t.output_data ?? {}).length > 0 && (
                      <details className="mt-3">
                        <summary className="cursor-pointer text-xs text-cyan-300">Agent output (JSON)</summary>
                        <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-ink-600 bg-ink-900 p-3 text-[11px] leading-relaxed text-slate-300">
{JSON.stringify(t.output_data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
