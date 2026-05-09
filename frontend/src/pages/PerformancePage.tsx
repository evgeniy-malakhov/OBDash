// frontend/src/pages/PerformancePage.tsx
import { useState, useEffect, useRef } from 'react'
import { usePidData } from '@/hooks/usePidData'
import { useAppStore } from '@/stores/appStore'
import { Card } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import {
  Timer,
  Gauge,
  Zap,
  TrendingUp,
  RotateCcw,
  Flag,
  Play,
  Square,
  Trophy,
} from 'lucide-react'

interface PerformanceMetrics {
  '0-60': number | null
  '0-100': number | null
  '60-120': number | null
  '1/4 mile': number | null
  maxSpeed: number
  maxRPM: number
  maxLoad: number
}

export function PerformancePage() {
  const { connected } = useAppStore()
  const { getNumericValue } = usePidData(['0C', '0D', '04'], connected)

  const [recording, setRecording] = useState(false)
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    '0-60': null,
    '0-100': null,
    '60-120': null,
    '1/4 mile': null,
    maxSpeed: 0,
    maxRPM: 0,
    maxLoad: 0,
  })

  const [currentTest, setCurrentTest] = useState<string | null>(null)
  const [testProgress, setTestProgress] = useState(0)
  const [testResult, setTestResult] = useState<number | null>(null)

  const startTimeRef = useRef<number>(0)
  const dataLogRef = useRef<Array<{ time: number; speed: number; rpm: number }>>([])
  const animationRef = useRef<number>()

  const speed = getNumericValue('0D') || 0
  const rpm = getNumericValue('0C') || 0
  const load = getNumericValue('04') || 0

  // Обновление максимальных значений
  useEffect(() => {
    if (speed > metrics.maxSpeed) {
      setMetrics(prev => ({ ...prev, maxSpeed: speed }))
    }
    if (rpm > metrics.maxRPM) {
      setMetrics(prev => ({ ...prev, maxRPM: rpm }))
    }
    if (load > metrics.maxLoad) {
      setMetrics(prev => ({ ...prev, maxLoad: load }))
    }
  }, [speed, rpm, load])

  // Логирование данных во время записи
  useEffect(() => {
    if (recording) {
      dataLogRef.current.push({
        time: performance.now(),
        speed,
        rpm,
      })
    }
  }, [speed, rpm, recording])

  // Замер разгона
  const startAccelerationTest = (testName: string, startCondition: number, endCondition: number) => {
    setCurrentTest(testName)
    setTestResult(null)
    setTestProgress(0)
    startTimeRef.current = 0

    const checkCondition = () => {
      const currentSpeed = getNumericValue('0D') || 0

      if (!startTimeRef.current && currentSpeed <= startCondition + 1) {
        startTimeRef.current = performance.now()
      }

      if (startTimeRef.current) {
        const elapsed = (performance.now() - startTimeRef.current) / 1000
        const progress = Math.min(100, ((currentSpeed - startCondition) / (endCondition - startCondition)) * 100)
        setTestProgress(progress)

        if (currentSpeed >= endCondition) {
          setTestResult(elapsed)
          setMetrics(prev => ({ ...prev, [testName]: elapsed }))
          setCurrentTest(null)
          return
        }
      }

      if (currentTest === testName) {
        animationRef.current = requestAnimationFrame(checkCondition)
      }
    }

    animationRef.current = requestAnimationFrame(checkCondition)
  }

  const stopTest = () => {
    setCurrentTest(null)
    setTestProgress(0)
    if (animationRef.current) cancelAnimationFrame(animationRef.current)
  }

  const resetMetrics = () => {
    setMetrics({
      '0-60': null,
      '0-100': null,
      '60-120': null,
      '1/4 mile': null,
      maxSpeed: 0,
      maxRPM: 0,
      maxLoad: 0,
    })
    dataLogRef.current = []
  }

  const tests = [
    { name: '0-60', label: '0-60 км/ч', icon: Timer, color: '#34d399', start: 0, end: 60 },
    { name: '0-100', label: '0-100 км/ч', icon: Gauge, color: '#60a5fa', start: 0, end: 100 },
    { name: '60-120', label: '60-120 км/ч', icon: TrendingUp, color: '#f97316', start: 60, end: 120 },
  ]

  return (
    <div className="space-y-6 page-enter">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Замеры производительности</h2>
          <p className="text-surface-400 mt-1">Тесты разгона и максимальные показатели</p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={resetMetrics} icon={<RotateCcw className="w-4 h-4" />}>
            Сброс
          </Button>
          <Button
            variant={recording ? 'danger' : 'primary'}
            onClick={() => setRecording(!recording)}
            icon={recording ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          >
            {recording ? 'Стоп' : 'Запись'}
          </Button>
        </div>
      </div>

      {/* Текущие показатели */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="!p-4 text-center">
          <p className="text-xs text-surface-500 uppercase mb-1">Скорость</p>
          <p className="text-3xl font-bold font-mono text-white">{speed.toFixed(1)}</p>
          <p className="text-xs text-surface-500">km/h</p>
        </Card>
        <Card className="!p-4 text-center">
          <p className="text-xs text-surface-500 uppercase mb-1">Обороты</p>
          <p className="text-3xl font-bold font-mono text-white">{Math.round(rpm)}</p>
          <p className="text-xs text-surface-500">RPM</p>
        </Card>
        <Card className="!p-4 text-center">
          <p className="text-xs text-surface-500 uppercase mb-1">Нагрузка</p>
          <p className="text-3xl font-bold font-mono text-white">{load.toFixed(1)}</p>
          <p className="text-xs text-surface-500">%</p>
        </Card>
      </div>

      {/* Тесты разгона */}
      <div>
        <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-3">
          Тесты разгона
        </h3>
        <div className="grid grid-cols-3 gap-4">
          {tests.map(test => (
            <Card key={test.name} className="!p-5 text-center relative overflow-hidden">
              <test.icon className="w-8 h-8 mx-auto mb-3" style={{ color: test.color }} />
              <h4 className="text-lg font-bold text-white">{test.label}</h4>

              {metrics[test.name as keyof PerformanceMetrics] !== null ? (
                <div className="mt-3">
                  <span className="text-3xl font-bold font-mono" style={{ color: test.color }}>
                    {(metrics[test.name as keyof PerformanceMetrics] as number).toFixed(2)}
                  </span>
                  <span className="text-surface-500 text-sm ml-1">сек</span>
                </div>
              ) : currentTest === test.name ? (
                <div className="mt-3 space-y-2">
                  <div className="h-2 rounded-full bg-surface-700/50 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${testProgress}%`,
                        background: `linear-gradient(90deg, ${test.color}80, ${test.color})`,
                      }}
                    />
                  </div>
                  <p className="text-xs text-surface-400 animate-pulse">Замер...</p>
                </div>
              ) : (
                <p className="text-surface-500 text-sm mt-3">Не измерено</p>
              )}

              <Button
                size="sm"
                variant="ghost"
                className="mt-3"
                onClick={() => {
                  if (currentTest === test.name) {
                    stopTest()
                  } else {
                    startAccelerationTest(test.name, test.start, test.end)
                  }
                }}
                disabled={currentTest !== null && currentTest !== test.name}
              >
                {currentTest === test.name ? 'Стоп' : 'Старт'}
              </Button>
            </Card>
          ))}
        </div>
      </div>

      {/* Максимальные значения */}
      <div>
        <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-3">
          Максимальные значения
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <Card className="!p-4 text-center">
            <Trophy className="w-6 h-6 text-amber-400 mx-auto mb-2" />
            <p className="text-xs text-surface-500 uppercase">Макс. скорость</p>
            <p className="text-2xl font-bold font-mono text-white mt-1">
              {metrics.maxSpeed.toFixed(1)}
            </p>
            <p className="text-xs text-surface-500">km/h</p>
          </Card>
          <Card className="!p-4 text-center">
            <Trophy className="w-6 h-6 text-amber-400 mx-auto mb-2" />
            <p className="text-xs text-surface-500 uppercase">Макс. обороты</p>
            <p className="text-2xl font-bold font-mono text-white mt-1">
              {Math.round(metrics.maxRPM)}
            </p>
            <p className="text-xs text-surface-500">RPM</p>
          </Card>
          <Card className="!p-4 text-center">
            <Trophy className="w-6 h-6 text-amber-400 mx-auto mb-2" />
            <p className="text-xs text-surface-500 uppercase">Макс. нагрузка</p>
            <p className="text-2xl font-bold font-mono text-white mt-1">
              {metrics.maxLoad.toFixed(1)}
            </p>
            <p className="text-xs text-surface-500">%</p>
          </Card>
        </div>
      </div>
    </div>
  )
}