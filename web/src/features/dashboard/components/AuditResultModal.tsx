import { clsx } from 'clsx'
import type { AuditResult } from '@/types'

interface AuditResultModalProps {
  isVisible: boolean
  auditResult: AuditResult | null
  onClose: () => void
  onDownloadPdf: () => void
  onDownloadJson: () => void
  onViewReport: () => void
  isDownloading: boolean
}

function getStageColor(stage: string): string {
  switch (stage) {
    case 'trusted': return 'text-green-600 bg-green-100'
    case 'discoverable': return 'text-blue-600 bg-blue-100'
    case 'emerging': return 'text-yellow-600 bg-yellow-100'
    case 'hidden':
    default: return 'text-orange-600 bg-orange-100'
  }
}

function getStageName(stage: string): string {
  switch (stage) {
    case 'trusted': return 'Trusted'
    case 'discoverable': return 'Discoverable'
    case 'emerging': return 'Emerging'
    case 'hidden':
    default: return 'Hidden'
  }
}

export function AuditResultModal({
  isVisible,
  auditResult,
  onClose,
  onDownloadPdf,
  onDownloadJson,
  onViewReport,
  isDownloading,
}: AuditResultModalProps) {
  if (!isVisible || !auditResult) return null

  // Safely get the score (handle NaN and undefined)
  const score = typeof auditResult.seo_score === 'number' && !isNaN(auditResult.seo_score)
    ? auditResult.seo_score
    : 0

  // Safely get issue counts (handle undefined)
  const criticalIssues = auditResult.critical_issues ?? 0
  const highIssues = auditResult.high_issues ?? 0
  const mediumIssues = auditResult.medium_issues ?? 0
  const lowIssues = auditResult.low_issues ?? 0

  // Get SEO stage (default to 'hidden' if not set)
  const seoStage = auditResult.seo_stage || 'hidden'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-h3 font-heading font-semibold">Audit Complete!</h3>
              <p className="text-primary-100 text-p2 font-sans mt-1">Your SEO report is ready</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/20 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-5">
          {/* Score Display */}
          <div className="text-center mb-6">
            <div className={clsx(
              'inline-flex items-center justify-center w-24 h-24 rounded-full mb-3',
              getStageColor(seoStage)
            )}>
              <span className="text-3xl font-bold">{Math.round(score)}</span>
            </div>
            <p className={clsx('text-h2 font-heading font-semibold', getStageColor(seoStage).split(' ')[0])}>
              {getStageName(seoStage)}
            </p>
            <p className="text-p2 font-sans text-text-secondary mt-1">{auditResult.website_url}</p>
          </div>

          {/* Issues Summary */}
          <div className="grid grid-cols-4 gap-3 mb-6">
            <div className="text-center p-3 bg-red-50 rounded-lg">
              <p className="text-h2 font-heading font-bold text-red-600">{criticalIssues}</p>
              <p className="text-note font-sans text-red-600">Critical</p>
            </div>
            <div className="text-center p-3 bg-orange-50 rounded-lg">
              <p className="text-h2 font-heading font-bold text-orange-600">{highIssues}</p>
              <p className="text-note font-sans text-orange-600">High</p>
            </div>
            <div className="text-center p-3 bg-yellow-50 rounded-lg">
              <p className="text-h2 font-heading font-bold text-yellow-600">{mediumIssues}</p>
              <p className="text-note font-sans text-yellow-600">Medium</p>
            </div>
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <p className="text-h2 font-heading font-bold text-blue-600">{lowIssues}</p>
              <p className="text-note font-sans text-blue-600">Low</p>
            </div>
          </div>

          {/* Download Buttons */}
          <div className="space-y-3">
            <button
              onClick={onDownloadPdf}
              disabled={isDownloading}
              className={clsx(
                'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-p1 font-sans font-medium transition-all',
                'bg-primary-600 text-white hover:bg-primary-700',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {isDownloading ? 'Downloading...' : 'Download PDF Report'}
            </button>

            <div className="flex gap-3">
              <button
                onClick={onDownloadJson}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-p1 font-sans font-medium transition-all',
                  'bg-white text-text-primary border border-gray-200 hover:bg-gray-50'
                )}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download JSON
              </button>

              <button
                onClick={onViewReport}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-p1 font-sans font-medium transition-all',
                  'bg-white text-primary-600 border border-primary-600 hover:bg-primary-50'
                )}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                View Full Report
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
