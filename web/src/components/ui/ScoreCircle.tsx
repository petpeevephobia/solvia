import { clsx } from 'clsx'

interface ScoreCircleProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  label?: string
}

export default function ScoreCircle({
  score,
  size = 'md',
  showLabel = true,
  label = 'SEO Score',
}: ScoreCircleProps) {
  // Determine color based on score
  const getScoreColor = (score: number) => {
    if (score >= 80) return { stroke: '#22c55e', text: 'text-score-excellent', bg: 'bg-green-50' }
    if (score >= 60) return { stroke: '#84cc16', text: 'text-score-good', bg: 'bg-lime-50' }
    if (score >= 40) return { stroke: '#eab308', text: 'text-score-average', bg: 'bg-yellow-50' }
    if (score >= 20) return { stroke: '#f97316', text: 'text-score-poor', bg: 'bg-orange-50' }
    return { stroke: '#ef4444', text: 'text-score-critical', bg: 'bg-red-50' }
  }

  const colors = getScoreColor(score)

  const sizes = {
    sm: { container: 'w-14 h-14', text: 'text-p1', label: 'text-note', strokeWidth: 3 },
    md: { container: 'w-24 h-24', text: 'text-h2', label: 'text-p2', strokeWidth: 5 },
    lg: { container: 'w-36 h-36', text: 'text-h1', label: 'text-p1', strokeWidth: 7 },
  }

  const { container, text, label: labelSize, strokeWidth } = sizes[size]

  // SVG circle calculations
  const radius = 45
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const dashOffset = circumference - progress

  return (
    <div className="flex flex-col items-center">
      <div className={clsx('relative', container)}>
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            className="transition-all duration-1000 ease-out animate-score-fill"
            style={{ '--score-offset': dashOffset } as React.CSSProperties}
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={clsx('font-bold font-heading', text, colors.text)}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      {showLabel && (
        <span className={clsx('mt-2 text-text-secondary font-medium', labelSize)}>
          {label}
        </span>
      )}
    </div>
  )
}
