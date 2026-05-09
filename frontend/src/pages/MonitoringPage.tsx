import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { api } from '@/services/api'
import { wsService } from '@/services/websocket'
import { useAppStore } from '@/stores/appStore'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import {
  Play,
  Square,
  X,
  Activity,
  Gauge,
  Thermometer,
  Zap,
  Droplets,
  Timer,
  Wind,
  Loader2,
  AlertCircle,
  Maximize2,
  Minimize2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  AreaChart,
  ComposedChart,
  ReferenceLine,
} from 'recharts'
import type { PIDValue, WSMessage } from '@/types/obd'

// Конфигурация доступных PID
const availablePids = [
  { pid: '0C', name: 'Обороты', unit: 'RPM', icon: Gauge, color: '#60a5fa', min: 0, max: 8000 },
  { pid: '0D', name: 'Скорость', unit: 'km/h', icon: Activity, color: '#34d399', min: 0, max: 260 },
  { pid: '05', name: 'Темп. ОЖ', unit: '°C', icon: Thermometer, color: '#f97316', min: -40, max: 120 },
  { pid: '0F', name: 'Темп. воздуха', unit: '°C', icon: Wind, color: '#38bdf8', min: -40, max: 80 },
  { pid: '04', name: 'Нагрузка', unit: '%', icon: Activity, color: '#a78bfa', min: 0, max: 100 },
  { pid: '2F', name: 'Топливо', unit: '%', icon: Droplets, color: '#fbbf24', min: 0, max: 100 },
  { pid: '42', name: 'Напряжение', unit: 'V', icon: Zap, color: '#818cf8', min: 0, max: 16 },
  { pid: '0B', name: 'Давл. впуска', unit: 'kPa', icon: Gauge, color: '#fb923c', min: 0, max: 255 },
  { pid: '11', name: 'Дроссель', unit: '%', icon: Activity, color: '#e879f9', min: 0, max: 100 },
  { pid: '1F', name: 'Время работы', unit: 'сек', icon: Timer, color: '#94a3b8', min: 0, max: 65535 },
]

const MAX_DATA_POINTS = 120 // Больше точек для плавности

// Интерфейс для точек данных
interface DataPoint {
  time: string
  timestamp: number
  index: number
  [key: string]: any
}

