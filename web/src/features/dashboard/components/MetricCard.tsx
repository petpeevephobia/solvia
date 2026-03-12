// MetricCard component - displays a single metric with icon

interface MetricCardProps {
  label: string
  value: string | number
  change?: string
  icon: React.ReactNode
  isLoading?: boolean
}

export function MetricCardSkeleton() {
  return (
    <div className="metric-card bg-white rounded-xl p-5 shadow-sm relative flex flex-col">
      <div className="absolute top-4 right-4 w-8 h-8 bg-gray-100 rounded-md animate-pulse" />
      <div className="h-3.5 w-20 bg-gray-200 rounded animate-pulse mb-2" />
      <div className="h-8 w-24 bg-gray-200 rounded animate-pulse mb-1" />
      <div className="h-3 w-32 bg-gray-200 rounded animate-pulse" />
    </div>
  )
}

export function MetricCard({ label, value, change, icon, isLoading }: MetricCardProps) {
  if (isLoading) {
    return <MetricCardSkeleton />
  }

  return (
    <div className="metric-card bg-white rounded-xl p-5 shadow-sm relative flex flex-col">
      <div className="absolute top-4 right-4 w-8 h-8 bg-gray-100 rounded-md flex items-center justify-center">
        {icon}
      </div>
      <div className="metric-content">
        <div className="text-p2 font-sans font-medium text-text-secondary mb-2">{label}</div>
        <div className="text-h2 font-heading font-semibold text-text-primary mb-1">{value}</div>
        <div className="text-p2 font-sans text-text-secondary">{change}</div>
      </div>
    </div>
  )
}
