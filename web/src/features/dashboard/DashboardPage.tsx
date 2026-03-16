import { useState, useRef, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { gscService } from '@/services/gsc'
import { auditService } from '@/services/audit'
import { useWebsiteStore } from '@/stores/websiteStore'
import { useAuthStore } from '@/stores/authStore'
import { useAuditStore } from '@/stores/auditStore'

// Import extracted components
import {
  MetricCard,
  IssueCard,
  IssueCardSkeleton,
  ChatSection,
} from './components'

// Import utils
import {
  calculateDateRange,
  DATE_PRESET_LABELS,
  formatDateDisplay,
  formatDateRangeDisplay,
  formatNumber,
  type DatePreset,
} from './utils/dateUtils'

export default function DashboardPage() {
  const { selectedWebsite } = useWebsiteStore()
  const { user } = useAuthStore()
  const { setAuditProgress, setAuditResultModal } = useAuditStore()
  const queryClient = useQueryClient()

  // Date filter state
  const [datePreset, setDatePreset] = useState<DatePreset>('28d')
  const [showCustomDateModal, setShowCustomDateModal] = useState(false)
  const [customStartDate, setCustomStartDate] = useState('')
  const [customEndDate, setCustomEndDate] = useState('')

  // Calculate date range
  const dateRange = useMemo(() => {
    if (datePreset === 'custom' && customStartDate && customEndDate) {
      return { startDate: customStartDate, endDate: customEndDate }
    }
    return calculateDateRange(datePreset)
  }, [datePreset, customStartDate, customEndDate])

  // Track banner hide timeout (updates store)
  const bannerTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Cleanup banner timeout on unmount
  useEffect(() => {
    return () => {
      if (bannerTimeoutRef.current) {
        clearTimeout(bannerTimeoutRef.current)
      }
    }
  }, [])

  // Hide audit progress banner
  const hideAuditBanner = (delay = 0) => {
    if (bannerTimeoutRef.current) {
      clearTimeout(bannerTimeoutRef.current)
      bannerTimeoutRef.current = null
    }

    if (delay > 0) {
      bannerTimeoutRef.current = setTimeout(() => {
        setAuditProgress({ isVisible: false, progress: 0 })
        bannerTimeoutRef.current = null
      }, delay)
    } else {
      setAuditProgress({ isVisible: false, progress: 0 })
    }
  }

  // Fetch GSC metrics
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['gsc-metrics', selectedWebsite, dateRange.startDate, dateRange.endDate],
    queryFn: () => gscService.getMetrics(selectedWebsite!, {
      startDate: dateRange.startDate,
      endDate: dateRange.endDate,
    }),
    enabled: !!selectedWebsite,
  })

  // Fetch current issues
  const { data: issuesData, isLoading: issuesLoading } = useQuery({
    queryKey: ['current-issues', selectedWebsite],
    queryFn: () => auditService.getCurrentIssues(selectedWebsite ?? undefined),
    enabled: !!selectedWebsite,
  })

  // Run audit mutation (updates audit store so banner/modal show on any route)
  const runAuditMutation = useMutation({
    mutationFn: async () => {
      setAuditProgress({ isVisible: true, progress: 0, message: 'Starting audit...' })

      try {
        const result = await auditService.runAudit(selectedWebsite!, (progress, message) => {
          setAuditProgress((prev) => ({ ...prev, progress, message }))
        })
        return result
      } catch (error) {
        hideAuditBanner(0)
        throw error
      }
    },
    onSuccess: (result) => {
      setAuditProgress({ isVisible: true, progress: 100, message: 'Audit completed!' })
      hideAuditBanner(1500)
      queryClient.invalidateQueries({ queryKey: ['current-issues'] })
      queryClient.invalidateQueries({ queryKey: ['audit-history'] })
      setAuditResultModal({ isVisible: true, result, isDownloading: false })
    },
    onError: () => {
      hideAuditBanner(0)
    },
  })

  // Custom date modal handlers
  const openCustomDateModal = () => {
    if (!customStartDate || !customEndDate) {
      const today = new Date()
      const endDate = new Date(today)
      endDate.setDate(endDate.getDate() - 1)
      const startDate = new Date(endDate)
      startDate.setDate(startDate.getDate() - 28)

      setCustomStartDate(startDate.toISOString().split('T')[0])
      setCustomEndDate(endDate.toISOString().split('T')[0])
    }
    setShowCustomDateModal(true)
  }

  const handleCustomDateApply = () => {
    if (customStartDate && customEndDate) {
      const start = new Date(customStartDate)
      const end = new Date(customEndDate)

      if (start > end) {
        alert('Start date must be before end date')
        return
      }

      setDatePreset('custom')
      setShowCustomDateModal(false)
    }
  }

  // Derived values
  const userName = user?.name?.split(' ')[0] || user?.email?.split('@')[0] || 'there'
  const issues = issuesData?.issues || []
  const seoScore = (metrics?.seo_score !== undefined && metrics?.seo_score !== null)
    ? metrics.seo_score
    : (issuesData?.seo_score !== undefined && issuesData?.seo_score !== null)
      ? issuesData.seo_score
      : 0
  const seoScoreLoading = metricsLoading || (issuesLoading && metrics?.seo_score === undefined)

  return (
    <div className="dashboard-container">
      {/* Custom Date Modal */}
      {showCustomDateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl p-6 shadow-xl w-full max-w-md mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-h3 font-heading font-semibold text-text-primary">Custom Date Range</h3>
              <button
                onClick={() => setShowCustomDateModal(false)}
                className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-p2 font-sans font-medium text-text-primary mb-1">Start Date</label>
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => setCustomStartDate(e.target.value)}
                  max={customEndDate || new Date().toISOString().split('T')[0]}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-p1 font-sans focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                />
              </div>
              <div>
                <label className="block text-p2 font-sans font-medium text-text-primary mb-1">End Date</label>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => setCustomEndDate(e.target.value)}
                  min={customStartDate}
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-p1 font-sans focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                />
              </div>
              <p className="text-note font-sans text-text-secondary">
                Note: GSC data has a ~1 day delay. Very recent data may not be available.
              </p>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCustomDateModal(false)}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-p2 font-sans font-medium text-text-secondary hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCustomDateApply}
                disabled={!customStartDate || !customEndDate}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg text-p1 font-sans font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header Section */}
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <h1 className="text-h1 font-heading font-bold text-text-primary">
            Hey, {userName}!{' '}
            {selectedWebsite && (
              <>
                We're tracking{' '}
                <span className="text-primary-600">{selectedWebsite}</span>
              </>
            )}
          </h1>
          <div className="text-p2 font-sans text-text-secondary">
            <span>Last Update: </span>
            <span>
              {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
          </div>
        </div>
      </div>

      {/* Overview Section */}
      <section className="overview mb-8">
        <div className="flex justify-between items-center mb-5">
          <div>
            <h2 className="text-h2 font-heading font-semibold text-text-primary">Overview</h2>
            <p className="text-p2 font-sans text-text-secondary mt-1">
              {datePreset === 'custom'
                ? `${formatDateDisplay(dateRange.startDate)} - ${formatDateDisplay(dateRange.endDate)}`
                : `All data displayed are from the ${DATE_PRESET_LABELS[datePreset]}`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {(['24h', '7d', '28d', '3mo'] as DatePreset[]).map((period) => (
              <button
                key={period}
                onClick={() => setDatePreset(period)}
                disabled={metricsLoading}
                className={clsx(
                  'px-3 py-1.5 text-p2 font-sans font-medium rounded-lg border transition-all',
                  period === datePreset
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white text-text-secondary border-gray-200 hover:text-primary-600 hover:border-primary-200 hover:bg-orange-50',
                  metricsLoading && 'opacity-50 cursor-not-allowed'
                )}
              >
                {period}
              </button>
            ))}
            <button
              onClick={openCustomDateModal}
              disabled={metricsLoading}
              className={clsx(
                'px-3 py-1.5 text-p2 font-sans font-medium rounded-lg border transition-all',
                datePreset === 'custom'
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-white text-text-secondary border-gray-200 hover:text-primary-600 hover:border-primary-200 hover:bg-orange-50',
                metricsLoading && 'opacity-50 cursor-not-allowed'
              )}
            >
              Custom
            </button>
            <span className="ml-2 text-p2 font-sans text-text-secondary">
              {formatDateRangeDisplay(dateRange.startDate, dateRange.endDate)}
            </span>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <MetricCard
            label="SEO Score"
            value={`${Math.round(seoScore)}/100`}
            change="Based on real GSC data"
            isLoading={seoScoreLoading}
            icon={<svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path stroke="#EC6019" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
          />
          <MetricCard
            label="Impressions"
            value={formatNumber(metrics?.impressions || 0)}
            change="Number of times you've appeared"
            isLoading={metricsLoading}
            icon={<svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path stroke="#EC6019" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
          />
          <MetricCard
            label="Avg. Position"
            value={(metrics?.position || 0).toFixed(1)}
            change="Search ranking position"
            isLoading={metricsLoading}
            icon={<svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path stroke="#EC6019" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>}
          />
          <MetricCard
            label="No. of Clicks"
            value={formatNumber(metrics?.clicks || 0)}
            change="Clicks from Google Search"
            isLoading={metricsLoading}
            icon={<svg width="20" height="20" fill="none" viewBox="0 0 24 24"><path stroke="#EC6019" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>}
          />
        </div>
      </section>

      {/* Current Issues Section */}
      <section className="current-issues mb-8">
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-h2 font-heading font-semibold text-text-primary">Current Issues Of The Month</h2>
          <button
            onClick={() => runAuditMutation.mutate()}
            disabled={!selectedWebsite || runAuditMutation.isPending}
            className={clsx(
              'px-4 py-2.5 rounded-lg text-p2 font-sans font-medium transition-all',
              'bg-white text-primary-600 border border-primary-600',
              'hover:bg-primary-600 hover:text-white',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {runAuditMutation.isPending ? 'Running...' : 'Run a new audit'}
          </button>
        </div>

        {/* Issues Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {issuesLoading ? (
            <>
              <IssueCardSkeleton />
              <IssueCardSkeleton />
              <IssueCardSkeleton />
            </>
          ) : issues.length > 0 ? (
            issues.map((issue, index) => (
              <IssueCard key={issue.id || index} issue={issue} />
            ))
          ) : (
            <div className="col-span-full py-12 text-center">
              <p className="text-p2 font-sans text-text-secondary">
                No issues. Run a new audit to get new insights.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Solvia Chat Section */}
      <ChatSection
        selectedWebsite={selectedWebsite}
        onAuditRequest={() => runAuditMutation.mutate()}
      />
    </div>
  )
}