// Кастомный тултип
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="bg-surface-900/95 backdrop-blur-xl border border-surface-700/50 rounded-xl p-4 shadow-2xl shadow-black/50">
      <p className="text-xs text-surface-400 mb-2 font-medium">{label}</p>
      <div className="space-y-1.5">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-3">
            <div
              className="w-2.5 h-2.5 rounded-full shadow-lg"
              style={{ backgroundColor: entry.color, boxShadow: `0 0 6px ${entry.color}` }}
            />
            <span className="text-xs text-surface-300 flex-1">{entry.name}</span>
            <span className="text-sm font-bold text-white font-mono">
              {typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Кастомная точка
const CustomDot = ({ cx, cy, stroke, payload, value }: any) => {
  // Показываем точки только для крайних значений
  if (!payload || payload.index % 10 !== 0) return null

  return (
    <circle
      cx={cx}
      cy={cy}
      r={3}
      fill={stroke}
      stroke="rgba(0,0,0,0.3)"
      strokeWidth={1}
      style={{ filter: `drop-shadow(0 0 4px ${stroke})` }}
    />
  )
}

export function MonitoringPage() {
  const [selectedPids, setSelectedPids] = useState<string[]>(['0C', '0D', '05'])
  const [monitoring, setMonitoring] = useState(false)
  const [dataPoints, setDataPoints] = useState<DataPoint[]>([])
  const [currentValues, setCurrentValues] = useState<Map<string, PIDValue>>(new Map())
  const [error, setError] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState<string>('')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showGrid, setShowGrid] = useState(true)
  const [animationEnabled, setAnimationEnabled] = useState(true)
  const { connected } = useAppStore()

  const dataPointsRef = useRef<DataPoint[]>([])
  const monitoringRef = useRef(false)
  const pointCounterRef = useRef(0)
  const chartContainerRef = useRef<HTMLDivElement>(null)

  // Синхронизируем ref с state
  useEffect(() => {
    dataPointsRef.current = dataPoints
  }, [dataPoints])

  useEffect(() => {
    monitoringRef.current = monitoring
  }, [monitoring])

  // Обработчик WebSocket сообщений
  useEffect(() => {
    if (!connected) return

    const handleMessage = (message: WSMessage) => {
      if (!monitoringRef.current) return

      let pidArray: PIDValue[] = []

      if (message.type === 'pid_data') {
        if (Array.isArray(message.data?.data)) {
          pidArray = message.data.data
        } else if (Array.isArray(message.data?.pids)) {
          pidArray = message.data.pids
        } else if (Array.isArray(message.data)) {
          pidArray = message.data
        }
      }

      if (Array.isArray(message.data) && message.type !== 'pid_data') {
        pidArray = message.data
      }

      if (pidArray.length > 0) {
        // Обновляем текущие значения
        setCurrentValues(prev => {
          const newMap = new Map(prev)
          pidArray.forEach((pid: PIDValue) => {
            if (pid && pid.pid) {
              newMap.set(pid.pid.toUpperCase(), pid)
            }
          })
          return newMap
        })

        // Добавляем точку на график
        const now = new Date()
        pointCounterRef.current++

        const point: DataPoint = {
          time: now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          timestamp: now.getTime(),
          index: pointCounterRef.current,
        }

        pidArray.forEach((pid: PIDValue) => {
          if (pid && pid.pid) {
            const pidUpper = pid.pid.toUpperCase()
            if (typeof pid.value === 'number') {
              point[pidUpper] = pid.value
            } else if (typeof pid.value === 'string') {
              const num = parseFloat(pid.value)
              if (!isNaN(num)) {
                point[pidUpper] = num
              }
            }
          }
        })

        setDataPoints(prev => {
          const updated = [...prev, point]
          if (updated.length > MAX_DATA_POINTS) {
            return updated.slice(-MAX_DATA_POINTS)
          }
          return updated
        })

        setError(null)
      }
    }

    const unsubData = wsService.onMessage('pid_data', handleMessage)
    const unsubAll = wsService.onMessage('*', (msg) => {
      if (msg.data && (Array.isArray(msg.data) || msg.data.pids || msg.data.data)) {
        handleMessage(msg)
      }
    })
    const unsubError = wsService.onMessage('error', (msg) => {
      setError(msg.data?.error || msg.data?.message || 'Ошибка мониторинга')
    })

    return () => {
      unsubData()
      unsubAll()
      unsubError()
    }
  }, [connected])

  // Запуск мониторинга
  const startMonitoring = useCallback(async () => {
    if (selectedPids.length === 0) {
      setError('Выберите хотя бы один параметр')
      return
    }

    setError(null)
    setDataPoints([])
    setCurrentValues(new Map())
    pointCounterRef.current = 0

    try {
      await api.startMonitoring({ pids: selectedPids, interval: 0.3 })
    } catch (err: any) {
      console.warn('REST start failed:', err.message)
    }

    wsService.send({
      action: 'start_monitor',
      pids: selectedPids,
      interval: 0.3,
    })

    setMonitoring(true)
  }, [selectedPids])

  // Остановка мониторинга
  const stopMonitoring = useCallback(async () => {
    try {
      await api.stopMonitoring()
    } catch {}

    wsService.send({ action: 'stop_monitor' })
    setMonitoring(false)
  }, [])

  // Автозапуск при входе
  useEffect(() => {
    if (connected && !monitoring && selectedPids.length > 0) {
      const timer = setTimeout(() => startMonitoring(), 500)
      return () => clearTimeout(timer)
    }
  }, [connected])

  // Очистка при уходе
  useEffect(() => {
    return () => {
      if (monitoringRef.current) {
        wsService.send({ action: 'stop_monitor' })
      }
    }
  }, [])

  const togglePid = (pid: string) => {
    if (monitoring) return
    setSelectedPids(prev =>
      prev.includes(pid) ? prev.filter(p => p !== pid) : [...prev, pid]
    )
  }

  const selectedConfigs = availablePids.filter(p => selectedPids.includes(p.pid))

  // Вычисляем общий диапазон Y для основного графика
  const yDomain = useMemo(() => {
    if (dataPoints.length === 0) return [0, 100]

    let min = Infinity, max = -Infinity
    dataPoints.forEach(point => {
      selectedPids.forEach(pid => {
        const val = point[pid]
        if (typeof val === 'number') {
          min = Math.min(min, val)
          max = Math.max(max, val)
        }
      })
    })

    const padding = (max - min) * 0.1 || 10
    return [Math.max(0, min - padding), max + padding]
  }, [dataPoints, selectedPids])

  // Форматирование времени для оси X
  const formatXAxis = (time: string) => {
    // Показываем только секунды для компактности
    return time.split(':').slice(1).join(':')
  }

  return (
    <div className="space-y-6">
      {/* Заголовок и управление */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Мониторинг</h2>
          <p className="text-surface-400 mt-1">
            {monitoring ? (
              <span className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                </span>
                Активен • {selectedPids.length} параметров • Обновление: 0.3с
              </span>
            ) : (
              'Графики параметров в реальном времени'
            )}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={cn(
              'px-3 py-2 rounded-xl text-xs border transition-all',
              showGrid
                ? 'bg-surface-800/60 border-surface-600/50 text-surface-300'
                : 'border-surface-700/30 text-surface-500'
            )}
          >
            Сетка
          </button>
          <button
            onClick={() => setAnimationEnabled(!animationEnabled)}
            className={cn(
              'px-3 py-2 rounded-xl text-xs border transition-all',
              animationEnabled
                ? 'bg-surface-800/60 border-surface-600/50 text-surface-300'
                : 'border-surface-700/30 text-surface-500'
            )}
          >
            Анимация
          </button>
          {!monitoring ? (
            <Button
              onClick={startMonitoring}
              disabled={selectedPids.length === 0}
              icon={<Play className="w-4 h-4" />}
              variant="success"
            >
              Запустить
            </Button>
          ) : (
            <Button
              onClick={stopMonitoring}
              icon={<Square className="w-4 h-4" />}
              variant="danger"
            >
              Остановить
            </Button>
          )}
        </div>
      </div>

      {/* Ошибка */}
      {error && (
        <Card className="!p-4 border-red-500/30 bg-red-500/5">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-red-400 text-sm flex-1">{error}</p>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
              <X className="w-5 h-5" />
            </button>
          </div>
        </Card>
      )}

      {/* Текущие значения */}
      {currentValues.size > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {selectedConfigs.map(config => {
            const value = currentValues.get(config.pid)
            const numValue = value ? (typeof value.value === 'number' ? value.value : parseFloat(value.value)) : null
            const percentage = numValue !== null
              ? Math.min(100, Math.max(0, ((numValue - config.min) / (config.max - config.min)) * 100))
              : 0

            return (
              <Card
                key={config.pid}
                className="!p-4 text-center transition-all duration-300 hover:scale-[1.02]"
                style={{ borderColor: `${config.color}20` }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center mx-auto mb-2 transition-transform"
                  style={{ backgroundColor: `${config.color}20` }}
                >
                  <config.icon className="w-4 h-4" style={{ color: config.color }} />
                </div>
                <p className="text-[10px] text-surface-500 uppercase truncate">{config.name}</p>
                <p
                  className="text-xl font-bold font-mono text-white mt-1 transition-all duration-300"
                  style={{
                    textShadow: `0 0 10px ${config.color}40`,
                  }}
                >
                  {numValue !== null ? numValue.toFixed(1) : '--'}
                </p>
                <p className="text-[10px] text-surface-500">{config.unit}</p>

                {/* Шкала с градиентом */}
                <div className="mt-2 h-1.5 rounded-full bg-surface-700/50 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${percentage}%`,
                      background: `linear-gradient(90deg, ${config.color}80, ${config.color})`,
                      boxShadow: `0 0 8px ${config.color}40`,
                    }}
                  />
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* График */}
      <Card
        ref={chartContainerRef}
        className={cn(
          '!p-5 transition-all duration-500',
          isFullscreen && 'fixed inset-4 z-50 !p-6 shadow-2xl'
        )}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-medium text-surface-200">График в реальном времени</h3>
            <p className="text-xs text-surface-500 mt-0.5">
              {dataPoints.length > 0
                ? `Отображается ${dataPoints.length} точек`
                : 'Ожидание данных...'}
            </p>
          </div>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 rounded-lg hover:bg-surface-800/50 text-surface-400 hover:text-surface-200 transition-colors"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>

        {dataPoints.length > 0 ? (
          <ResponsiveContainer width="100%" height={isFullscreen ? window.innerHeight - 200 : 400}>
            <ComposedChart data={dataPoints}>
              {/* Градиенты для областей */}
              <defs>
                {selectedConfigs.map(config => (
                  <linearGradient key={config.pid} id={`gradient-${config.pid}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={config.color} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={config.color} stopOpacity={0.02} />
                  </linearGradient>
                ))}
                {/* Градиент для свечения */}
                <filter id="glow">
                  <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {showGrid && (
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(148,163,184,0.08)"
                  vertical={false}
                />
              )}

              <XAxis
                dataKey="time"
                stroke="#475569"
                fontSize={10}
                tickLine={false}
                axisLine={{ stroke: 'rgba(148,163,184,0.15)' }}
                tickFormatter={formatXAxis}
                interval="preserveStartEnd"
                minTickGap={30}
              />

              <YAxis
                stroke="#475569"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={yDomain}
                tickFormatter={(value) => {
                  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`
                  return value.toString()
                }}
                width={45}
              />

              <Tooltip content={<CustomTooltip />} />

              <Legend
                wrapperStyle={{
                  paddingTop: '16px',
                  fontSize: '11px',
                }}
                iconType="circle"
                iconSize={8}
              />

              {selectedConfigs.map((config, index) => (
                <Area
                  key={`area-${config.pid}`}
                  type="monotone"
                  dataKey={config.pid}
                  stroke="none"
                  fill={`url(#gradient-${config.pid})`}
                  animationDuration={animationEnabled ? 300 : 0}
                />
              ))}

              {selectedConfigs.map((config, index) => (
                <Line
                  key={`line-${config.pid}`}
                  type="monotone"
                  dataKey={config.pid}
                  stroke={config.color}
                  strokeWidth={2}
                  dot={<CustomDot />}
                  activeDot={{
                    r: 5,
                    fill: config.color,
                    stroke: '#fff',
                    strokeWidth: 2,
                    style: { filter: `drop-shadow(0 0 8px ${config.color})` },
                  }}
                  name={`${config.name} (${config.unit})`}
                  animationDuration={animationEnabled ? 300 : 0}
                  animationEasing="ease-in-out"
                  connectNulls
                  style={{ filter: `drop-shadow(0 0 3px ${config.color}40)` }}
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className={cn(
            'flex flex-col items-center justify-center text-surface-500 border-2 border-dashed border-surface-700/30 rounded-xl transition-all',
            isFullscreen ? 'h-[calc(100vh-250px)]' : 'h-[400px]'
          )}>
            {monitoring ? (
              <>
                <div className="relative">
                  <Loader2 className="w-10 h-10 text-primary-400 animate-spin mb-4" />
                  <div className="absolute inset-0 rounded-full border-2 border-primary-500/20 animate-ping" />
                </div>
                <p className="text-lg font-medium">Сбор данных...</p>
                <p className="text-sm mt-1">Ожидание первых показаний</p>
              </>
            ) : (
              <>
                <Activity className="w-14 h-14 text-surface-600 mb-4" />
                <p className="text-lg font-medium">Нет данных</p>
                <p className="text-sm mt-1">Нажмите "Запустить" для начала</p>
              </>
            )}
          </div>
        )}
      </Card>

      {/* Последние значения */}
      {dataPoints.length > 0 && (
        <Card className="!p-5">
          <h3 className="font-medium text-surface-200 mb-4">Последние значения</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-700/30">
                  <th className="text-left p-2.5 text-xs text-surface-500 font-medium">Время</th>
                  {selectedConfigs.map(config => (
                    <th key={config.pid} className="text-right p-2.5 text-xs text-surface-500 font-medium">
                      <span className="flex items-center justify-end gap-1.5">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
                        {config.name}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataPoints.slice(-10).reverse().map((point, idx) => (
                  <tr
                    key={point.index}
                    className={cn(
                      'border-b border-surface-700/20 last:border-0 transition-colors hover:bg-surface-800/20',
                      idx === 0 && 'bg-primary-500/5'
                    )}
                  >
                    <td className="p-2.5 text-surface-400 font-mono text-xs">{point.time}</td>
                    {selectedConfigs.map(config => (
                      <td
                        key={config.pid}
                        className={cn(
                          'p-2.5 text-right font-mono text-xs font-medium transition-all duration-300',
                          idx === 0 ? 'text-white' : 'text-surface-300'
                        )}
                      >
                        {point[config.pid] !== undefined
                          ? Number(point[config.pid]).toFixed(1)
                          : '--'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Выбор PID */}
      <Card className="!p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-surface-200">
            Параметры ({selectedPids.length} выбрано)
          </h3>
          {selectedPids.length > 0 && !monitoring && (
            <button
              onClick={() => setSelectedPids([])}
              className="text-xs text-surface-400 hover:text-primary-400 transition-colors"
            >
              Сбросить всё
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {availablePids.map(({ pid, name, icon: Icon, color }) => {
            const isSelected = selectedPids.includes(pid)
            return (
              <button
                key={pid}
                onClick={() => togglePid(pid)}
                disabled={monitoring}
                className={cn(
                  'flex items-center gap-2 px-3 py-2.5 rounded-xl border transition-all duration-300 text-sm',
                  monitoring && 'opacity-50 cursor-not-allowed',
                  isSelected
                    ? 'shadow-lg hover:shadow-xl'
                    : 'border-surface-700/30 bg-surface-800/30 hover:border-surface-600/50 hover:bg-surface-800/50'
                )}
                style={{
                  borderColor: isSelected ? color : undefined,
                  backgroundColor: isSelected ? `${color}12` : undefined,
                }}
              >
                <Icon
                  className="w-4 h-4 flex-shrink-0 transition-colors"
                  style={{ color: isSelected ? color : '#64748b' }}
                />
                <span
                  className="truncate text-xs font-medium transition-colors"
                  style={{ color: isSelected ? '#e2e8f0' : '#94a3b8' }}
                >
                  {name}
                </span>
                {isSelected && !monitoring && (
                  <X className="w-3 h-3 ml-auto flex-shrink-0 opacity-60" style={{ color }} />
                )}
                {isSelected && monitoring && (
                  <div
                    className="w-2 h-2 rounded-full ml-auto flex-shrink-0"
                    style={{
                      backgroundColor: color,
                      boxShadow: `0 0 6px ${color}`,
                      animation: 'pulse 2s infinite',
                    }}
                  />
                )}
              </button>
            )
          })}
        </div>
      </Card>
    </div>
  )
}