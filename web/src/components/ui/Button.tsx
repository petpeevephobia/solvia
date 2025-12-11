import { forwardRef, ButtonHTMLAttributes } from 'react'
import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = clsx(
      'inline-flex items-center justify-center gap-2',
      'font-ui font-medium',
      'rounded-button transition-all duration-200',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none'
    )

    const variants = {
      primary: clsx(
        'bg-gradient-primary text-white',
        'shadow-button hover:shadow-button-hover',
        'hover:brightness-110 active:brightness-95',
        'focus:ring-primary-500'
      ),
      secondary: clsx(
        'bg-white text-text-primary border border-gray-200',
        'hover:bg-gray-50 hover:border-gray-300',
        'focus:ring-gray-400'
      ),
      danger: clsx(
        'bg-status-error text-white',
        'hover:bg-red-600',
        'focus:ring-red-500'
      ),
      ghost: clsx(
        'bg-transparent text-text-secondary',
        'hover:bg-gray-100 hover:text-text-primary',
        'focus:ring-gray-400'
      ),
    }

    const sizes = {
      sm: 'px-3 py-1.5 text-caption',
      md: 'px-5 py-2.5 text-body-sm',
      lg: 'px-6 py-3 text-body',
      icon: 'p-2.5 aspect-square',
    }

    return (
      <button
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          leftIcon && <span className="flex-shrink-0">{leftIcon}</span>
        )}
        {children}
        {!isLoading && rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
