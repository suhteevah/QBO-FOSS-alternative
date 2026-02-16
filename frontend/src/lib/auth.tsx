import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
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

  useEffect(() => {
    if (token) {
      authApi.me().then(setUser).catch(() => {
        localStorage.removeItem('token')
        setToken(null)
      }).finally(() => setLoading(false))
    }
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

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
