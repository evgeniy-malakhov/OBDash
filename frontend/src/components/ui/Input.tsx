import { InputHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, ...props }, ref) => {
    return (
      <div className="space-y-1">
        {label && (
          <label className="text-xs text-surface-500 font-medium">{label}</label>
        )}
        <input
          ref={ref}
          className={cn(
            'w-full px-3 py-2 rounded-xl bg-surface-800 border text-surface-200 text-sm',
            'placeholder:text-surface-600',
            'focus:border-primary-500/50 focus:outline-none focus:ring-1 focus:ring-primary-500/20',
            'transition-all duration-200',
            error ? 'border-red-500/50' : 'border-surface-700',
            className
          )}
          {...props}
        />
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'