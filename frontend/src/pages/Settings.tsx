import { useEffect, useState } from 'react'
import { Info, Save, Settings as SettingsIcon, ShieldCheck } from 'lucide-react'
import {
  Button, Card, ErrorNote, Field, Input, Note, PageHeader, Select, Spinner, Textarea,
} from '../components/ui'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import type { UserSettings } from '../types'

export default function SettingsPage() {
  const { meta, user, settings, setSettings } = useAuth()
  const [form, setForm] = useState<UserSettings | null>(settings)
  const [loading, setLoading] = useState(!settings)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (settings) return
    ;(async () => {
      try {
        setForm(await api.getSettings())
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load settings.')
      } finally {
        setLoading(false)
      }
    })()
  }, [settings])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form) return
    setBusy(true)
    setError('')
    setSaved(false)
    try {
      const updated = await api.updateSettings(form)
      setForm(updated)
      setSettings(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save your settings.')
    } finally {
      setBusy(false)
    }
  }

  if (loading || !form) return <Spinner label="Loading settings…" />

  const platformOptions = (meta?.platforms ?? []).map((p) => ({ value: p.key, label: p.label }))

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<SettingsIcon size={18} />}
        title="Settings"
        subtitle="Defaults for new clips, and the voice the Community agent writes in."
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      <form onSubmit={save} className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <p className="mb-4 font-semibold text-slate-100">Production defaults</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Default platform">
              <Select value={form.default_platform}
                      onChange={(v) => setForm({ ...form, default_platform: v })}
                      options={platformOptions} />
            </Field>
            <Field label="Default clip length (seconds)" hint="Between 5 and 90.">
              <Input type="number" min={5} max={90} value={form.default_clip_seconds}
                     onChange={(e) => setForm({ ...form, default_clip_seconds: Number(e.target.value) })} />
            </Field>
          </div>

          <div className="mt-4 space-y-2.5">
            <label className="flex items-center gap-2.5 text-sm text-slate-200">
              <input type="checkbox" checked={form.burn_captions} className="h-4 w-4 accent-cyan-400"
                     onChange={(e) => setForm({ ...form, burn_captions: e.target.checked })} />
              Burn captions into rendered clips
            </label>
            <label className="flex items-center gap-2.5 text-sm text-slate-200">
              <input type="checkbox" checked={form.auto_subtitles} className="h-4 w-4 accent-cyan-400"
                     onChange={(e) => setForm({ ...form, auto_subtitles: e.target.checked })} />
              Generate subtitles automatically when a transcript exists
            </label>
          </div>

          <div className="mt-4">
            <Field label="Creator persona" hint="Used by the Community agent when drafting replies.">
              <Textarea rows={3} value={form.creator_persona}
                        onChange={(e) => setForm({ ...form, creator_persona: e.target.value })} />
            </Field>
          </div>

          <div className="mt-5 flex items-center gap-3">
            <Button type="submit" loading={busy}><Save size={15} /> Save changes</Button>
            {saved && <span className="text-sm text-emerald-300">Saved.</span>}
          </div>
        </Card>

        <div className="space-y-5">
          <Card>
            <p className="mb-2 flex items-center gap-2 font-semibold text-slate-100">
              <Info size={15} className="text-cyan-300" /> Engines
            </p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between gap-2">
                <span className="text-muted">Copy engine</span>
                <span className="text-right text-slate-200">{meta?.engines.llm}</span>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-muted">Speech-to-text</span>
                <span className="text-right text-slate-200">{meta?.engines.asr}</span>
              </div>
            </div>
            <Note>
              To use a model for copy, set <code className="text-slate-300">ACA_LLM_API_KEY</code> (and
              optionally <code className="text-slate-300">ACA_LLM_BASE_URL</code>,{' '}
              <code className="text-slate-300">ACA_LLM_MODEL</code>) in your .env file. Without it the
              deterministic template engine runs and results are labelled <code className="text-slate-300">offline</code>.
            </Note>
          </Card>

          <Card>
            <p className="mb-2 flex items-center gap-2 font-semibold text-slate-100">
              <ShieldCheck size={15} className="text-emerald-300" /> Account
            </p>
            <p className="text-sm text-slate-200">{user?.name}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
            <Note>
              Your videos and clips are stored per account and served only to you. Signing out
              revokes this session on the server immediately.
            </Note>
          </Card>
        </div>
      </form>
    </div>
  )
}
