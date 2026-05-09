import { useEffect, useState, useRef } from 'react'
import { cn } from '@/lib/utils'

interface SpeedometerProps {
  value: number
  max: number
  unit: string
  label: string
  color?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
  warningZone?: number
  dangerZone?: number
}

export function Speedometer({
  value,
  max,
  unit,
  label,
  color = '#3b82f6',
  size = 'md',
  className,
  warningZone,
  dangerZone,
}: SpeedometerProps) {
  const [currentAngle, setCurrentAngle] = useState(-135)
  const [displayValue, setDisplayValue] = useState(0)
  const requestRef = useRef<number>()
  const previousAngleRef = useRef(-135)

  // Конфигурация размеров с увеличенными значениями
  const sizes = {
    sm: { width: 200, height: 160, fontSize: 28, labelSize: 10, unitSize: 12, padding: 20 },
    md: { width: 280, height: 220, fontSize: 40, labelSize: 12, unitSize: 14, padding: 30 },
    lg: { width: 360, height: 280, fontSize: 52, labelSize: 14, unitSize: 16, padding: 40 },
  }

  const { width, height, fontSize, labelSize, unitSize, padding } = sizes[size]
  const centerX = width / 2
  const centerY = height * 0.82
  const radius = Math.min(width, height) * 0.40

  const startAngle = -135
  const endAngle = 135
  const totalAngle = endAngle - startAngle

  // Плавная анимация
  useEffect(() => {
    const targetAngle = startAngle + (Math.min(value, max) / max) * totalAngle
    const targetValue = Math.min(value, max)

    const animate = () => {
      const diff = targetAngle - previousAngleRef.current
      previousAngleRef.current += diff * 0.08

      if (Math.abs(diff) > 0.01) {
        setCurrentAngle(previousAngleRef.current)
        setDisplayValue(prev => {
          const valDiff = targetValue - prev
          return prev + valDiff * 0.12
        })
        requestRef.current = requestAnimationFrame(animate)
      } else {
        previousAngleRef.current = targetAngle
        setCurrentAngle(targetAngle)
        setDisplayValue(targetValue)
      }
    }

    requestRef.current = requestAnimationFrame(animate)
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current)
    }
  }, [value, max, startAngle, totalAngle])

  const describeArc = (cx: number, cy: number, r: number, start: number, end: number) => {
    const startRad = (start - 90) * Math.PI / 180
    const endRad = (end - 90) * Math.PI / 180
    const x1 = cx + r * Math.cos(startRad)
    const y1 = cy + r * Math.sin(startRad)
    const x2 = cx + r * Math.cos(endRad)
    const y2 = cy + r * Math.sin(endRad)
    const largeArc = end - start <= 180 ? 0 : 1
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`
  }

  // Деления шкалы
  const ticks = []
  const numTicks = 26
  for (let i = 0; i <= numTicks; i++) {
    const angle = startAngle + (i / numTicks) * totalAngle
    const rad = (angle - 90) * Math.PI / 180
    const isMain = i % 5 === 0 || i === numTicks
    const tickLength = isMain ? 14 : 7
    const innerR = radius - tickLength - 8
    const outerR = radius - 8

    const x1 = centerX + innerR * Math.cos(rad)
    const y1 = centerY + innerR * Math.sin(rad)
    const x2 = centerX + outerR * Math.cos(rad)
    const y2 = centerY + outerR * Math.sin(rad)

    const tickValue = (i / numTicks) * max
    const isWarning = warningZone && tickValue >= warningZone
    const isDanger = dangerZone && tickValue >= dangerZone

    ticks.push({
      x1, y1, x2, y2,
      value: tickValue,
      isMain,
      isWarning: isWarning && !isDanger,
      isDanger,
    })
  }

  // Координаты стрелки
  const needleAngle = currentAngle - 90
  const needleRad = needleAngle * Math.PI / 180
  const needleLength = radius * 0.7
  const needleX = centerX + needleLength * Math.cos(needleRad)
  const needleY = centerY + needleLength * Math.sin(needleRad)

  return (
    <div className={cn('relative inline-flex flex-col items-center', className)}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ overflow: 'visible' }}
      >
        {/* Фоновая дуга */}
        <path
          d={describeArc(centerX, centerY, radius - 6, startAngle, endAngle)}
          fill="none"
          stroke="rgba(148,163,184,0.06)"
          strokeWidth={18}
          strokeLinecap="round"
        />

        {/* Зона предупреждения */}
        {warningZone && (
          <path
            d={describeArc(
              centerX, centerY, radius - 6,
              startAngle + (warningZone / max) * totalAngle,
              dangerZone ? startAngle + (dangerZone / max) * totalAngle : endAngle
            )}
            fill="none"
            stroke="rgba(251,191,36,0.2)"
            strokeWidth={18}
            strokeLinecap="round"
          />
        )}

        {/* Зона опасности */}
        {dangerZone && (
          <path
            d={describeArc(
              centerX, centerY, radius - 6,
              startAngle + (dangerZone / max) * totalAngle,
              endAngle
            )}
            fill="none"
            stroke="rgba(239,68,68,0.2)"
            strokeWidth={18}
            strokeLinecap="round"
          />
        )}

        {/* Активная дуга */}
        <path
          d={describeArc(centerX, centerY, radius - 6, startAngle, currentAngle)}
          fill="none"
          stroke={color}
          strokeWidth={18}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 10px ${color}50)` }}
        />

        {/* Деления */}
        {ticks.map((tick, i) => (
          <line
            key={i}
            x1={tick.x1}
            y1={tick.y1}
            x2={tick.x2}
            y2={tick.y2}
            stroke={
              tick.isDanger ? 'rgba(239,68,68,0.9)' :
              tick.isWarning ? 'rgba(251,191,36,0.9)' :
              tick.isMain ? 'rgba(226,232,240,0.8)' : 'rgba(148,163,184,0.4)'
            }
            strokeWidth={tick.isMain ? 2.5 : 1.5}
            strokeLinecap="round"
          />
        ))}

        {/* Подписи делений */}
        {ticks.filter(t => t.isMain).map((tick, i) => (
          <text
            key={`label-${i}`}
            x={tick.x2 + (tick.x2 - centerX) * 0.22}
            y={tick.y2 + (tick.y2 - centerY) * 0.22}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={
              tick.isDanger ? 'rgba(239,68,68,0.9)' :
              tick.isWarning ? 'rgba(251,191,36,0.9)' :
              'rgba(203,213,225,0.9)'
            }
            fontSize={labelSize + 1}
            fontFamily="monospace"
            fontWeight="bold"
          >
            {Math.round(tick.value)}
          </text>
        ))}

        {/* Стрелка */}
        <g>
          {/* Тень стрелки */}
          <line
            x1={centerX + 1}
            y1={centerY + 1}
            x2={needleX + 1}
            y2={needleY + 1}
            stroke="rgba(0,0,0,0.4)"
            strokeWidth={4}
            strokeLinecap="round"
          />
          {/* Стрелка с градиентом */}
          <line
            x1={centerX}
            y1={centerY}
            x2={needleX}
            y2={needleY}
            stroke={color}
            strokeWidth={3}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
          {/* Центр */}
          <circle cx={centerX} cy={centerY} r={8} fill="#1e293b" stroke={color} strokeWidth={2.5} />
          <circle cx={centerX} cy={centerY} r={4} fill={color} />
        </g>
      </svg>

      {/* Цифровое значение */}
      <div className="absolute text-center" style={{ bottom: height * 0.1 }}>
        <div
          className="font-bold font-mono leading-none transition-all duration-150"
          style={{
            fontSize,
            color,
            textShadow: `0 0 25px ${color}50`,
          }}
        >
          {displayValue.toFixed(0)}
        </div>
        <div className="text-surface-500 font-medium mt-1" style={{ fontSize: unitSize }}>
          {unit}
        </div>
        <div className="text-surface-400 uppercase tracking-wider mt-1.5" style={{ fontSize: labelSize }}>
          {label}
        </div>
      </div>
    </div>
  )
}