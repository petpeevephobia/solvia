import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, AlertCircle, Info, CheckCircle, Download, FileText, FileJson, ChevronLeft } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, ScoreCircle } from '@/components/ui'
import { auditService } from '@/services/audit'
import { clsx } from 'clsx'

export default function AuditDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [isDownloading, setIsDownloading] = useState(false)

  const { data: auditData, isLoading } = useQuery({
    queryKey: ['audit-with-issues', id],
    queryFn: () => auditService.getAuditWithIssues(id!),
    enabled: !!id,
  })

  const audit = auditData?.audit
  const issues = auditData?.issues || []

  // Calculate issue counts from issues array
  const criticalIssues = issues.filter(i => i.severity === 'critical').length
  const highIssues = issues.filter(i => i.severity === 'high').length
  const mediumIssues = issues.filter(i => i.severity === 'medium').length
  const lowIssues = issues.filter(i => i.severity === 'low').length

  // Download PDF handler
  const handleDownloadPdf = async () => {
    if (!id) return
    setIsDownloading(true)
    try {
      const blob = await auditService.downloadPdf(id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `seo_audit_${id}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download PDF:', error)
      alert('Failed to download PDF. Please try again.')
    } finally {
      setIsDownloading(false)
    }
  }

  // Download JSON handler
  const handleDownloadJson = () => {
    if (!auditData) return
    const dataStr = JSON.stringify(auditData, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `seo_audit_${id}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-5 h-5 text-red-500" />
      case 'high':
        return <AlertCircle className="w-5 h-5 text-orange-500" />
      case 'medium':
        return <Info className="w-5 h-5 text-yellow-500" />
      default:
        return <CheckCircle className="w-5 h-5 text-blue-500" />
    }
  }

  if (isLoading) {
    return <div className="text-center py-12 text-gray-500">Loading audit...</div>
  }

  if (!audit) {
    return <div className="text-center py-12 text-gray-500">Audit not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Back button / Breadcrumb */}
      <Link
        to="/audit"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        Back to Audit History
      </Link>

      {/* Page header with download buttons */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Report</h1>
          <p className="text-gray-600 mt-1">{audit.website_url}</p>
          <p className="text-sm text-gray-500 mt-1">
            {new Date(audit.created_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleDownloadPdf}
            disabled={isDownloading}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all',
              'bg-primary-600 text-white hover:bg-primary-700',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            <FileText className="w-4 h-4" />
            {isDownloading ? 'Downloading...' : 'Download PDF'}
          </button>
          <button
            onClick={handleDownloadJson}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all',
              'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
            )}
          >
            <FileJson className="w-4 h-4" />
            Download JSON
          </button>
        </div>
      </div>

      {/* Score overview */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="flex flex-col items-center justify-center py-8">
          <ScoreCircle score={audit.seo_score} size="lg" />
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Issues Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center p-4 bg-red-50 rounded-lg">
                <p className="text-3xl font-bold text-red-600">{criticalIssues}</p>
                <p className="text-sm text-red-600">Critical</p>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <p className="text-3xl font-bold text-orange-600">{highIssues}</p>
                <p className="text-sm text-orange-600">High</p>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <p className="text-3xl font-bold text-yellow-600">{mediumIssues}</p>
                <p className="text-sm text-yellow-600">Medium</p>
              </div>
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-3xl font-bold text-blue-600">{lowIssues}</p>
                <p className="text-sm text-blue-600">Low</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Issues list */}
      <Card>
        <CardHeader>
          <CardTitle>Issues ({issues?.length || 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {issues.length > 0 ? (
            <div className="space-y-4">
              {issues.map((issue) => (
                <div
                  key={issue.id}
                  className={clsx(
                    'p-4 rounded-lg border-l-4',
                    issue.severity === 'critical' && 'bg-red-50 border-red-500',
                    issue.severity === 'high' && 'bg-orange-50 border-orange-500',
                    issue.severity === 'medium' && 'bg-yellow-50 border-yellow-500',
                    issue.severity === 'low' && 'bg-blue-50 border-blue-500'
                  )}
                >
                  <div className="flex items-start gap-3">
                    {getSeverityIcon(issue.severity)}
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900">{issue.title}</h4>
                      <p className="text-sm text-gray-600 mt-1">{issue.description}</p>
                      {issue.recommendation && (
                        <p className="text-sm text-gray-700 mt-2">
                          <strong>Recommendation:</strong> {issue.recommendation}
                        </p>
                      )}
                      {issue.affected_url && (
                        <p className="text-xs text-gray-500 mt-2 font-mono">{issue.affected_url}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No issues found - great job!</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
