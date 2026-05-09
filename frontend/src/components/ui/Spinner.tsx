import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  text?: string
}

export function Spinner({ size = 'md', className, text }: SpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3', className)}>
      <Loader2 className={cn(
        'animate-spin text-primary-400',
        size === 'sm' && 'w-5 h-5',
        size === 'md' && 'w-8 h-8',
        size === 'lg' && 'w-12 h-12',
      )} />
      {text && (
        <p className="text-sm text-surface-400">{text}</p>
      )}
    </div>
  )
}