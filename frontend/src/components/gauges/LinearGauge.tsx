import { useEffect, useState, useRef } from 'react'
import { cn } from '@/lib/utils'

interface LinearGaugeProps {
  value: number
  min: number
  max: number
  unit: string
  label: string
  icon?: React.ReactNode
  color?: string
  warningMin?: number
  warningMax?: number
  className?: string
  vertical?: boolean
  showValue?: boolean
}

export function LinearGauge({
  value,
  min,
  max,
  unit,
  label,
  icon,
  color = '#3b82f6',
  warningMin,
  warningMax,
  className,
  vertical = false,
  showValue = true,
}: LinearGaugeProps) {
  const [displayValue, setDisplayValue] = useState(value)
  const requestRef = useRef<number>()

  // Плавная анимация значения
  useEffect(() => {
    const animate = () => {
      setDisplayValue(prev => {
        const diff = value - prev
        if (Math.abs(diff) < 0.01) return value
        return prev + diff * 0.15
      })
      requestRef.current = requestAnimationFrame(animate)
    }
    requestRef.current = requestAnimationFrame(animate)
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current)
    }
  }, [value])

  const percentage = Math.min(100, Math.max(0, ((displayValue - min) / (max - min)) * 100))

  const isWarning = (warningMin && displayValue < warningMin) ||
                     (warningMax && displayValue > warningMax)

  return (
    <div className={cn(
      'flex gap-3',
      vertical ? 'flex-col items-center h-48' : 'items-center',
      className
    )}>
      {icon && (
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${color}20` }}
        >
          {icon}
        </div>
      )}

      <div className={cn(
        'flex-1 flex flex-col gap-1.5',
        vertical && 'h-full justify-end'
      )}>
        <div className="flex justify-between items-center">
          <span className="text-[10px] text-surface-500 uppercase font-medium">{label}</span>
          {showValue && (
            <span
              className="text-sm font-bold font-mono transition-colors duration-300"
              style={{ color: isWarning ? '#ef4444' : color }}
            >
              {displayValue.toFixed(1)}
              <span className="text-surface-500 text-[10px] ml-0.5">{unit}</span>
            </span>
          )}
        </div>

        <div className={cn(
          'relative rounded-full bg-surface-700/50 overflow-hidden',
          vertical ? 'w-3 flex-1' : 'h-2.5 w-full'
        )}>
          {/* Фон с градиентом */}
          <div
            className={cn(
              'absolute rounded-full transition-all duration-500 ease-out',
              vertical ? 'bottom-0 left-0 right-0' : 'left-0 top-0 bottom-0'
            )}
            style={{
              [vertical ? 'height' : 'width']: `${percentage}%`,
              background: isWarning
                ? 'linear-gradient(90deg, #ef4444, #f87171)'
                : `linear-gradient(90deg, ${color}80, ${color})`,
              boxShadow: `0 0 8px ${isWarning ? '#ef444460' : `${color}40`}`,
            }}
          />

          {/* Блики */}
          <div
            className={cn(
              'absolute rounded-full opacity-30',
              vertical ? 'left-0 right-0 h-1/2 top-0' : 'top-0 bottom-0 w-1/2 left-0'
            )}
            style={{
              background: `linear-gradient(${vertical ? '180deg' : '90deg'}, rgba(255,255,255,0.4), transparent)`,
            }}
          />

          {/* Метки предупреждений */}
          {warningMin && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-amber-400/50"
              style={{ left: `${((warningMin - min) / (max - min)) * 100}%` }}
            />
          )}
          {warningMax && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-red-400/50"
              style={{ left: `${((warningMax - min) / (max - min)) * 100}%` }}
            />
          )}
        </div>

        {/* Метки мин/макс */}
        <div className="flex justify-between text-[9px] text-surface-600 font-mono">
          <span>{min}</span>
          <span>{max}</span>
        </div>
      </div>
    </div>
  )
}