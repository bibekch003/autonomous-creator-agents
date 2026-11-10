import { Link } from 'react-router-dom'
import {
  ArrowRight, Bot, Clapperboard, Cpu, Image, Layers, Scissors, ShieldCheck,
  Sparkles, TextCursorInput, Video, Wand2,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

const agents = [
  { icon: Video, name: 'Video Intelligence', body: 'Probes the file, extracts audio, transcribes speech and ranks the passages with the highest measured energy.' },
  { icon: Scissors, name: 'Editing', body: 'Cuts those moments into 9:16, 1:1 or 16:9 clips with FFmpeg, loudness-normalised and captioned.' },
  { icon: Image, name: 'Design', body: 'Renders thumbnail concepts from real frames and scores each on five measured sub-scores.' },
  { icon: TextCursorInput, name: 'SEO', body: 'Three titles, a description, hashtags and per-platform copy — template engine or your own LLM.' },
  { icon: Layers, name: 'Analytics', body: 'Reports your own production statistics. Never pretends to be platform engagement data.' },
  { icon: Bot, name: 'Community', body: 'Drafts replies in your voice and stops. Nothing is posted without your approval.' },
]

const steps = [
  { n: '01', title: 'Upload a long take', body: 'MP4, MOV, WEBM or MKV. Size and type are validated before anything touches the disk.' },
  { n: '02', title: 'The agents analyse it', body: 'Audio energy finds the moments; a transcript (Whisper or pasted) turns them into captions.' },
  { n: '03', title: 'Pick and adjust', body: 'Every suggested moment shows its score and the reason. Move the handles if you disagree.' },
  { n: '04', title: 'Download ready clips', body: 'Vertical with captions burned in, plus thumbnails, titles and descriptions.' },
]

export default function Landing() {
  const { user } = useAuth()
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-violet-500 text-ink-950">
            <Sparkles size={18} />
          </div>
          <span className="text-sm font-semibold text-white">Autonomous Creator Agents</span>
        </div>
        <nav className="flex items-center gap-2">
          {user ? (
            <Link to="/app/dashboard" className="btn-primary">Open studio <ArrowRight size={15} /></Link>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">Sign in</Link>
              <Link to="/register" className="btn-primary">Get started</Link>
            </>
          )}
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-5 pb-16 pt-10 text-center">
        <span className="chip">AI production studio · runs on your own machine</span>
        <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold leading-tight tracking-tight text-white sm:text-5xl">
          One long video in.<br />
          <span className="gradient-text">A week of shorts out.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-slate-400">
          Upload a take and six specialised agents do the repetitive work: find the moments worth
          clipping, cut them for every platform, write the copy and design the thumbnails. You
          review, adjust, and download.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link to={user ? '/app/dashboard' : '/register'} className="btn-primary px-6 py-3">
            Start a project <ArrowRight size={16} />
          </Link>
          <Link to="/login" className="btn-ghost px-6 py-3">I already have an account</Link>
        </div>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-slate-500">
          <span className="flex items-center gap-1.5"><ShieldCheck size={13} /> Private per-account storage</span>
          <span className="flex items-center gap-1.5"><Cpu size={13} /> No GPU, no paid API required</span>
          <span className="flex items-center gap-1.5"><Wand2 size={13} /> Works fully offline</span>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-16">
        <h2 className="mb-1 text-center text-2xl font-semibold text-white">Six agents, one orchestrator</h2>
        <p className="mb-8 text-center text-sm text-muted">
          Each agent is a separate module with its own inputs, logs and failure handling.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map(({ icon: Icon, name, body }) => (
            <div key={name} className="card card-hover p-5">
              <div className="mb-3 grid h-9 w-9 place-items-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
                <Icon size={17} />
              </div>
              <p className="font-semibold text-slate-100">{name}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-16">
        <div className="card overflow-hidden p-0">
          <div className="grid gap-0 md:grid-cols-4">
            {steps.map((s) => (
              <div key={s.n} className="border-b border-ink-600/70 p-6 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
                <p className="font-mono text-xs text-cyan-300">{s.n}</p>
                <p className="mt-2 font-semibold text-slate-100">{s.title}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-20">
        <div className="card flex flex-wrap items-center justify-between gap-5 p-7">
          <div>
            <p className="flex items-center gap-2 text-lg font-semibold text-white">
              <Clapperboard size={18} className="text-cyan-300" /> Honest about what it is
            </p>
            <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-muted">
              Clip suggestions come from measured audio energy — a signal, not a promise of virality.
              Analytics are your own production numbers, not platform data. Copy is written by a
              template engine unless you connect an LLM. Every screen says which is which.
            </p>
          </div>
          <Link to="/register" className="btn-primary">Create an account</Link>
        </div>
      </section>

      <footer className="border-t border-ink-600/70 py-6 text-center text-xs text-slate-500">
        Autonomous Creator Agents · FastAPI + React + FFmpeg · MIT licence
      </footer>
    </div>
  )
}
