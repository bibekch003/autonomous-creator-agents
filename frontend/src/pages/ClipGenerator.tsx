import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Download, Plus, Scissors, Trash2, Subtitles } from 'lucide-react'
import {
  Badge, Button, Card, EmptyState, ErrorNote, Field, Input, PageHeader, Select, Spinner,
  StatusBadge, timecode,
} from '../components/ui'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import type { Clip, Video } from '../types'

export default function ClipGenerator() {
  const { videoId = '' } = useParams()
  const [params] = useSearchParams()
  const { meta, settings } = useAuth()
  const [video, setVideo] = useState<Video | null>(null)
  const [clips, setClips] = useState<Clip[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [platform, setPlatform] = useState(settings?.default_platform ?? 'youtube_shorts')
  const [start, setStart] = useState(Number(params.get('start') ?? 0))
  const [end, setEnd] = useState(Number(params.get('end') ?? 15))
  const [title, setTitle] = useState('')

  const load = async () => {
    try {
      const [v, list] = await Promise.all([api.getVideo(videoId), api.listClips(videoId)])
      setVideo(v)
      setClips(list)
      localStorage.setItem('aca:lastVideo', v.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load clips.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [videoId]) // eslint-disable-line react-hooks/exhaustive-deps

  const create = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.createClip({
        video_id: videoId, start_s: start, end_s: end,
        title: title || `Clip ${clips.length + 1}`, platform,
      })
      if (res.status !== 'succeeded') throw new Error(res.error || 'Rendering failed.')
      setTitle('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not render the clip.')
    } finally {
      setBusy(false)
    }
  }

  const adjust = async (clip: Clip, patch: { start_s?: number; end_s?: number }) => {
    setBusy(true)
    setError('')
    try {
      const res = await api.updateClip(clip.id, patch)
      if (res.status !== 'succeeded') throw new Error('Re-render failed.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the clip.')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (clip: Clip) => {
    if (!confirm('Delete this clip and its rendered file?')) return
    try {
      await api.deleteClip(clip.id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete the clip.')
    }
  }

  if (loading) return <Spinner label="Loading clips…" />
  if (!video) return <ErrorNote>{error || 'Video not found.'}</ErrorNote>

  const platformOptions = (meta?.platforms ?? []).map((p) => ({ value: p.key, label: p.label }))
  const max = Math.floor(video.duration_s)

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<Scissors size={18} />}
        title="AI Clip Generator"
        subtitle={`Cut segments of “${video.original_name}” into platform-ready clips.`}
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      <Card className="mb-5">
        <p className="mb-3 font-semibold text-slate-100">New clip</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
          <Field label="Start (s)">
            <Input type="number" min={0} max={max} value={start}
                   onChange={(e) => setStart(Number(e.target.value))} />
          </Field>
          <Field label="End (s)">
            <Input type="number" min={1} max={max} value={end}
                   onChange={(e) => setEnd(Number(e.target.value))} />
          </Field>
          <Field label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Optional" />
          </Field>
          <Field label="Platform">
            <Select value={platform} onChange={setPlatform} options={platformOptions} />
          </Field>
          <Button onClick={create} loading={busy} disabled={end <= start}>
            <Plus size={15} /> Render clip
          </Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Range {timecode(start)} → {timecode(end)} ({Math.max(0, end - start)}s). Minimum{' '}
          {meta?.limits.clip_min_seconds ?? 3}s, and the range must stay inside the video.
        </p>
      </Card>

      {clips.length === 0 ? (
        <EmptyState
          icon={<Scissors size={26} />}
          title="No clips yet"
          body="Pick a suggested moment in the Video Studio, or set your own start and end above."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {clips.map((c) => (
            <Card key={c.id} className="!p-0 overflow-hidden">
              {c.status === 'ready' && c.video_url ? (
                <video src={c.video_url} controls preload="metadata"
                       className="aspect-[9/16] w-full bg-black object-contain" />
              ) : (
                <div className="grid aspect-[9/16] w-full place-items-center bg-ink-850 text-center text-xs text-muted">
                  {c.status === 'failed' ? c.error || 'Render failed' : 'Rendering…'}
                </div>
              )}
              <div className="p-4">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="truncate font-medium text-slate-100">{c.title}</p>
                  <StatusBadge status={c.status} />
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge tone="cyan">{c.aspect}</Badge>
                  <span className="chip">{timecode(c.start_s)} → {timecode(c.end_s)}</span>
                  {c.has_subtitles && <span className="chip">captions burned</span>}
                  {c.file_size > 0 && <span className="chip">{(c.file_size / 1048576).toFixed(2)} MB</span>}
                </div>
                {c.reason && <p className="mt-2 line-clamp-2 text-xs text-slate-500">{c.reason}</p>}

                <div className="mt-3 flex flex-wrap gap-2">
                  {c.status === 'ready' && (
                    <>
                      <a href={c.video_url} download className="btn-ghost !px-3 !py-1.5 text-xs">
                        <Download size={13} /> MP4
                      </a>
                      {c.subtitle_url && (
                        <a href={c.subtitle_url} download className="btn-ghost !px-3 !py-1.5 text-xs">
                          <Subtitles size={13} /> SRT
                        </a>
                      )}
                    </>
                  )}
                  <Button variant="ghost" className="!px-3 !py-1.5 text-xs"
                          onClick={() => adjust(c, { start_s: Math.max(0, c.start_s - 1), end_s: Math.max(c.start_s + 3, c.end_s - 1) })}
                          disabled={busy}>
                    −1s
                  </Button>
                  <Button variant="ghost" className="!px-3 !py-1.5 text-xs"
                          onClick={() => adjust(c, { start_s: c.start_s + 1, end_s: Math.min(video.duration_s, c.end_s + 1) })}
                          disabled={busy}>
                    +1s
                  </Button>
                  <Button variant="danger" className="!px-2.5 !py-1.5 text-xs" onClick={() => remove(c)}>
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
