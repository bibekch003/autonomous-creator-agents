/** Small, reusable UI primitives. No component library, no extra dependency. */
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'

export function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ')
}

export function Card({ children, className, hover }: { children: ReactNode; className?: string; hover?: boolean }) {
  return <div className={cx('card p-5', hover && 'card-hover', className)}>{children}</div>
}

export function PageHeader({ title, subtitle, actions, icon }: {
  title: string
  subtitle?: string
  actions?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon && (
          <div className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
            {icon}
          </div>
        )}
        <div>
          <h1 className="heading text-xl">{title}</h1>
          {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Button({ children, className, variant = 'primary', loading, ...rest }: {
  children: ReactNode
  variant?: 'primary' | 'ghost' | 'danger'
  loading?: boolean
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = variant === 'primary' ? 'btn-primary' : variant === 'danger' ? 'btn-danger' : 'btn-ghost'
  return (
    <button className={cx(styles, className)} disabled={rest.disabled || loading} {...rest}>
      {loading && <Loader2 size={15} className="animate-spin" />}
      {children}
    </button>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  )
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx('input', props.className)} />
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx('input resize-y', props.className)} />
}

export function Select({ value, onChange, options, className }: {
  value: string
  onChange: (v: string) => void
  options: Array<{ value: string; label: string }>
  className?: string
}) {
  return (
    <select className={cx('input', className)} value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-ink-850">
          {o.label}
        </option>
      ))}
    </select>
  )
}

export function Badge({ children, tone = 'default' }: {
  children: ReactNode
  tone?: 'default' | 'cyan' | 'violet' | 'green' | 'amber' | 'rose'
}) {
  const tones: Record<string, string> = {
    default: 'border-ink-500 bg-ink-750 text-slate-300',
    cyan: 'border-cyan-400/30 bg-cyan-400/10 text-cyan-300',
    violet: 'border-violet-400/30 bg-violet-400/10 text-violet-300',
    green: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
    amber: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
    rose: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
  }
  return (
    <span className={cx('inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide', tones[tone])}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, 'default' | 'cyan' | 'green' | 'amber' | 'rose'> = {
    ready: 'green', succeeded: 'green', uploaded: 'cyan', analysing: 'amber', rendering: 'amber',
    queued: 'default', running: 'cyan', awaiting_approval: 'violet' as never, failed: 'rose', rejected: 'rose',
  }
  return <Badge tone={map[status] ?? 'default'}>{status.replace(/_/g, ' ')}</Badge>
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted">
      <Loader2 size={16} className="animate-spin text-cyan-300" />
      {label ?? 'Working…'}
    </div>
  )
}

export function EmptyState({ title, body, action, icon }: {
  title: string
  body: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-600 bg-ink-850/40 px-6 py-14 text-center">
      {icon && <div className="mb-3 text-ink-500">{icon}</div>}
      <p className="text-base font-semibold text-slate-200">{title}</p>
      <p className="mt-1.5 max-w-md text-sm text-muted">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2.5 text-sm text-rose-200">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <span>{children}</span>
    </div>
  )
}

export function Progress({ value, tone = 'cyan' }: { value: number; tone?: 'cyan' | 'violet' }) {
  const bar = tone === 'cyan' ? 'from-cyan-400 to-cyan-300' : 'from-violet-500 to-violet-400'
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
      <div className={cx('h-full rounded-full bg-gradient-to-r transition-all duration-300', bar)}
           style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

export function Stat({ label, value, hint, icon }: { label: string; value: ReactNode; hint?: string; icon?: ReactNode }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-muted">{label}</span>
        {icon && <span className="text-cyan-300/80">{icon}</span>}
      </div>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-ink-600 bg-ink-850/60 px-3.5 py-2.5 text-xs leading-relaxed text-muted">{children}</p>
}

export function timecode(seconds: number) {
  const s = Math.max(0, Math.floor(seconds))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export function bytes(mb: number | null | undefined) {
  if (!mb) return '—'
  return mb >= 1 ? `${mb.toFixed(2)} MB` : `${Math.round(mb * 1024)} KB`
}
