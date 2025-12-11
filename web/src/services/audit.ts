import api, { extractData } from './api'
import type { AuditResult, AuditIssue } from '@/types'

export interface CreateAuditRequest {
  website_url: string
}

// Helper to delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

export const auditService = {
  // Start new audit (returns the pending audit)
  async startAudit(websiteUrl: string): Promise<{ audit: { id: number; status: string; seo_score: number }; message: string }> {
    const response = await api.post('/audit', { website_url: websiteUrl })
    return extractData(response)
  },

  // Run audit and wait for completion (polls until done)
  // Progress distribution: 0-10% start, 10-80% polling, 80-95% fetching results, 95-100% done
  async runAudit(websiteUrl: string, onProgress?: (progress: number, message: string) => void): Promise<AuditResult> {
    // Start the audit
    if (onProgress) onProgress(5, 'Starting audit...')

    const startResponse = await api.post('/audit', { website_url: websiteUrl })
    const { audit } = extractData(startResponse) as { audit: { id: number; status: string } }
    const auditId = audit.id

    if (onProgress) onProgress(10, 'Audit started, analyzing website...')

    // Poll for completion - progress goes from 10% to 80%
    let attempts = 0
    const maxAttempts = 60 // 5 minutes max (5 second intervals)

    while (attempts < maxAttempts) {
      await delay(5000) // Wait 5 seconds between polls

      const statusResponse = await api.get(`/audit/${auditId}/status`)
      const status = extractData(statusResponse) as { status: string; seo_score?: number; pdf_ready?: boolean; error?: string }

      if (onProgress) {
        // Progress from 10% to 80% during polling (reserve 20% for final fetch)
        const progress = Math.min(10 + (attempts * 2), 80)
        const statusMessage = status.status === 'running'
          ? 'Analyzing SEO metrics...'
          : status.status === 'pending'
            ? 'Waiting for analysis...'
            : `Processing... (${status.status})`
        onProgress(progress, statusMessage)
      }

      if (status.status === 'completed') {
        // Notify that we're fetching the full results (80% -> 95%)
        if (onProgress) onProgress(85, 'Fetching audit results...')

        // Fetch full audit with issues
        const fullResponse = await api.get(`/audit/${auditId}/issues`)
        const fullData = extractData(fullResponse) as { audit: AuditResult; issues: AuditIssue[] }

        if (onProgress) onProgress(95, 'Processing issues...')

        // Count issues by severity
        const issues = fullData.issues || []
        const criticalCount = issues.filter(i => i.severity === 'critical').length
        const highCount = issues.filter(i => i.severity === 'high').length
        const mediumCount = issues.filter(i => i.severity === 'medium').length
        const lowCount = issues.filter(i => i.severity === 'low').length

        if (onProgress) onProgress(100, 'Audit completed!')

        return {
          ...fullData.audit,
          critical_issues: criticalCount,
          high_issues: highCount,
          medium_issues: mediumCount,
          low_issues: lowCount,
          total_issues: issues.length,
        }
      }

      if (status.status === 'failed') {
        throw new Error(status.error || 'Audit failed')
      }

      attempts++
    }

    throw new Error('Audit timed out - please try again')
  },

  // Get audit history
  async getHistory(limit?: number): Promise<AuditResult[]> {
    const response = await api.get('/audit', { params: { limit } })
    const data = extractData(response) as { audits: Array<{
      id: number
      user_email: string
      website_url: string
      status: string
      seo_score: number
      seo_stage: string
      pdf_generated: boolean
      pdf_path?: string
      email_sent: boolean
      created_at: string
      critical_issues?: number
      high_issues?: number
      medium_issues?: number
      low_issues?: number
      total_issues?: number
    }> }

    // Map API response to frontend AuditResult type
    return (data.audits || []).map(audit => ({
      id: audit.id,
      audit_id: String(audit.id),
      website_url: audit.website_url,
      seo_score: audit.seo_score,
      critical_issues: audit.critical_issues || 0,
      high_issues: audit.high_issues || 0,
      medium_issues: audit.medium_issues || 0,
      low_issues: audit.low_issues || 0,
      total_issues: audit.total_issues || 0,
      audit_date: audit.created_at,
      status: audit.status as 'pending' | 'running' | 'completed' | 'failed',
      pdf_generated: audit.pdf_generated || false,
      pdf_path: audit.pdf_path,
      created_at: audit.created_at,
    }))
  },

  // Get single audit
  async getAudit(id: string): Promise<AuditResult> {
    const response = await api.get(`/audit/${id}`)
    return extractData(response)
  },

  // Get audit with issues
  async getAuditWithIssues(id: string): Promise<{ audit: AuditResult; issues: AuditIssue[] }> {
    const response = await api.get(`/audit/${id}/issues`)
    return extractData(response)
  },

  // Check audit status
  async checkStatus(id: string): Promise<{ status: string; seo_score?: number }> {
    const response = await api.get(`/audit/${id}/status`)
    return extractData(response)
  },

  // Get latest audit for website
  async getLatest(websiteUrl: string): Promise<AuditResult | null> {
    const response = await api.get('/audit/latest', { params: { website: websiteUrl } })
    return extractData(response)
  },

  // Download PDF
  async downloadPdf(id: string): Promise<Blob> {
    const response = await api.get(`/audit/${id}/pdf`, {
      responseType: 'blob',
    })
    return response.data
  },

  // Get current issues (from latest audit)
  async getCurrentIssues(websiteUrl?: string): Promise<{ issues: AuditIssue[]; seo_score: number }> {
    const response = await api.get('/audit/current-issues', { params: { website: websiteUrl } })
    return extractData(response)
  },
}
