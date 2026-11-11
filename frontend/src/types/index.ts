/** Types mirroring the FastAPI schemas. Kept in one file so pages stay readable. */

export interface User {
  id: string
  name: string
  email: string
  created_at: string
}

export interface UserSettings {
  default_platform: string
  default_clip_seconds: number
  burn_captions: boolean
  auto_subtitles: boolean
  creator_persona: string
  theme: string
}

export interface AuthResponse {
  user: User
  settings: UserSettings | null
}

export interface Platform {
  key: string
  label: string
  width: number
  height: number
}

export interface AgentInfo {
  name: string
  title: string
  description: string
  capabilities: string[]
  requires_approval: boolean
}

export interface Meta {
  app_name: string
  tagline: string
  version: string
  platforms: Platform[]
  agents: AgentInfo[]
  demo_mode?: boolean
  limits: {
    max_upload_mb: number
    clip_min_seconds: number
    clip_max_seconds: number
    max_segments: number
    video_extensions: string[]
  }
  engines: { llm: string; asr: string }
}

export interface Project {
  id: string
  name: string
  description: string
  status: string
  created_at: string
  video_count: number
  clip_count: number
}

export interface Moment {
  start: number
  end: number
  score: number
  reason: string
  label: string
}

export interface Transcript {
  id: string
  source: string
  language: string
  text: string
  cues: unknown[]
}

export interface Video {
  id: string
  project_id: string
  original_name: string
  size_bytes: number
  duration_s: number
  width: number
  height: number
  fps: number
  has_audio: boolean
  status: string
  error: string
  moments: Moment[]
  created_at: string
  clip_count: number
  stream_url: string
  transcript?: Transcript | null
  analysis?: Record<string, unknown>
}

export interface ThumbnailScore {
  score: number | null
  reasons?: string[]
  contrast?: number
  colorfulness?: number
  face_ratio?: number
  legibility?: number
  clutter?: number
  subject_method?: string
}

export interface Thumbnail {
  id: string
  clip_id: string | null
  video_id: string
  headline: string
  style: string
  width: number
  height: number
  is_uploaded: boolean
  score: ThumbnailScore
  created_at: string
  image_url: string
}

export interface ClipContent {
  id: string
  kind: string
  platform: string
  body: string
  source: string
}

export interface Clip {
  id: string
  video_id: string
  project_id: string
  title: string
  start_s: number
  end_s: number
  duration_s: number
  aspect: string
  platform: string
  status: string
  file_size: number
  has_subtitles: boolean
  error: string
  reason: string
  score: number
  created_at: string
  video_url: string
  subtitle_url: string
  thumbnails: Array<{ id: string; style: string; headline: string; score: number | null; image_url: string }>
  content: ClipContent[]
}

export interface GeneratedContent {
  id: string
  clip_id: string | null
  kind: string
  platform: string
  body: string
  is_selected: boolean
  source: string
}

export interface SeoResult {
  task_id: string
  source: string
  note: string
  topic: string
  titles: string[]
  description: string
  hashtags: string[]
  caption: string
  items: number
}

export interface AgentLog {
  id: string
  level: string
  message: string
  created_at: string
}

export interface AgentTask {
  id: string
  agent: string
  task_type: string
  status: string
  progress: number
  attempts: number
  error: string
  input_data: Record<string, unknown>
  output_data: Record<string, unknown>
  video_id: string | null
  clip_id: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  logs: AgentLog[]
}

export interface AnalyticsOverview {
  projects: number
  videos: number
  videos_processed: number
  clips: number
  clips_ready: number
  thumbnails: number
  total_video_seconds: number
  total_clip_seconds: number
  tasks_succeeded: number
  tasks_failed: number
  storage_mb: number
  source_note: string
}

export interface AnalyticsDetail extends AnalyticsOverview {
  activity: Array<{ label: string; value: number }>
  by_platform: Array<{ label: string; value: number }>
  recent: Array<{
    id: string
    title: string
    platform: string
    status: string
    duration_s: number
    score: number
    created_at: string
  }>
}

export interface TaskResult {
  task_id: string
  status: string
  output?: Record<string, unknown>
  error?: string
  note?: string
}
