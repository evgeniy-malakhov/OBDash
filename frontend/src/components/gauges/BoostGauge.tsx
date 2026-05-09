import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface BoostGaugeProps {
  value: number  // kPa
  maxBoost?: number
  className?: string
}

export function BoostGauge({ value, maxBoost = 150, className }: BoostGaugeProps) {
  const [displayValue, setDisplayValue] = useState(0)
  const [displayBar, setDisplayBar] = useState(0)
  const requestRef = useRef<number>()

  // Конвертация kPa в bar для отображения
  const barValue = value / 100
  const maxBar = maxBoost / 100

  // Плавная анимация
  useEffect(() => {
    const animate = () => {
      setDisplayValue(prev => {
        const diff = barValue - prev
        if (Math.abs(diff) < 0.001) return barValue
        return prev + diff * 0.12
      })
      setDisplayBar(prev => {
        const target = Math.min(1, Math.max(0, barValue / (maxBar * 1.2)))
        const diff = target - prev
        if (Math.abs(diff) < 0.001) return target
        return prev + diff * 0.1
      })
      requestRef.current = requestAnimationFrame(animate)
    }
    requestRef.current = requestAnimationFrame(animate)
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current)
    }
  }, [barValue, maxBar])

  const isBoost = displayValue > 0
  const isVacuum = displayValue < 0
  const boostColor = displayValue > 1.2 ? '#ef4444' : displayValue > 0.8 ? '#f59e0b' : '#34d399'

  return (
    <div className={cn('text-center', className)}>
      <div className="relative w-32 h-40 mx-auto">
        {/* Фон */}
        <div className="absolute inset-0 rounded-2xl bg-surface-800/40 border border-surface-700/30 overflow-hidden">
          {/* Шкала вакуума */}
          <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-gradient-to-t from-blue-500/10 to-transparent" />
          {/* Шкала наддува */}
          <div className="absolute top-0 left-0 right-0 h-2/3 bg-gradient-to-b from-red-500/5 via-amber-500/5 to-transparent" />

          {/* Индикаторная полоса */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 rounded-t-full transition-all duration-300"
            style={{
              height: `${displayBar * 100}%`,
              background: isBoost
                ? `linear-gradient(to top, ${boostColor}, ${boostColor}80)`
                : 'linear-gradient(to top, #60a5fa, #3b82f680)',
              boxShadow: `0 0 12px ${isBoost ? boostColor : '#3b82f6'}40`,
            }}
          />

          {/* Блики */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-2 rounded-t-full bg-white/20"
            style={{ height: `${displayBar * 100}%` }}
          />
        </div>

        {/* Значение */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold font-mono text-white tabular-nums"
            style={{ textShadow: `0 0 20px ${isBoost ? boostColor : '#3b82f6'}40` }}
          >
            {displayValue.toFixed(1)}
          </span>
          <span className="text-xs text-surface-400 mt-1">bar</span>
        </div>
      </div>

      <div className="flex justify-between text-[10px] text-surface-500 mt-2 px-1">
        <span>Vac</span>
        <span>0</span>
        <span>{maxBar.toFixed(1)}</span>
      </div>
    </div>
  )
}