import api, { extractData } from './api'

export interface PageAnalysis {
  id: number
  user_email: string
  url: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  score: number
  created_at: string
  completed_at?: string
  error?: string
}

export interface PageData {
  title: string
  description: string
  h1: string
  h2_count: number
  h3_count: number
  word_count: number
  image_count: number
  images_with_alt: number
  internal_links: number
  external_links: number
  has_canonical: boolean
  has_robots: boolean
  has_open_graph: boolean
  has_schema: boolean
  load_time_ms: number
  content_hash: string
}

export interface SEOIssue {
  id: number
  analysis_id: number
  severity: 'critical' | 'warning' | 'info'
  category: string
  title: string
  description: string
  current_value?: string
  suggestion: string
  created_at: string
}

export interface SiteMapResult {
  pages: string[]
  total: number
}

export const onpageService = {
  // Analyze a page
  async analyzePage(url: string): Promise<PageAnalysis> {
    const response = await api.post('/onpage/analyze', { url })
    return extractData(response)
  },

  // Get analysis history
  async getAnalyses(limit?: number): Promise<PageAnalysis[]> {
    const response = await api.get('/onpage/analyses', { params: { limit } })
    return extractData(response)
  },

  // Get single analysis with data and issues
  async getAnalysis(id: number): Promise<{ analysis: PageAnalysis; data: PageData; issues: SEOIssue[] }> {
    const response = await api.get(`/onpage/analyses/${id}`)
    return extractData(response)
  },

  // Check analysis status
  async checkStatus(id: number): Promise<{ status: string; score?: number }> {
    const response = await api.get(`/onpage/analyses/${id}/status`)
    return extractData(response)
  },

  // Map site pages
  async mapSite(url: string): Promise<SiteMapResult> {
    const response = await api.post('/onpage/map', { url })
    return extractData(response)
  },
}
