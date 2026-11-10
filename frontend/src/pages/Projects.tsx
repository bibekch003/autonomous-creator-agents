import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Film, FolderKanban, Plus, Trash2, Upload, Video as VideoIcon, X,
} from 'lucide-react'
import {
  Button, Card, EmptyState, ErrorNote, Field, Input, PageHeader, Progress, Spinner,
  StatusBadge, timecode,
} from '../components/ui'
import { api } from '../services/api'
import type { Project, Video } from '../types'

export default function Projects() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<Project | null>(null)
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = async () => {
    try {
      const list = await api.listProjects()
      setProjects(list)
      if (selected) {
        const fresh = list.find((p) => p.id === selected.id) ?? null
        setSelected(fresh)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load projects.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const openProject = async (p: Project) => {
    setSelected(p)
    setError('')
    try {
      setVideos(await api.listVideos(p.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load videos.')
    }
  }

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      const p = await api.createProject({ name: name.trim(), description })
      setName('')
      setDescription('')
      setShowForm(false)
      await load()
      await openProject(p)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the project.')
    } finally {
      setCreating(false)
    }
  }

  const remove = async (p: Project) => {
    if (!confirm(`Delete "${p.name}"? Its videos and clips are removed too. This cannot be undone.`)) return
    try {
      await api.deleteProject(p.id)
      if (selected?.id === p.id) { setSelected(null); setVideos([]) }
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete the project.')
    }
  }

  const upload = async (file: File) => {
    if (!selected) return
    setError('')
    setUploadPct(0)
    try {
      const video = await api.uploadVideo(selected.id, file, setUploadPct)
      localStorage.setItem('aca:lastVideo', video.id)
      setVideos((v) => [video, ...v])
      await load()
      navigate(`/app/videos/${video.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setUploadPct(null)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  if (loading) return <Spinner label="Loading projects…" />

  return (
    <div className="animate-fade-up">
      <PageHeader
        icon={<FolderKanban size={18} />}
        title="My Projects"
        subtitle="A project groups one shoot. Upload a long take inside it and the agents take over."
        actions={<Button onClick={() => setShowForm((s) => !s)}><Plus size={15} /> New project</Button>}
      />

      {error && <div className="mb-4"><ErrorNote>{error}</ErrorNote></div>}

      {showForm && (
        <Card className="mb-5">
          <form onSubmit={create} className="grid gap-3 sm:grid-cols-[1fr_1.4fr_auto] sm:items-end">
            <Field label="Project name">
              <Input required value={name} onChange={(e) => setName(e.target.value)} placeholder="March shoot" />
            </Field>
            <Field label="Description (optional)">
              <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Two takes, one interview" />
            </Field>
            <div className="flex gap-2">
              <Button type="submit" loading={creating}>Create</Button>
              <Button type="button" variant="ghost" onClick={() => setShowForm(false)}><X size={15} /></Button>
            </div>
          </form>
        </Card>
      )}

      {projects.length === 0 ? (
        <EmptyState
          icon={<FolderKanban size={26} />}
          title="No projects yet"
          body="Create a project to hold your uploads, clips and generated copy."
          action={<Button onClick={() => setShowForm(true)}><Plus size={15} /> Create a project</Button>}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Card key={p.id} hover className={selected?.id === p.id ? '!border-cyan-400/50' : ''}>
              <div className="flex items-start justify-between gap-2">
                <button className="min-w-0 text-left" onClick={() => openProject(p)}>
                  <p className="truncate font-medium text-slate-100">{p.name}</p>
                  <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">{p.description || 'No description'}</p>
                </button>
                <button onClick={() => remove(p)} className="text-slate-500 hover:text-rose-300" title="Delete project">
                  <Trash2 size={15} />
                </button>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                <StatusBadge status={p.status} />
                <span className="chip">{p.video_count} videos</span>
                <span className="chip">{p.clip_count} clips</span>
              </div>
              <Button variant="ghost" className="mt-3 w-full" onClick={() => openProject(p)}>
                <VideoIcon size={14} /> Open
              </Button>
            </Card>
          ))}
        </div>
      )}

      {selected && (
        <div className="mt-8">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="heading">Videos in “{selected.name}”</h2>
            <div className="flex items-center gap-2">
              <input
                ref={fileRef}
                type="file"
                accept=".mp4,.mov,.m4v,.webm,.mkv"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
              />
              <Button onClick={() => fileRef.current?.click()} disabled={uploadPct !== null}>
                <Upload size={15} /> Upload video
              </Button>
            </div>
          </div>

          {uploadPct !== null && (
            <Card className="mb-3">
              <p className="mb-2 text-sm text-muted">Uploading… {uploadPct}%</p>
              <Progress value={uploadPct} />
            </Card>
          )}

          {videos.length === 0 ? (
            <EmptyState
              icon={<Film size={24} />}
              title="No videos in this project"
              body="Upload an MP4, MOV, WEBM or MKV. The file is validated and probed before anything else happens."
            />
          ) : (
            <div className="space-y-2">
              {videos.map((v) => (
                <Card key={v.id} hover className="flex flex-wrap items-center justify-between gap-3 !p-4">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-100">{v.original_name}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {v.width}×{v.height} · {timecode(v.duration_s)} · {v.fps} fps
                      {!v.has_audio && ' · no audio'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={v.status} />
                    <span className="chip">{v.clip_count} clips</span>
                    <Link to={`/app/videos/${v.id}`} className="btn-ghost !py-1.5 !px-3 text-xs">Open studio</Link>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
