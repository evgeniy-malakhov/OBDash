import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface TachometerProps {
  value: number
  max?: number
  redline?: number
  shiftLight?: number
  className?: string
}

export function Tachometer({
  value,
  max = 8000,
  redline = 6500,
  shiftLight = 6000,
  className,
}: TachometerProps) {
  const [angle, setAngle] = useState(-130)
  const angleRef = useRef(-130)
  const requestRef = useRef<number>()
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const startAngle = -130
  const endAngle = 130
  const totalAngle = endAngle - startAngle
  const targetAngle = startAngle + (Math.min(value, max) / max) * totalAngle

  // Плавная анимация стрелки
  useEffect(() => {
    const animate = () => {
      const diff = targetAngle - angleRef.current
      angleRef.current += diff * 0.06

      if (Math.abs(diff) > 0.05) {
        setAngle(angleRef.current)
        requestRef.current = requestAnimationFrame(animate)
      } else {
        angleRef.current = targetAngle
        setAngle(targetAngle)
      }
    }

    requestRef.current = requestAnimationFrame(animate)
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current)
    }
  }, [targetAngle])

  // Отрисовка на canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const cx = rect.width / 2
    const cy = rect.height * 0.78
    const radius = Math.min(cx, cy) * 0.72

    ctx.clearRect(0, 0, rect.width, rect.height)

    // Фоновая дуга
    ctx.beginPath()
    ctx.arc(cx, cy, radius - 4, (startAngle - 90) * Math.PI / 180, (endAngle - 90) * Math.PI / 180)
    ctx.strokeStyle = 'rgba(148,163,184,0.08)'
    ctx.lineWidth = 16
    ctx.lineCap = 'round'
    ctx.stroke()

    // Красная зона
    const redStart = startAngle + (redline / max) * totalAngle
    ctx.beginPath()
    ctx.arc(cx, cy, radius - 4, (redStart - 90) * Math.PI / 180, (endAngle - 90) * Math.PI / 180)
    ctx.strokeStyle = 'rgba(239,68,68,0.15)'
    ctx.lineWidth = 16
    ctx.lineCap = 'round'
    ctx.stroke()

    // Жёлтая зона
    const yellowStart = startAngle + (shiftLight / max) * totalAngle
    ctx.beginPath()
    ctx.arc(cx, cy, radius - 4, (yellowStart - 90) * Math.PI / 180, (redStart - 90) * Math.PI / 180)
    ctx.strokeStyle = 'rgba(251,191,36,0.12)'
    ctx.lineWidth = 16
    ctx.lineCap = 'round'
    ctx.stroke()

    // Деления
    const numTicks = 40
    for (let i = 0; i <= numTicks; i++) {
      const tickAngle = startAngle + (i / numTicks) * totalAngle
      const rad = (tickAngle - 90) * Math.PI / 180
      const isMain = i % 10 === 0
      const isHalf = i % 5 === 0
      const tickValue = (i / numTicks) * max

      let tickColor = 'rgba(148,163,184,0.3)'
      let tickWidth = 1
      let innerR = radius - 12
      const outerR = radius - 4

      if (isMain) {
        tickWidth = 3
        innerR = radius - 26
        tickColor = 'rgba(226,232,240,0.9)'
      } else if (isHalf) {
        tickWidth = 2
        innerR = radius - 20
        tickColor = 'rgba(148,163,184,0.6)'
      }

      // Цветовые зоны
      if (tickValue >= redline) {
        tickColor = 'rgba(239,68,68,0.9)'
      } else if (tickValue >= shiftLight) {
        tickColor = 'rgba(251,191,36,0.9)'
      }

      const x1 = cx + innerR * Math.cos(rad)
      const y1 = cy + innerR * Math.sin(rad)
      const x2 = cx + outerR * Math.cos(rad)
      const y2 = cy + outerR * Math.sin(rad)

      ctx.beginPath()
      ctx.moveTo(x1, y1)
      ctx.lineTo(x2, y2)
      ctx.strokeStyle = tickColor
      ctx.lineWidth = tickWidth
      ctx.lineCap = 'round'
      ctx.stroke()

      // Подписи (каждые 1000 RPM)
      if (isMain) {
        const labelR = innerR - 22
        const lx = cx + labelR * Math.cos(rad)
        const ly = cy + labelR * Math.sin(rad)
        ctx.fillStyle = tickValue >= redline ? 'rgba(239,68,68,0.9)' : 'rgba(203,213,225,0.9)'
        ctx.font = 'bold 12px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(`${Math.round(tickValue / 1000)}`, lx, ly)
      }
    }

    // Стрелка
    const needleRad = (angle - 90) * Math.PI / 180
    const needleLen = radius * 0.62

    // Тень стрелки
    ctx.beginPath()
    ctx.moveTo(cx + 1, cy + 1)
    ctx.lineTo(
      cx + needleLen * Math.cos(needleRad) + 1,
      cy + needleLen * Math.sin(needleRad) + 1
    )
    ctx.strokeStyle = 'rgba(0,0,0,0.4)'
    ctx.lineWidth = 4
    ctx.lineCap = 'round'
    ctx.stroke()

    // Основная стрелка
    const inRed = angle >= startAngle + (redline / max) * totalAngle
    const inYellow = angle >= startAngle + (shiftLight / max) * totalAngle && !inRed

    let needleColor = '#f97316'
    if (inRed) needleColor = '#ef4444'
    else if (inYellow) needleColor = '#fbbf24'

    const gradient = ctx.createLinearGradient(
      cx, cy,
      cx + needleLen * Math.cos(needleRad),
      cy + needleLen * Math.sin(needleRad)
    )
    gradient.addColorStop(0, '#ffffff')
    gradient.addColorStop(0.3, needleColor)
    gradient.addColorStop(1, needleColor)

    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(
      cx + needleLen * Math.cos(needleRad),
      cy + needleLen * Math.sin(needleRad)
    )
    ctx.strokeStyle = gradient
    ctx.lineWidth = 2.5
    ctx.lineCap = 'round'
    ctx.shadowColor = inRed ? 'rgba(239,68,68,0.8)' : inYellow ? 'rgba(251,191,36,0.6)' : 'rgba(249,115,22,0.5)'
    ctx.shadowBlur = 15
    ctx.stroke()
    ctx.shadowBlur = 0

    // Центральная точка
    ctx.beginPath()
    ctx.arc(cx, cy, 9, 0, Math.PI * 2)
    ctx.fillStyle = '#0f172a'
    ctx.fill()
    ctx.strokeStyle = needleColor
    ctx.lineWidth = 2.5
    ctx.stroke()

    ctx.beginPath()
    ctx.arc(cx, cy, 4, 0, Math.PI * 2)
    ctx.fillStyle = needleColor
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1
    ctx.stroke()

  }, [angle, redline, shiftLight, max, startAngle, endAngle, totalAngle])

  return (
    <div className={cn('relative w-full max-w-[320px] mx-auto', className)}>
      <canvas
        ref={canvasRef}
        className="w-full aspect-[4/3]"
      />
    </div>
  )
}