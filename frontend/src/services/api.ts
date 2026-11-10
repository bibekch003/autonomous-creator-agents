/**
 * One place that talks to the backend.
 *
 * Every call goes through `request`, which:
 *  - sends the session cookie (credentials: 'include')
 *  - turns non-2xx responses into ApiError with the server's message
 *  - surfaces 401 as a typed error so the auth context can redirect
 */
import type {
  AgentInfo, AgentTask, AnalyticsDetail, AnalyticsOverview, AuthResponse, Clip,
  GeneratedContent, Meta, Project, SeoResult, TaskResult, Thumbnail, UserSettings, Video,
} from '../types'

const BASE = '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...init,
  })

  if (res.status === 204) return undefined as T

  const text = await res.text()
  const data = text ? safeJson(text) : null

  if (!res.ok) {
    const detail =
      (data && (data.detail || data.message)) ||
      (typeof data === 'string' ? data : '') ||
      `Request failed (${res.status})`
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data as T
}

function safeJson(text: string): any {
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

const get = <T>(p: string) => request<T>(p)
const post = <T>(p: string, body?: unknown) =>
  request<T>(p, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
const patch = <T>(p: string, body: unknown) =>
  request<T>(p, { method: 'PATCH', body: JSON.stringify(body) })
const del = (p: string) => request<void>(p, { method: 'DELETE' })

/** Upload with real progress events (fetch cannot report upload progress). */
function upload<T>(path: string, file: File, fields: Record<string, string> = {},
                   onProgress?: (pct: number) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)
    Object.entries(fields).forEach(([k, v]) => form.append(k, v))

    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE}${path}`)
    xhr.withCredentials = true
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      const data = xhr.responseText ? safeJson(xhr.responseText) : null
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as T)
      else reject(new ApiError(xhr.status, data?.detail || `Upload failed (${xhr.status})`))
    }
    xhr.onerror = () => reject(new ApiError(0, 'Network error during upload.'))
    xhr.send(form)
  })
}

export const api = {
  // --- meta / auth -------------------------------------------------------
  meta: () => get<Meta>('/meta'),
  health: () => get<Record<string, unknown>>('/health'),
  session: () => get<{ authenticated: boolean; user: unknown }>('/auth/session'),
  register: (body: { name: string; email: string; password: string }) =>
    post<AuthResponse>('/auth/register', body),
  login: (body: { email: string; password: string }) => post<AuthResponse>('/auth/login', body),
  logout: () => post<void>('/auth/logout'),
  me: () => get<AuthResponse>('/auth/me'),

  // --- projects ----------------------------------------------------------
  listProjects: () => get<Project[]>('/projects'),
  createProject: (body: { name: string; description?: string }) => post<Project>('/projects', body),
  getProject: (id: string) => get<Project>(`/projects/${id}`),
  updateProject: (id: string, body: { name: string; description?: string }) =>
    patch<Project>(`/projects/${id}`, body),
  deleteProject: (id: string) => del(`/projects/${id}`),

  // --- videos ------------------------------------------------------------
  listVideos: (projectId: string) => get<Video[]>(`/projects/${projectId}/videos`),
  getVideo: (id: string) => get<Video>(`/videos/${id}`),
  uploadVideo: (projectId: string, file: File, onProgress?: (pct: number) => void) =>
    upload<Video>(`/projects/${projectId}/videos`, file, {}, onProgress),
  setTranscript: (videoId: string, text: string, language = 'en') =>
    post<Video>(`/videos/${videoId}/transcript`, { text, language }),
  deleteVideo: (id: string) => del(`/videos/${id}`),

  analyse: (videoId: string, opts: { platform?: string; clipSeconds?: number; count?: number; sync?: boolean } = {}) => {
    const q = new URLSearchParams({
      sync: String(opts.sync ?? true),
      platform: opts.platform ?? 'youtube_shorts',
      clip_seconds: String(opts.clipSeconds ?? 30),
      count: String(opts.count ?? 3),
    })
    return post<TaskResult>(`/videos/${videoId}/analyse?${q}`)
  },

  pipeline: (videoId: string, opts: { platform?: string; clipSeconds?: number; count?: number; sync?: boolean } = {}) => {
    const q = new URLSearchParams({
      sync: String(opts.sync ?? true),
      platform: opts.platform ?? 'youtube_shorts',
      clip_seconds: String(opts.clipSeconds ?? 30),
      count: String(opts.count ?? 3),
    })
    return post<{ status: string; results: Record<string, TaskResult> }>(`/videos/${videoId}/pipeline?${q}`)
  },

  // --- clips -------------------------------------------------------------
  listClips: (videoId: string) => get<Clip[]>(`/videos/${videoId}/clips`),
  getClip: (id: string) => get<Clip>(`/clips/${id}`),
  createClip: (body: { video_id: string; start_s: number; end_s: number; title?: string; platform?: string; reason?: string }, sync = true) =>
    post<TaskResult>(`/clips?sync=${sync}`, body),
  updateClip: (id: string, body: { title?: string; start_s?: number; end_s?: number; platform?: string }, sync = true) =>
    patch<{ task_id: string; status: string; clip: Clip }>(`/clips/${id}?sync=${sync}`, body),
  deleteClip: (id: string) => del(`/clips/${id}`),

  // --- thumbnails --------------------------------------------------------
  listThumbnails: (params: { clip_id?: string; video_id?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.clip_id) q.set('clip_id', params.clip_id)
    if (params.video_id) q.set('video_id', params.video_id)
    return get<Thumbnail[]>(`/thumbnails?${q}`)
  },
  renderThumbnails: (body: { video_id: string; clip_id?: string | null; headline?: string; styles?: string[]; at_seconds?: number }) =>
    post<Thumbnail[]>('/thumbnails/render', body),
  uploadThumbnail: (file: File, fields: { video_id: string; clip_id?: string; headline?: string }) =>
    upload<Thumbnail>('/thumbnails/upload', file, fields as Record<string, string>),
  deleteThumbnail: (id: string) => del(`/thumbnails/${id}`),

  // --- content -----------------------------------------------------------
  generateContent: (body: { clip_id?: string | null; video_id?: string; platform?: string; topic?: string }) =>
    post<SeoResult>('/content/generate', body),
  listContent: (params: { clip_id?: string; video_id?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.clip_id) q.set('clip_id', params.clip_id)
    if (params.video_id) q.set('video_id', params.video_id)
    return get<GeneratedContent[]>(`/content?${q}`)
  },
  selectContent: (id: string) => patch<GeneratedContent>(`/content/${id}/select`, {}),

  // --- agents ------------------------------------------------------------
  listAgents: () => get<AgentInfo[]>('/agents'),
  listTasks: (limit = 20) => get<AgentTask[]>(`/agents/tasks?limit=${limit}`),
  getTask: (id: string) => get<AgentTask>(`/agents/tasks/${id}`),
  runAgent: (body: { agent: string; video_id?: string; clip_id?: string; project_id?: string; params?: Record<string, unknown> }, sync = true) =>
    post<AgentTask>(`/agents/run?sync=${sync}`, body),
  approveTask: (id: string, approve: boolean, note = '') =>
    post<AgentTask>(`/agents/tasks/${id}/approve`, { approve, note }),

  // --- analytics / settings ---------------------------------------------
  analyticsOverview: () => get<AnalyticsOverview>('/analytics/overview'),
  analyticsDetail: () => get<AnalyticsDetail>('/analytics/detail'),
  getSettings: () => get<UserSettings>('/settings'),
  updateSettings: (body: Partial<UserSettings>) => patch<UserSettings>('/settings', body),
}

export const mediaUrl = (path: string) => path
