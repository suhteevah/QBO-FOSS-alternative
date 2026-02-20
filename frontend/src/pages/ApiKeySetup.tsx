import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Key, Check } from 'lucide-react'
import { useAuth } from '../lib/auth'

export default function ApiKeySetup() {
  const { user, createApiKey } = useAuth()
  const navigate = useNavigate()
  const [keyName, setKeyName] = useState('My Desktop')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  // Auto-detect device info for the API key
  const [deviceInfo, setDeviceInfo] = useState('Desktop App')
  useEffect(() => {
    async function detectPlatform() {
      try {
        if (window.__TAURI__) {
          const { invoke } = await import('@tauri-apps/api/core')
          const info: { os: string; arch: string; hostname: string } = await invoke('get_platform_info')
          setDeviceInfo(`${info.os} ${info.arch}`)
          setKeyName(`${info.hostname} Desktop`)
        }
      } catch {
        // Fallback to generic info
        setDeviceInfo(`${navigator.platform || 'Desktop'}`)
      }
    }
    detectPlatform()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await createApiKey(keyName.trim(), 'desktop', deviceInfo)
      setSuccess(true)
      setTimeout(() => navigate('/'), 1000)
    } catch (err: any) {
      setError(err.message || 'Failed to create API key')
    } finally {
      setLoading(false)
    }
  }

  // If user isn't logged in yet, redirect to login
  if (!user) {
    navigate('/login')
    return null
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-950 to-brand-800 px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <BookOpen className="w-10 h-10 text-brand-400" />
          <span className="text-3xl font-bold text-white tracking-tight">OpenLedger</span>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 space-y-6">
          {success ? (
            <div className="text-center py-6">
              <Check className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-green-700">Connected!</h2>
              <p className="text-sm text-gray-500 mt-2">Your desktop is now linked to OpenLedger</p>
            </div>
          ) : (
            <>
              <div className="text-center">
                <Key className="w-12 h-12 text-brand-500 mx-auto mb-3" />
                <h2 className="text-xl font-semibold">Link This Desktop</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Create a persistent API key so you stay signed in
                </p>
              </div>

              {error && <div className="bg-red-50 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}

              <div className="bg-gray-50 rounded-lg px-4 py-3 text-sm text-gray-600">
                <div>Signed in as <span className="font-medium text-gray-900">{user.email}</span></div>
                <div className="text-xs text-gray-400 mt-1">Device: {deviceInfo}</div>
              </div>

              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Device Name</label>
                  <input
                    type="text"
                    required
                    value={keyName}
                    onChange={e => setKeyName(e.target.value)}
                    placeholder="e.g. Work Laptop"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || !keyName.trim()}
                  className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {loading ? 'Creating...' : 'Create & Connect'}
                </button>
              </form>

              <button
                onClick={() => navigate('/')}
                className="w-full text-center text-sm text-gray-500 hover:text-gray-700"
              >
                Skip for now (use temporary session)
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
