import api, { extractData } from './api'
import type { GSCWebsite, GSCMetrics, GSCQuery, GSCPage } from '@/types'

export interface GSCFilters {
  website?: string
  startDate?: string
  endDate?: string
  dimensions?: string[]
}

export interface GSCDateFilter {
  startDate?: string
  endDate?: string
}

interface WebsitesResponse {
  websites?: GSCWebsite[]
}

interface QueriesResponse {
  queries?: GSCQuery[]
}

interface PagesResponse {
  pages?: GSCPage[]
}

interface DailyMetricsResponse {
  daily_metrics?: unknown[]
}

interface SelectedWebsiteResponse {
  success: boolean
  selected_website: string | null
}

interface SelectPropertyRequest {
  property_url: string
}

export const gscService = {
  // Get connected websites
  async getWebsites(): Promise<GSCWebsite[]> {
    const response = await api.get('/gsc/websites')
    // Handle wrapped response { websites: [...] }
    const data = extractData(response) as WebsitesResponse | GSCWebsite[]
    if (Array.isArray(data)) return data
    return data.websites || []
  },

  // Sync websites from GSC (fetches fresh data from Google)
  async syncWebsites(): Promise<GSCWebsite[]> {
    const response = await api.post('/gsc/websites/sync')
    const data = extractData(response) as WebsitesResponse | GSCWebsite[]
    if (Array.isArray(data)) return data
    return data.websites || []
  },

  // Get user's selected website (1:1 parity with original Python)
  async getSelectedWebsite(): Promise<string | null> {
    const response = await api.get('/gsc/selected-website')
    const data = extractData(response) as SelectedWebsiteResponse
    return data.selected_website
  },

  // Set user's selected website (1:1 parity with original Python)
  async selectProperty(propertyUrl: string): Promise<void> {
    await api.post('/gsc/select-property', { property_url: propertyUrl } as SelectPropertyRequest)
  },

  // Get metrics for selected website (with optional date filter)
  async getMetrics(website: string, dateFilter?: GSCDateFilter): Promise<GSCMetrics> {
    const params: Record<string, string> = { website }
    if (dateFilter?.startDate) params.start_date = dateFilter.startDate
    if (dateFilter?.endDate) params.end_date = dateFilter.endDate

    const response = await api.get('/gsc/metrics', { params })
    return extractData(response) as GSCMetrics
  },

  // Get top queries
  async getQueries(website: string, filters?: Omit<GSCFilters, 'website'>): Promise<GSCQuery[]> {
    const response = await api.get('/gsc/queries', {
      params: { website, ...filters }
    })
    const data = extractData(response) as QueriesResponse | GSCQuery[]
    if (Array.isArray(data)) return data
    return data.queries || []
  },

  // Get top pages
  async getPages(website: string, filters?: Omit<GSCFilters, 'website'>): Promise<GSCPage[]> {
    const response = await api.get('/gsc/pages', {
      params: { website, ...filters }
    })
    const data = extractData(response) as PagesResponse | GSCPage[]
    if (Array.isArray(data)) return data
    return data.pages || []
  },

  // Get daily metrics for charts
  async getDailyMetrics(website: string, filters?: Omit<GSCFilters, 'website'>): Promise<unknown[]> {
    const response = await api.get('/gsc/daily', {
      params: { website, ...filters }
    })
    const data = extractData(response) as DailyMetricsResponse | unknown[]
    if (Array.isArray(data)) return data
    return data.daily_metrics || []
  },
}
