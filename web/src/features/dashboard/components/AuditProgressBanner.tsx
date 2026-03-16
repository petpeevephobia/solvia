// Audit Progress Banner - shows audit progress at top of screen

interface AuditProgressBannerProps {
  isVisible: boolean
  progress: number
  message: string
}

export function AuditProgressBanner({
  isVisible,
  progress,
  message,
}: AuditProgressBannerProps) {
  if (!isVisible) return null

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg transform transition-transform duration-400"
      style={{ transform: isVisible ? 'translateY(0)' : 'translateY(-100%)' }}
    >
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center">
          {/* Progress Info */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <div>
              <div className="font-semibold text-p2 font-sans">Running SEO Audit</div>
              <div className="text-note font-sans text-white/80">{message}</div>
            </div>
          </div>

          {/* Progress Bar — centered */}
          <div className="flex-1 flex justify-center min-w-0 px-4">
            <div className="w-full max-w-md">
              <div className="h-2 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-white rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          </div>

          {/* Progress Percentage */}
          <div className="text-p2 font-sans font-bold flex-shrink-0">{progress}%</div>
        </div>
      </div>
    </div>
  )
}
