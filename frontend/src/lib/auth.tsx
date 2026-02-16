import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { auth as authApi } from './api'

interface User {
  id: string
  email: string
  full_name: string
  role: string
  organization_id: string
}

interface AuthCtx {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string, org: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthCtx>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [loading, setLoading] = useState(!!token)

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }, [])

  // Hydrate user from stored token on mount
  useEffect(() => {
    if (!token) return

    let cancelled = false
    authApi.me()
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch(() => {
        // Token is invalid or expired — clear it but DON'T trigger a
        // redirect here. The 401 interceptor in api.ts handles redirects
        // for active requests. This only handles stale tokens on app load.
        if (!cancelled) {
          localStorage.removeItem('token')
          setToken(null)
          setUser(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [token])

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    localStorage.setItem('token', res.access_token)
    setToken(res.access_token)
    const me = await authApi.me()
    setUser(me)
  }

  const register = async (email: string, password: string, name: string, org: string) => {
    const res = await authApi.register(email, password, name, org)
    localStorage.setItem('token', res.access_token)
    setToken(res.access_token)
    const me = await authApi.me()
    setUser(me)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
