import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Download, Image as ImageIcon, Sparkles, Trash2, Upload } from 'lucide-react'
import {
  Badge, Button, Card, EmptyState, ErrorNote, Field, Input, PageHeader, Spinner,
} from '../components/ui'
import { api } from '../services/api'
import type { Clip, Thumbnail, Video } from '../types'

const STYLES = [
  { key: 'bold_lower', label: 'Bold lower third' },
  { key: 'split_band', label: 'Centre band' },
  { key: 'top_strip', label: 'Top strip' },
]

export default function ThumbnailStudio() {
  const { videoId = '' } = useParams()
  const [video, setVideo] = useState<Video | null>(null)
  const [clips, setClips] = useState<Clip[]>([])
  const [thumbs, setThumbs] = useState<Thumbnail[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [headline, setHeadline] = useState('')
  const [clipId, setClipId] = useState('')
  const [styles, setStyles] = useState<string[]>(['bold_lower', 'split_band', 'top_strip'])
  const fileRef = useRef<HTMLInputElement>(null)

  const load = async () => {
    try {
      const [v, c, t] = await Promise.all([
        api.getVideo(videoId), api.listClips(videoId), api.listThumbnails({ video_id: videoId }),
      ])
      setVideo(v)
      setClips(c)
      setThumbs(t)
      if (!headline) setHeadline(v.original_name.replace(/\.[^.]+$/, '').slice(0, 60))
      localStorage.setItem('aca:lastVideo', v.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the studio.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [videoId]) // eslint-disable-line react-hooks/exhaustive-deps

  const render = async () => {
    setBusy(true)
    setError('')
    try {
      await api.renderThumbnails({
        video_id: videoId, clip_id: clipId || null, headline,
        styles, at_seconds: clips.find((c) => c.id === clipId)?.start_s ?? 0.5,
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rendering failed.')
    } finally {
      setBusy(false)
    }
  }

  const upload = async (file: File) => {
    setBusy(true)
    setError('')
    try {
      await api.uploadThumbnail(file, { video_id: videoId, clip_id: clipId, headline })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const remove = async (t: Thumbnail) => {
    if (!confirm('Delete this thumbnail?')) return
    try {
      await api.deleteThumbnail(t.id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete it.')
    }
  }

  if (loading) return <Spinner label="Loading thumbnails…" />
  if (!video) return <ErrorNote>{error || 'Video not found.'}</ErrorNote>

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<ImageIcon size={18} />}
        title="Thumbnail Studio"
        subtitle="Concepts are rendered from a real frame and scored on five measured sub-scores."
        actions={
          <>
            <input ref={fileRef} type="file" accept=".jpg,.jpeg,.png,.webp" className="hidden"
                   onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            <Button variant="ghost" onClick={() => fileRef.current?.click()} disabled={busy}>
              <Upload size={15} /> Upload my own
            </Button>
          </>
        }
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      <Card className="mb-5">
        <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr_auto] lg:items-end">
          <Field label="Headline on the image">
            <Input value={headline} onChange={(e) => setHeadline(e.target.value)}
                   placeholder="Stop guessing the hook" maxLength={120} />
          </Field>
          <Field label="Frame from">
            <select className="input" value={clipId} onChange={(e) => setClipId(e.target.value)}>
              <option value="">Whole video (0.5s)</option>
              {clips.map((c) => (
                <option key={c.id} value={c.id}>{c.title} ({Math.round(c.start_s)}s)</option>
              ))}
            </select>
          </Field>
          <Button onClick={render} loading={busy}><Sparkles size={15} /> Render concepts</Button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {STYLES.map((s) => {
            const on = styles.includes(s.key)
            return (
              <button key={s.key}
                      onClick={() => setStyles((prev) => on ? prev.filter((x) => x !== s.key) : [...prev, s.key])}
                      className={`chip transition ${on ? '!border-cyan-400/50 !text-cyan-300' : 'hover:!text-slate-200'}`}>
                {s.label}
              </button>
            )
          })}
        </div>
      </Card>

      {thumbs.length === 0 ? (
        <EmptyState
          icon={<ImageIcon size={26} />}
          title="No thumbnails yet"
          body="Write a headline, choose the styles, and render. Each concept gets a score with reasons you can disagree with."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {thumbs.map((t) => (
            <Card key={t.id} className="!p-0 overflow-hidden">
              <img src={t.image_url} alt={t.headline}
                   className="w-full bg-black object-cover" style={{ aspectRatio: `${t.width}/${t.height}` }} />
              <div className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-medium text-slate-100">{t.headline || 'Untitled'}</p>
                  {t.is_uploaded
                    ? <Badge tone="violet">yours</Badge>
                    : <Badge tone="cyan">{t.score?.score ?? '—'}/100</Badge>}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {t.style} · {t.width}×{t.height}
                </p>
                {!!t.score?.reasons?.length && (
                  <ul className="mt-2 space-y-1">
                    {t.score.reasons.slice(0, 3).map((r) => (
                      <li key={r} className="text-xs text-muted">· {r}</li>
                    ))}
                  </ul>
                )}
                <div className="mt-3 flex gap-2">
                  <a href={t.image_url} download className="btn-ghost !px-3 !py-1.5 text-xs">
                    <Download size={13} /> JPG
                  </a>
                  <Button variant="danger" className="!px-2.5 !py-1.5 text-xs" onClick={() => remove(t)}>
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
