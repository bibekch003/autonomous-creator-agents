import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Sparkles } from 'lucide-react'
import { Button, ErrorNote, Field, Input } from '../components/ui'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email.trim(), password)
      navigate(location.state?.from || '/app/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-5">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2.5">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-violet-500 text-ink-950">
            <Sparkles size={19} />
          </div>
          <span className="font-semibold text-white">Autonomous Creator Agents</span>
        </Link>

        <div className="card p-7">
          <h1 className="heading">Welcome back</h1>
          <p className="mt-1 text-sm text-muted">Sign in to your production studio.</p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <Field label="Email">
              <Input type="email" autoComplete="email" required value={email}
                     onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </Field>
            <Field label="Password">
              <Input type="password" autoComplete="current-password" required value={password}
                     onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </Field>
            {error && <ErrorNote>{error}</ErrorNote>}
            <Button type="submit" loading={busy} className="w-full">
              Sign in <ArrowRight size={15} />
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-muted">
            No account?{' '}
            <Link to="/register" className="font-medium text-cyan-300 hover:underline">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
