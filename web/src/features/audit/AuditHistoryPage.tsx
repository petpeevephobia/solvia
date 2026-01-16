import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// Removed useNavigate - now using PDF preview modal instead of separate page
import { Eye, Download, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui'
import { auditService } from '@/services/audit'
import { useWebsiteStore } from '@/stores/websiteStore'
import { PdfPreviewModal } from './components/PdfPreviewModal'

type FilterType = 'all' | 'week' | 'month' | 'high_score' | 'low_score' | 'critical_issues'
type SortType = 'created_at_desc' | 'created_at_asc' | 'seo_score_desc' | 'seo_score_asc'

export default function AuditHistoryPage() {
  const { selectedWebsite } = useWebsiteStore()
  const queryClient = useQueryClient()

  const [filter, setFilter] = useState<FilterType>('all')
  const [sort, setSort] = useState<SortType>('created_at_desc')

  // PDF Preview Modal state
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewAuditId, setPreviewAuditId] = useState<string | null>(null)
  const [previewWebsiteUrl, setPreviewWebsiteUrl] = useState<string | undefined>(undefined)

  const { data: audits, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['audit-history'],
    queryFn: () => auditService.getHistory(50),
  })

  const runAuditMutation = useMutation({
    mutationFn: () => auditService.runAudit(selectedWebsite!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit-history'] })
    },
  })

  // Format date like original: "Dec 8, 2025, 06:45 AM"
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Filter audits
  const filterAudits = (audits: typeof auditsData) => {
    if (!audits) return []

    let filtered = [...audits]
    const now = new Date()

    switch (filter) {
      case 'week':
        filtered = filtered.filter(a => {
          const daysDiff = (now.getTime() - new Date(a.audit_date).getTime()) / (1000 * 60 * 60 * 24)
          return daysDiff <= 7
        })
        break
      case 'month':
        filtered = filtered.filter(a => {
          const daysDiff = (now.getTime() - new Date(a.audit_date).getTime()) / (1000 * 60 * 60 * 24)
          return daysDiff <= 30
        })
        break
      case 'high_score':
        filtered = filtered.filter(a => a.seo_score >= 80)
        break
      case 'low_score':
        filtered = filtered.filter(a => a.seo_score < 50)
        break
      case 'critical_issues':
        filtered = filtered.filter(a => (a.critical_issues || 0) > 0)
        break
    }

    return filtered
  }

  // Sort audits
  const sortAudits = (audits: typeof auditsData) => {
    if (!audits) return []

    return [...audits].sort((a, b) => {
      switch (sort) {
        case 'created_at_desc':
          return new Date(b.audit_date).getTime() - new Date(a.audit_date).getTime()
        case 'created_at_asc':
          return new Date(a.audit_date).getTime() - new Date(b.audit_date).getTime()
        case 'seo_score_desc':
          return b.seo_score - a.seo_score
        case 'seo_score_asc':
          return a.seo_score - b.seo_score
        default:
          return 0
      }
    })
  }

  const auditsData = audits || []
  const processedAudits = sortAudits(filterAudits(auditsData))

  // Open PDF preview modal instead of navigating to detail page
  const handlePreviewPdf = (auditId: string, websiteUrl?: string) => {
    setPreviewAuditId(auditId)
    setPreviewWebsiteUrl(websiteUrl)
    setPreviewModalOpen(true)
  }

  const handleClosePreview = () => {
    setPreviewModalOpen(false)
    setPreviewAuditId(null)
    setPreviewWebsiteUrl(undefined)
  }

  const handleDownloadPdf = async (auditId: string) => {
    try {
      const blob = await auditService.downloadPdf(auditId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `seo_audit_${auditId}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download PDF:', error)
      alert('Failed to download PDF report')
    }
  }

  // Calculate total issues for a row
  const getTotalIssues = (audit: typeof auditsData[0]) => {
    return (audit.critical_issues || 0) + (audit.high_issues || 0) +
           (audit.medium_issues || 0) + (audit.low_issues || 0)
  }

  return (
    <div className="space-y-6">
      {/* Page header - minimal like original */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 font-heading">Audit History</h1>
        <p className="text-gray-500 mt-1">View and download your past SEO audit reports</p>
      </div>

      {/* Controls bar - matching original exactly */}
      <div className="flex justify-between items-center flex-wrap gap-4">
        {/* Left side: Filters */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Filter:</label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as FilterType)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
            >
              <option value="all">All Audits</option>
              <option value="week">Last Week</option>
              <option value="month">Last Month</option>
              <option value="high_score">High Score (80+)</option>
              <option value="low_score">Low Score (&lt;50)</option>
              <option value="critical_issues">Critical Issues</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Sort:</label>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortType)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 bg-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
            >
              <option value="created_at_desc">Newest First</option>
              <option value="created_at_asc">Oldest First</option>
              <option value="seo_score_desc">Highest Score</option>
              <option value="seo_score_asc">Lowest Score</option>
            </select>
          </div>
        </div>

        {/* Right side: Refresh button */}
        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="p-2 hover:bg-gray-100 rounded-md transition-colors"
          title="Refresh audit history"
        >
          <RefreshCw className={`w-5 h-5 text-gray-600 ${isRefetching ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-16">
          <div className="w-10 h-10 mx-auto mb-4 border-3 border-gray-200 border-t-orange-500 rounded-full animate-spin" />
          <p className="text-gray-500">Loading audit history...</p>
        </div>
      )}

      {/* Audit Table - matching original exactly */}
      {!isLoading && processedAudits.length > 0 && (
        <div>
          {/* Header with count */}
          <h3 className="text-lg font-bold text-gray-900 font-heading mb-4">
            Audit Reports ({processedAudits.length} found)
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse bg-white rounded-lg overflow-hidden shadow-sm">
              <thead>
                <tr className="bg-gray-50 border-b-2 border-gray-200">
                  <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Website
                  </th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    SEO Score
                  </th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Issues
                  </th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {processedAudits.map((audit) => (
                  <tr
                    key={audit.audit_id}
                    className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    {/* Date */}
                    <td className="px-3 py-4 text-sm text-gray-900 whitespace-nowrap">
                      {formatDate(audit.audit_date)}
                    </td>

                    {/* Website */}
                    <td className="px-3 py-4 text-sm text-gray-500 max-w-[200px] overflow-hidden text-ellipsis">
                      {audit.website_url || 'Website'}
                    </td>

                    {/* SEO Score - format as XX/100 like original */}
                    <td className="px-3 py-4 text-center">
                      <span className="text-sm font-semibold text-gray-900">
                        {Math.round(audit.seo_score || 0)}/100
                      </span>
                    </td>

                    {/* Issues - total count */}
                    <td className="px-3 py-4 text-center">
                      <span className="text-sm font-semibold text-gray-900">
                        {getTotalIssues(audit)}
                      </span>
                    </td>

                    {/* Actions - Eye icon and Download icon */}
                    <td className="px-3 py-4">
                      <div className="flex items-center gap-2 justify-center">
                        {/* Preview PDF button */}
                        <button
                          onClick={() => handlePreviewPdf(audit.audit_id, audit.website_url)}
                          disabled={!audit.pdf_generated}
                          className={`p-2 hover:bg-gray-100 rounded-md transition-colors ${!audit.pdf_generated ? 'opacity-30 cursor-not-allowed' : ''}`}
                          title={audit.pdf_generated ? "Preview PDF" : "PDF not available yet"}
                        >
                          <Eye className="w-[18px] h-[18px] text-gray-600" />
                        </button>

                        {/* Download PDF button - only show if PDF is generated */}
                        {audit.pdf_generated ? (
                          <button
                            onClick={() => handleDownloadPdf(audit.audit_id)}
                            className="p-2 hover:bg-gray-100 rounded-md transition-colors"
                            title="Download PDF"
                          >
                            <Download className="w-[18px] h-[18px] text-gray-600" />
                          </button>
                        ) : (
                          <button
                            disabled
                            className="p-2 opacity-30 cursor-not-allowed"
                            title="PDF not available yet"
                          >
                            <Download className="w-[18px] h-[18px] text-gray-400" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State - matching original */}
      {!isLoading && processedAudits.length === 0 && (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">📊</div>
          <div className="text-lg font-semibold text-gray-900 mb-2">No Audit History</div>
          <div className="text-sm text-gray-500 mb-6">
            Run your first audit to see detailed SEO analysis and recommendations
          </div>
          <Button
            onClick={() => runAuditMutation.mutate()}
            disabled={!selectedWebsite || runAuditMutation.isPending}
            isLoading={runAuditMutation.isPending}
          >
            Run First Audit
          </Button>
        </div>
      )}

      {/* PDF Preview Modal */}
      {previewAuditId && (
        <PdfPreviewModal
          isOpen={previewModalOpen}
          onClose={handleClosePreview}
          auditId={previewAuditId}
          websiteUrl={previewWebsiteUrl}
        />
      )}
    </div>
  )
}
