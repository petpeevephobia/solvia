import { useState } from 'react'
import { clsx } from 'clsx'
import type { AuditIssue } from '@/types'

// Severity Icon Component
function SeverityIcon({ severity }: { severity: string }) {
  switch (severity?.toLowerCase()) {
    case 'high':
    case 'critical':
      return (
        <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      )
    case 'medium':
    case 'warning':
      return (
        <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      )
    default:
      return (
        <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
      )
  }
}

// Issue Card Skeleton
export function IssueCardSkeleton() {
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-5 h-5 bg-gray-200 rounded-full" />
        <div className="h-4 w-32 bg-gray-200 rounded" />
      </div>
      <div className="space-y-2 mb-3">
        <div className="h-3 w-full bg-gray-200 rounded" />
        <div className="h-3 w-3/4 bg-gray-200 rounded" />
      </div>
      <div className="h-3 w-24 bg-gray-100 rounded" />
    </div>
  )
}

// Issue Card Component
export function IssueCard({ issue }: { issue: AuditIssue }) {
  const [expanded, setExpanded] = useState(false)

  const getSeverityClass = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'high':
      case 'critical': return 'bg-[#FFD8D8] border-l-4 border-red-500'
      case 'medium':
      case 'warning': return 'bg-[#FFF1D8] border-l-4 border-yellow-500'
      default: return 'bg-[#FFF1D8] border-l-4 border-yellow-500'
    }
  }

  return (
    <div className={clsx('rounded-xl p-5 transition-all', getSeverityClass(issue.severity))}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <SeverityIcon severity={issue.severity} />
        <h3 className="text-h3 font-heading font-semibold text-text-primary">{issue.title}</h3>
      </div>

      {/* Description */}
      <div className="mb-3">
        {!expanded ? (
          <span className="text-p2 font-sans text-text-secondary block">{issue.description}</span>
        ) : (
          <div className="text-p2 font-sans text-text-secondary">
            <span className="font-semibold text-text-primary block mb-2">Detailed Analysis:</span>
            <span className="block">{issue.description}</span>
          </div>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="text-p2 font-sans text-primary-600 hover:text-primary-700 mt-2 font-medium"
        >
          {expanded ? '← Show less' : 'Show more details →'}
        </button>
      </div>

      {/* Fix Recommendation */}
      <div className="text-p2 font-sans">
        <span className="font-medium text-text-primary">Fix: </span>
        <span className="text-text-secondary">{issue.recommendation || 'Review and address this issue to improve your SEO score.'}</span>
      </div>
    </div>
  )
}
