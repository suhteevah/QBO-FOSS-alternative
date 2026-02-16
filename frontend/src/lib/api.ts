const BASE = '/api'

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...opts, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

function upload<T>(path: string, file: File): Promise<T> {
  const token = localStorage.getItem('token')
  const form = new FormData()
  form.append('file', file)
  return fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  }).then(async (res) => {
    if (res.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }
    return res.json()
  })
}

// ── Auth ────────────────────────────────────────────────
export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string; role: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, full_name: string, organization_name: string) =>
    request<{ access_token: string; role: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, organization_name }),
    }),
  me: () => request<{ id: string; email: string; full_name: string; role: string; organization_id: string }>('/auth/me'),
}

// ── Accounts ────────────────────────────────────────────
export const accounts = {
  list: () => request<any[]>('/accounts/'),
  create: (data: any) => request<any>('/accounts/', { method: 'POST', body: JSON.stringify(data) }),
}

// ── Transactions ────────────────────────────────────────
export const transactions = {
  list: (reconciled?: boolean) => {
    const q = reconciled !== undefined ? `?reconciled=${reconciled}` : ''
    return request<any[]>(`/transactions/${q}`)
  },
  import: (file: File) => upload<any>('/transactions/import', file),
  classify: (limit = 50) =>
    request<any>('/transactions/classify', { method: 'POST', body: JSON.stringify({ limit }) }),
  createEntries: (threshold = 0.7) =>
    request<any>('/transactions/create-entries', { method: 'POST', body: JSON.stringify({ confidence_threshold: threshold }) }),
  process: (limit = 50, threshold = 0.7) =>
    request<any>('/transactions/process', { method: 'POST', body: JSON.stringify({ limit, confidence_threshold: threshold }) }),
}

// ── Journal Entries ─────────────────────────────────────
export const journal = {
  list: (status?: string) => {
    const q = status ? `?status=${status}` : ''
    return request<any[]>(`/journal/${q}`)
  },
  create: (data: any) => request<any>('/journal/', { method: 'POST', body: JSON.stringify(data) }),
  approve: (id: string) => request<any>(`/journal/${id}/approve`, { method: 'POST' }),
  void: (id: string, reason?: string) =>
    request<any>(`/journal/${id}/void${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`, { method: 'POST' }),
}

// ── Reports ─────────────────────────────────────────────
export const reports = {
  types: () => request<any>('/reports/'),
  profitLoss: (start_date: string, end_date: string) =>
    request<any>('/reports/profit-loss', {
      method: 'POST',
      body: JSON.stringify({ report_type: 'profit_loss', start_date, end_date }),
    }),
  balanceSheet: (end_date: string) =>
    request<any>('/reports/balance-sheet', {
      method: 'POST',
      body: JSON.stringify({ report_type: 'balance_sheet', start_date: '2020-01-01', end_date }),
    }),
  trialBalance: (end_date: string) =>
    request<any>('/reports/trial-balance', {
      method: 'POST',
      body: JSON.stringify({ report_type: 'trial_balance', start_date: '2020-01-01', end_date }),
    }),
}

// ── Reconciliation ──────────────────────────────────────
export const reconciliation = {
  suggestions: (limit = 50) => request<any[]>(`/reconciliation/suggestions?limit=${limit}`),
  match: (bank_transaction_id: string, journal_entry_id: string) =>
    request<any>('/reconciliation/match', {
      method: 'POST',
      body: JSON.stringify({ bank_transaction_id, journal_entry_id }),
    }),
  unmatch: (txn_id: string) => request<any>(`/reconciliation/unmatch/${txn_id}`, { method: 'POST' }),
  summary: () => request<any>('/reconciliation/summary'),
}

// ── Receipts ────────────────────────────────────────────
export const receipts = {
  list: () => request<any[]>('/receipts/'),
  upload: (file: File) => upload<any>('/receipts/upload', file),
  classify: (id: string) => request<any>(`/receipts/${id}/classify`, { method: 'POST' }),
  createEntry: (id: string, account_id?: string) =>
    request<any>(`/receipts/${id}/create-entry`, {
      method: 'POST',
      body: JSON.stringify(account_id ? { account_id } : {}),
    }),
}

// ── Periods ─────────────────────────────────────────────
export const periods = {
  list: () => request<any[]>('/periods/'),
  create: (data: { name: string; start_date: string; end_date: string }) =>
    request<any>('/periods/', { method: 'POST', body: JSON.stringify(data) }),
  readiness: (id: string) => request<any>(`/periods/${id}/readiness`),
  close: (id: string) => request<any>(`/periods/${id}/close`, { method: 'POST' }),
  reopen: (id: string) => request<any>(`/periods/${id}/reopen`, { method: 'POST' }),
}

// ── Audit ───────────────────────────────────────────────
export const audit = {
  list: (limit = 100) => request<any[]>(`/audit/?limit=${limit}`),
}

// ── Consolidated API export ─────────────────────────────
export const api = {
  auth,
  accounts,
  transactions,
  journal,
  reports,
  reconciliation,
  receipts,
  periods,
  audit,
}
