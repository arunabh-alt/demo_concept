export type User = {
  id: string
  full_name: string
  email: string
  created_at: string
  primary_agent_id: string | null
}

export type AuthResponse = {
  access_token: string
  token_type: string
  user: User
}

export type AgentExecutionRequest = {
  user_id: string
  agent_id: string
  message: string
}

export type ActionPayload = {
  type: string
  status: string
  details: Record<string, unknown>
}

export type LearningUpdate = {
  status: 'created' | 'updated'
  pattern_key: string
  usage_count: number
}

export type AgentExecutionResponse = {
  request_id: string
  conversation_id: string
  user_id: string
  agent_id: string
  mode: 'direct' | 'orchestrator'
  intent: string
  specialists_used: string[]
  prompt: string
  response_text: string
  structured_action: ActionPayload
  memory_hits: string[]
  learning_update: LearningUpdate
  created_at: string
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

export function buildVoicePipelineUrl(token: string): string {
  const websocketBase = API_BASE_URL.replace(/^http/, 'ws')
  return `${websocketBase}/voice/pipeline/ws?token=${encodeURIComponent(token)}`
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({ detail: 'Request failed' }))) as { detail?: string }
    throw new Error(payload.detail ?? 'Request failed')
  }
  return (await response.json()) as T
}

export async function signup(full_name: string, email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ full_name, email, password }),
  })
  return parseResponse<AuthResponse>(response)
}

export async function signin(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/signin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  return parseResponse<AuthResponse>(response)
}

export async function getMe(token: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseResponse<User>(response)
}

export async function executeAgent(token: string, payload: AgentExecutionRequest): Promise<AgentExecutionResponse> {
  const response = await fetch(`${API_BASE_URL}/agents/execute`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return parseResponse<AgentExecutionResponse>(response)
}
