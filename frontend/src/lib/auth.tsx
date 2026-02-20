import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { auth as authApi, apiKeys } from './api'

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
  isDesktop: boolean
  hasServerUrl: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string, org: string) => Promise<void>
  createApiKey: (name: string, platform: string, deviceInfo?: string) => Promise<string>
  logout: () => void
}

const AuthContext = createContext<AuthCtx>(null!)

// Detect Tauri desktop environment
const isDesktop = typeof window !== 'undefined' && '__TAURI__' in window

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('api_key') || localStorage.getItem('token')
  )
  const [loading, setLoading] = useState(!!token)
  const hasServerUrl = !!localStorage.getItem('server_url')

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('api_key')
    // Keep server_url — user doesn't need to re-enter it on next login
    setToken(null)
    setUser(null)
  }, [])

  // Hydrate user from stored token/API key on mount
  useEffect(() => {
    if (!token) { setLoading(false); return }

    let cancelled = false
    authApi.me()
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem('token')
          localStorage.removeItem('api_key')
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

  const createApiKey = async (name: string, platform: string, deviceInfo?: string): Promise<string> => {
    const res = await apiKeys.create(name, platform, deviceInfo)
    // Store the API key and clear the JWT — API key is now the primary auth
    localStorage.setItem('api_key', res.raw_key)
    localStorage.removeItem('token')
    setToken(res.raw_key)
    return res.raw_key
  }

  return (
    <AuthContext.Provider value={{
      user, token, loading, isDesktop, hasServerUrl,
      login, register, createApiKey, logout,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
