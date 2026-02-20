import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Cloud, Server, Wifi } from 'lucide-react'
import { checkHealth } from '../lib/api'

// Tauri IPC — only available in desktop mode
declare global {
  interface Window { __TAURI__?: any }
}

async function invokeTauri(cmd: string, args?: Record<string, unknown>): Promise<any> {
  if (window.__TAURI__) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke(cmd, args)
  }
  throw new Error('Not running in Tauri')
}

export default function ServerSetup() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'choose' | 'remote'>('choose')
  const [serverUrl, setServerUrl] = useState('http://localhost:8000')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [version, setVersion] = useState('')
  const isTauri = typeof window !== 'undefined' && '__TAURI__' in window

  const handleLocalServer = async () => {
    setError('')
    setLoading(true)
    try {
      if (isTauri) {
        // Tell Tauri to spawn the Python sidecar
        await invokeTauri('spawn_local_server')
      }
      // Test connection to local server
      const health = await checkHealth('http://localhost:8000')
      localStorage.setItem('server_url', 'http://localhost:8000')
      setVersion(health.version)
      setTimeout(() => navigate('/login'), 500)
    } catch (err: any) {
      setError(err.message || 'Could not connect to local server')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoteServer = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const url = serverUrl.replace(/\/+$/, '')
      const health = await checkHealth(url)
      localStorage.setItem('server_url', url)
      setVersion(health.version)
      setTimeout(() => navigate('/login'), 500)
    } catch (err: any) {
      setError(err.message || 'Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-950 to-brand-800 px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <BookOpen className="w-10 h-10 text-brand-400" />
          <span className="text-3xl font-bold text-white tracking-tight">OpenLedger</span>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 space-y-6">
          <div className="text-center">
            <Cloud className="w-12 h-12 text-brand-500 mx-auto mb-3" />
            <h2 className="text-xl font-semibold">Connect to Server</h2>
            <p className="text-sm text-gray-500 mt-1">Choose how to connect to your OpenLedger instance</p>
          </div>

          {error && <div className="bg-red-50 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}
          {version && <div className="bg-green-50 text-green-700 px-4 py-2 rounded-lg text-sm">Connected — v{version}</div>}

          {mode === 'choose' ? (
            <div className="space-y-3">
              {/* Local server option — only meaningful in Tauri, but show for any user */}
              <button
                onClick={handleLocalServer}
                disabled={loading}
                className="w-full flex items-center gap-4 px-4 py-4 border-2 border-gray-200 rounded-xl hover:border-brand-500 hover:bg-brand-50 transition-colors text-left disabled:opacity-50"
              >
                <Server className="w-8 h-8 text-brand-600 shrink-0" />
                <div>
                  <div className="font-medium text-gray-900">Use Local Server</div>
                  <div className="text-sm text-gray-500">
                    {isTauri ? 'Start the built-in server on this computer' : 'Connect to localhost:8000'}
                  </div>
                </div>
              </button>

              <button
                onClick={() => setMode('remote')}
                disabled={loading}
                className="w-full flex items-center gap-4 px-4 py-4 border-2 border-gray-200 rounded-xl hover:border-brand-500 hover:bg-brand-50 transition-colors text-left disabled:opacity-50"
              >
                <Wifi className="w-8 h-8 text-brand-600 shrink-0" />
                <div>
                  <div className="font-medium text-gray-900">Connect to Remote Server</div>
                  <div className="text-sm text-gray-500">Enter an IP address or hostname</div>
                </div>
              </button>
            </div>
          ) : (
            <form onSubmit={handleRemoteServer} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Server URL</label>
                <input
                  type="url"
                  required
                  value={serverUrl}
                  onChange={e => setServerUrl(e.target.value)}
                  placeholder="http://192.168.1.5:8000"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setMode('choose')}
                  className="flex-1 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {loading ? 'Testing...' : 'Test Connection'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
