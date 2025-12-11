// Audit Progress Banner - shows audit progress at top of screen

interface AuditProgressBannerProps {
  isVisible: boolean
  progress: number
  message: string
  onMinimize: () => void
}

export function AuditProgressBanner({
  isVisible,
  progress,
  message,
  onMinimize,
}: AuditProgressBannerProps) {
  if (!isVisible) return null

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg transform transition-transform duration-400"
      style={{ transform: isVisible ? 'translateY(0)' : 'translateY(-100%)' }}
    >
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            {/* Progress Info */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
              <div>
                <div className="font-semibold text-sm">Running SEO Audit</div>
                <div className="text-xs text-white/80">{message}</div>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="flex-1 max-w-md">
              <div className="h-2 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-white rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Progress Percentage */}
            <div className="text-sm font-bold">{progress}%</div>
          </div>

          {/* Minimize Button */}
          <button
            onClick={onMinimize}
            className="ml-4 p-1 rounded hover:bg-white/20 transition-colors"
            title="Minimize"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
