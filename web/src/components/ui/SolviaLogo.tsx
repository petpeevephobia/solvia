import { clsx } from 'clsx'

interface SolviaLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export default function SolviaLogo({ size = 'md', className }: SolviaLogoProps) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-14 h-14',
    xl: 'w-20 h-20',
  }

  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={clsx(sizes[size], className)}
    >
      {/* 8 triangular rays */}
      <g fill="#EC6019">
        {/* Top ray */}
        <polygon points="24,2 27,10 21,10" />
        {/* Top-right ray */}
        <polygon points="38,10 33,15 36,19" />
        {/* Right ray */}
        <polygon points="46,24 38,21 38,27" />
        {/* Bottom-right ray */}
        <polygon points="38,38 36,29 33,33" />
        {/* Bottom ray */}
        <polygon points="24,46 21,38 27,38" />
        {/* Bottom-left ray */}
        <polygon points="10,38 12,29 15,33" />
        {/* Left ray */}
        <polygon points="2,24 10,21 10,27" />
        {/* Top-left ray */}
        <polygon points="10,10 15,15 12,19" />
      </g>
      {/* Center circle */}
      <circle cx="24" cy="24" r="10" fill="#EC6019" />
    </svg>
  )
}
