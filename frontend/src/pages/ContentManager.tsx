import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Check, Copy, Sparkles, TextCursorInput } from 'lucide-react'
import {
  Badge, Button, Card, EmptyState, ErrorNote, Field, Note, PageHeader, Select, Spinner,
} from '../components/ui'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import type { Clip, SeoResult, Video } from '../types'

export default function ContentManager() {
  const { videoId = '' } = useParams()
  const { meta, settings } = useAuth()
  const [video, setVideo] = useState<Video | null>(null)
  const [clips, setClips] = useState<Clip[]>([])
  const [clipId, setClipId] = useState('')
  const [platform, setPlatform] = useState(settings?.default_platform ?? 'youtube_shorts')
  const [result, setResult] = useState<SeoResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')

  useEffect(() => {
    ;(async () => {
      try {
        const [v, c] = await Promise.all([api.getVideo(videoId), api.listClips(videoId)])
        setVideo(v)
        setClips(c)
        setClipId(c[0]?.id ?? '')
        localStorage.setItem('aca:lastVideo', v.id)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not load the project.')
      } finally {
        setLoading(false)
      }
    })()
  }, [videoId])

  const generate = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.generateContent({
        clip_id: clipId || null, video_id: videoId, platform,
      })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The copy engine failed.')
    } finally {
      setBusy(false)
    }
  }

  const copy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(key)
      setTimeout(() => setCopied(''), 1500)
    } catch {
      setError('Your browser blocked clipboard access. Select the text and copy it manually.')
    }
  }

  if (loading) return <Spinner label="Loading content…" />
  if (!video) return <ErrorNote>{error || 'Video not found.'}</ErrorNote>

  const platformOptions = (meta?.platforms ?? []).map((p) => ({ value: p.key, label: p.label }))

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<TextCursorInput size={18} />}
        title="Content Manager"
        subtitle="Titles, descriptions, hashtags and per-platform copy — written from your transcript."
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      <Card className="mb-5">
        <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr_auto] lg:items-end">
          <Field label="For which clip?">
            <select className="input" value={clipId} onChange={(e) => setClipId(e.target.value)}>
              <option value="">Whole video</option>
              {clips.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} ({Math.round(c.start_s)}s → {Math.round(c.end_s)}s)
                </option>
              ))}
            </select>
          </Field>
          <Field label="Platform">
            <Select value={platform} onChange={setPlatform} options={platformOptions} />
          </Field>
          <Button onClick={generate} loading={busy}><Sparkles size={15} /> Generate copy</Button>
        </div>
        <Note>
          Copy is written by the built-in template engine unless an LLM is configured
          (current engine: <span className="text-slate-300">{meta?.engines.llm}</span>).
          Every result says which engine produced it.
        </Note>
      </Card>

      {!result ? (
        <EmptyState
          icon={<TextCursorInput size={26} />}
          title="Nothing generated yet"
          body="Pick a clip and generate three title options, a description, hashtags and platform-specific captions."
        />
      ) : (
        <div className="space-y-5">
          <Card>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold text-slate-100">Titles</p>
              <div className="flex items-center gap-2">
                <Badge tone={result.source === 'llm' ? 'violet' : 'cyan'}>{result.source}</Badge>
                <span className="chip">topic: {result.topic}</span>
              </div>
            </div>
            <div className="space-y-2">
              {result.titles.map((t, i) => (
                <div key={i} className="flex items-center justify-between gap-3 rounded-xl border border-ink-600 bg-ink-850/60 px-3.5 py-2.5">
                  <span className="text-sm text-slate-200">{t}</span>
                  <button onClick={() => copy(t, `t${i}`)} className="text-slate-400 hover:text-cyan-300" title="Copy">
                    {copied === `t${i}` ? <Check size={15} /> : <Copy size={15} />}
                  </button>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-500">{result.note}</p>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <div className="mb-2 flex items-center justify-between">
                <p className="font-semibold text-slate-100">Description</p>
                <button onClick={() => copy(result.description, 'desc')} className="text-slate-400 hover:text-cyan-300">
                  {copied === 'desc' ? <Check size={15} /> : <Copy size={15} />}
                </button>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">{result.description}</p>
            </Card>

            <Card>
              <div className="mb-2 flex items-center justify-between">
                <p className="font-semibold text-slate-100">Hashtags & caption</p>
                <button onClick={() => copy(`${result.hashtags.join(' ')}\n\n${result.caption}`, 'tags')}
                        className="text-slate-400 hover:text-cyan-300">
                  {copied === 'tags' ? <Check size={15} /> : <Copy size={15} />}
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {result.hashtags.map((h) => <span key={h} className="chip !text-cyan-300">{h}</span>)}
              </div>
              <p className="mt-3 rounded-xl border border-ink-600 bg-ink-850/60 px-3.5 py-2.5 text-sm text-slate-200">
                {result.caption}
              </p>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
