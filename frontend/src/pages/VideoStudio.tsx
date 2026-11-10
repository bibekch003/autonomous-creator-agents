import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ClipboardPaste, Image, Play, Scissors, Sparkles, Video as VideoIcon, Wand2,
} from 'lucide-react'
import {
  Badge, Button, Card, ErrorNote, Field, Note, PageHeader, Select, Spinner, StatusBadge,
  Textarea, timecode,
} from '../components/ui'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import type { Video } from '../types'

export default function VideoStudio() {
  const { videoId = '' } = useParams()
  const { meta, settings } = useAuth()
  const [video, setVideo] = useState<Video | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState<'analyse' | 'pipeline' | 'transcript' | null>(null)
  const [transcript, setTranscript] = useState('')
  const [platform, setPlatform] = useState(settings?.default_platform ?? 'youtube_shorts')
  const [clipSeconds, setClipSeconds] = useState(settings?.default_clip_seconds ?? 30)
  const [count, setCount] = useState(3)

  const load = async () => {
    try {
      const v = await api.getVideo(videoId)
      setVideo(v)
      setTranscript(v.transcript?.text ?? '')
      localStorage.setItem('aca:lastVideo', v.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load this video.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [videoId]) // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (kind: 'analyse' | 'pipeline') => {
    setBusy(kind)
    setError('')
    setInfo('')
    try {
      if (kind === 'analyse') {
        const res = await api.analyse(videoId, { platform, clipSeconds, count })
        if (res.status !== 'succeeded') throw new Error(res.error || 'Analysis failed.')
        setInfo(`Found ${(res.output?.moments as unknown[] | undefined)?.length ?? 0} candidate moments.`)
      } else {
        const res = await api.pipeline(videoId, { platform, clipSeconds, count })
        const failed = Object.entries(res.results).filter(([, r]) => r.status !== 'succeeded')
        setInfo(failed.length
          ? `Pipeline finished with ${failed.length} step(s) not succeeded.`
          : 'Pipeline finished: moments, clips, thumbnails and copy are ready.')
      }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The agent could not finish.')
    } finally {
      setBusy(null)
    }
  }

  const saveTranscript = async () => {
    setBusy('transcript')
    setError('')
    try {
      const v = await api.setTranscript(videoId, transcript)
      setVideo(v)
      setInfo('Transcript saved. Captions and transcript-based copy are now available.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the transcript.')
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <Spinner label="Loading video…" />
  if (!video) return <ErrorNote>{error || 'Video not found.'}</ErrorNote>

  const platformOptions = (meta?.platforms ?? []).map((p) => ({ value: p.key, label: p.label }))

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<VideoIcon size={18} />}
        title="Video Studio"
        subtitle={video.original_name}
        actions={
          <>
            <Link to={`/app/videos/${video.id}/clips`} className="btn-ghost"><Scissors size={15} /> Clips</Link>
            <Button onClick={() => run('pipeline')} loading={busy === 'pipeline'}>
              <Wand2 size={15} /> Run full pipeline
            </Button>
          </>
        }
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}
      {info && <div className="mb-4 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-3.5 py-2.5 text-sm text-emerald-200">{info}</div>}

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-5">
          <Card className="!p-0 overflow-hidden">
            <video
              key={video.id}
              src={video.stream_url}
              controls
              preload="metadata"
              className="aspect-video w-full bg-black"
            />
            <div className="flex flex-wrap items-center gap-2 p-4">
              <StatusBadge status={video.status} />
              <span className="chip">{video.width}×{video.height}</span>
              <span className="chip">{timecode(video.duration_s)}</span>
              <span className="chip">{video.fps} fps</span>
              <span className="chip">{(video.size_bytes / 1048576).toFixed(1)} MB</span>
              <span className="chip">{video.has_audio ? 'audio' : 'no audio'}</span>
            </div>
          </Card>

          <Card>
            <div className="mb-3 flex items-center justify-between">
              <p className="font-semibold text-slate-100">Suggested moments</p>
              <Button variant="ghost" onClick={() => run('analyse')} loading={busy === 'analyse'}>
                <Sparkles size={14} /> {video.moments.length ? 'Re-analyse' : 'Analyse video'}
              </Button>
            </div>

            {video.moments.length === 0 ? (
              <Note>
                No analysis yet. The Video Intelligence agent measures the audio track and ranks
                the passages with the highest energy. It needs a video with sound.
              </Note>
            ) : (
              <div className="space-y-2">
                {video.moments.map((m, i) => (
                  <div key={`${m.start}-${i}`} className="rounded-xl border border-ink-600 bg-ink-850/60 p-3.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge tone="cyan">#{i + 1}</Badge>
                        <span className="font-mono text-sm text-slate-200">
                          {timecode(m.start)} → {timecode(m.end)}
                        </span>
                        <span className="chip">score {m.score}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Link to={`/app/videos/${video.id}/clips?start=${m.start}&end=${m.end}`}
                              className="btn-ghost !px-3 !py-1.5 text-xs">
                          <Scissors size={13} /> Use this
                        </Link>
                      </div>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-muted">{m.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <p className="mb-3 font-semibold text-slate-100">Agent settings</p>
            <div className="space-y-3">
              <Field label="Platform">
                <Select value={platform} onChange={setPlatform} options={platformOptions} />
              </Field>
              <Field label={`Clip length · ${clipSeconds}s`} hint={`Between ${meta?.limits.clip_min_seconds ?? 3}s and ${meta?.limits.clip_max_seconds ?? 90}s`}>
                <input type="range" min={meta?.limits.clip_min_seconds ?? 5} max={60} step={1}
                       value={clipSeconds} onChange={(e) => setClipSeconds(Number(e.target.value))}
                       className="w-full accent-cyan-400" />
              </Field>
              <Field label={`Suggestions · ${count}`}>
                <input type="range" min={1} max={meta?.limits.max_segments ?? 8} step={1}
                       value={count} onChange={(e) => setCount(Number(e.target.value))}
                       className="w-full accent-cyan-400" />
              </Field>
            </div>
          </Card>

          <Card>
            <div className="mb-2 flex items-center gap-2">
              <ClipboardPaste size={15} className="text-cyan-300" />
              <p className="font-semibold text-slate-100">Transcript</p>
            </div>
            <p className="mb-2 text-xs text-muted">
              Current source:{' '}
              <span className="font-medium text-slate-300">{video.transcript?.source ?? 'none'}</span>
              {video.transcript?.source === 'none' && ' — paste your script to enable captions and transcript-based copy.'}
            </p>
            <Textarea rows={6} value={transcript} onChange={(e) => setTranscript(e.target.value)}
                      placeholder="Paste the words spoken in the video…" />
            <Button variant="ghost" className="mt-2 w-full" onClick={saveTranscript}
                    loading={busy === 'transcript'} disabled={!transcript.trim()}>
              Save transcript
            </Button>
          </Card>

          <Card>
            <p className="mb-2 font-semibold text-slate-100">Next steps</p>
            <div className="space-y-2">
              <Link to={`/app/videos/${video.id}/clips`} className="flex items-center gap-2 text-sm text-cyan-300 hover:underline">
                <Scissors size={14} /> Generate and adjust clips
              </Link>
              <Link to={`/app/videos/${video.id}/thumbnails`} className="flex items-center gap-2 text-sm text-cyan-300 hover:underline">
                <Image size={14} /> Design thumbnails
              </Link>
              <Link to={`/app/videos/${video.id}/content`} className="flex items-center gap-2 text-sm text-cyan-300 hover:underline">
                <Play size={14} /> Write titles and descriptions
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
