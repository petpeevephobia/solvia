// API Response types
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: ApiError
  meta?: PaginationMeta
}

export interface ApiError {
  code: string
  message: string
  details?: string
}

export interface PaginationMeta {
  page: number
  per_page: number
  total: number
  total_pages: number
}

// User types
export interface User {
  id: number
  email: string
  name: string
  picture?: string
  selected_website?: string
  last_login: string
  created_at: string
}

export interface Session {
  user_id: number
  email: string
  name: string
  picture?: string
  expires_at: string
}

// GSC types
export interface GSCWebsite {
  site_url: string
  permission_level: string
}

export interface GSCMetrics {
  impressions: number
  clicks: number
  ctr: number
  position: number
  seo_score: number
}

export interface GSCQuery {
  query: string
  impressions: number
  clicks: number
  ctr: number
  position: number
}

export interface GSCPage {
  page: string
  impressions: number
  clicks: number
  ctr: number
  position: number
}

// Audit types
export interface AuditResult {
  id: number
  audit_id: string
  website_url: string
  seo_score: number
  seo_stage?: 'hidden' | 'emerging' | 'discoverable' | 'trusted'
  previous_score?: number
  score_delta?: number
  critical_issues: number
  high_issues: number
  medium_issues: number
  low_issues: number
  total_issues: number
  audit_date: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  pdf_generated: boolean
  pdf_path?: string
  created_at: string
}

export interface AuditIssue {
  id: number
  issue_type: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  recommendation: string
  affected_url?: string
}

// Chat types
export interface Conversation {
  id: number
  user_email: string
  website_url?: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  tokens_used?: number
  created_at: string
}

// Dashboard types
export interface DashboardData {
  metrics: GSCMetrics
  recent_audits: AuditResult[]
  score_history: ScoreHistoryPoint[]
}

export interface ScoreHistoryPoint {
  date: string
  score: number
}
