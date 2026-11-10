import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ApiError, api } from '../services/api'
import type { Meta, User, UserSettings } from '../types'

interface AuthState {
  user: User | null
  settings: UserSettings | null
  meta: Meta | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshSettings: () => Promise<void>
  setSettings: (s: UserSettings) => void
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [session, metaResult] = await Promise.all([
          api.session().catch(() => ({ authenticated: false, user: null })),
          api.meta().catch(() => null),
        ])
        if (cancelled) return
        setMeta(metaResult)
        if (session.authenticated) {
          const me = await api.me().catch(() => null)
          if (!cancelled && me) {
            setUser(me.user)
            setSettings(me.settings)
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login({ email, password })
    setUser(res.user)
    setSettings(res.settings)
  }, [])

  const register = useCallback(async (name: string, email: string, password: string) => {
    const res = await api.register({ name, email, password })
    setUser(res.user)
    setSettings(res.settings)
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch (err) {
      if (!(err instanceof ApiError)) throw err
    }
    setUser(null)
    setSettings(null)
  }, [])

  const refreshSettings = useCallback(async () => {
    const s = await api.getSettings()
    setSettings(s)
  }, [])

  const value = useMemo(
    () => ({ user, settings, meta, loading, login, register, logout, refreshSettings, setSettings }),
    [user, settings, meta, loading, login, register, logout, refreshSettings],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
