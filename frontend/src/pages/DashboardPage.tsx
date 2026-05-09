import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { wsService } from '@/services/websocket'
import { useAppStore } from '@/stores/appStore'
import { useEffect, useState, useCallback } from 'react'
import Card from '@/components/ui/Card'
import {
  Gauge,
  Thermometer,
  Activity,
  Zap,
  Droplets,
  Wind,
  Timer,
  Fuel,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PIDValue } from '@/types/obd'

interface GaugeConfig {
  pid: string
  name: string
  unit: string
  icon: any
  color: string
  min: number
  max: number
  warningMin?: number
  warningMax?: number
}

const gauges: GaugeConfig[] = [
  { pid: '0C', name: 'Обороты', unit: 'RPM', icon: Gauge, color: 'from-blue-500 to-cyan-400', min: 0, max: 8000, warningMax: 6000 },
  { pid: '0D', name: 'Скорость', unit: 'km/h', icon: Activity, color: 'from-emerald-500 to-green-400', min: 0, max: 260 },
  { pid: '05', name: 'Темп. ОЖ', unit: '°C', icon: Thermometer, color: 'from-orange-500 to-red-400', min: -40, max: 120, warningMax: 105 },
  { pid: '0F', name: 'Темп. воздуха', unit: '°C', icon: Wind, color: 'from-sky-500 to-blue-400', min: -40, max: 80 },
  { pid: '2F', name: 'Топливо', unit: '%', icon: Fuel, color: 'from-amber-500 to-yellow-400', min: 0, max: 100, warningMin: 15 },
  { pid: '42', name: 'Напряжение', unit: 'V', icon: Zap, color: 'from-purple-500 to-violet-400', min: 0, max: 16, warningMin: 11.5 },
]

export function DashboardPage() {
  const [pidData, setPidData] = useState<Map<string, PIDValue>>(new Map())
  const { connected } = useAppStore()

  // Запрос начальных данных
  const { data: initialData } = useQuery({
    queryKey: ['dashboardPids'],
    queryFn: () => api.readPIDs(gauges.map(g => g.pid)),
    refetchInterval: 2000,
    enabled: connected,
  })

  useEffect(() => {
    if (initialData) {
      const newMap = new Map<string, PIDValue>()
      initialData.forEach((pid: PIDValue) => {
        newMap.set(pid.pid, pid)
      })
      setPidData(newMap)
    }
  }, [initialData])

  // WebSocket для real-time обновлений
  useEffect(() => {
    if (!connected) return

    const unsub = wsService.onMessage('pid_data', (message) => {
      const pids = message.data?.data || message.data?.pids || []
      if (Array.isArray(pids)) {
        setPidData(prev => {
          const newMap = new Map(prev)
          pids.forEach((pid: PIDValue) => {
            newMap.set(pid.pid, pid)
          })
          return newMap
        })
      }
    })

    // Запускаем мониторинг
    wsService.send({
      action: 'start_monitor',
      pids: gauges.map(g => g.pid),
      interval: 1.0,
    })

    return () => {
      unsub()
      wsService.send({ action: 'stop_monitor' })
    }
  }, [connected])

  // Функция для отрисовки шкалы
  const renderGauge = (config: GaugeConfig, value: PIDValue | undefined) => {
    const val = value?.value ?? 0
    const percentage = Math.min(100, Math.max(0, ((val - config.min) / (config.max - config.min)) * 100))

    const isWarning = value?.status === 'WARNING' ||
      (config.warningMin && val < config.warningMin) ||
      (config.warningMax && val > config.warningMax)

    return (
      <Card
        key={config.pid}
        className={cn(
          'relative overflow-hidden transition-all duration-300 hover:scale-[1.02]',
          isWarning && 'border-red-500/30'
        )}
      >
        {/* Фоновый градиент */}
        <div className={cn(
          'absolute inset-0 opacity-10 bg-gradient-to-br',
          config.color
        )} />

        <div className="relative space-y-4">
          {/* Заголовок */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={cn(
                'w-8 h-8 rounded-lg flex items-center justify-center',
                'bg-surface-800/60 border border-surface-700/30'
              )}>
                <config.icon className="w-4 h-4 text-surface-300" />
              </div>
              <span className="text-sm font-medium text-surface-400">{config.name}</span>
            </div>
            {value?.status === 'WARNING' && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                ВНИМАНИЕ
              </span>
            )}
          </div>

          {/* Значение */}
          <div className="text-center">
            <span className={cn(
              'text-4xl font-bold font-mono',
              isWarning ? 'text-red-400' : 'text-white'
            )}>
              {typeof val === 'number' ? val.toFixed(1) : val}
            </span>
            <span className="text-lg text-surface-500 ml-1">{config.unit}</span>
          </div>

          {/* Шкала */}
          <div className="relative h-2 rounded-full bg-surface-700/50 overflow-hidden">
            <div
              className={cn(
                'absolute inset-y-0 left-0 rounded-full transition-all duration-500 bg-gradient-to-r',
                config.color,
                isWarning && 'from-red-500 to-red-400'
              )}
              style={{ width: `${percentage}%` }}
            />
            {/* Метки предупреждений */}
            {config.warningMax && (
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-red-400/50"
                style={{ left: `${((config.warningMax - config.min) / (config.max - config.min)) * 100}%` }}
              />
            )}
          </div>

          {/* Мин/Макс */}
          <div className="flex justify-between text-[10px] text-surface-600">
            <span>{config.min}</span>
            <span>{config.max}</span>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Приборная панель</h2>
        <p className="text-surface-400 mt-1">Основные показатели в реальном времени</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {gauges.map(config => renderGauge(config, pidData.get(config.pid)))}
      </div>

      {/* Дополнительная информация */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <h3 className="text-sm font-medium text-surface-400 mb-3">Данные в реальном времени</h3>
          <div className="space-y-2">
            {Array.from(pidData.entries()).map(([pid, value]) => (
              <div key={pid} className="flex items-center justify-between py-1.5 border-b border-surface-700/20 last:border-0">
                <span className="text-sm text-surface-300">{value.name}</span>
                <span className="text-sm font-mono font-medium text-white">
                  {typeof value.value === 'number' ? value.value.toFixed(1) : value.value}
                  <span className="text-surface-500 ml-1">{value.unit}</span>
                </span>
              </div>
            ))}
            {pidData.size === 0 && (
              <p className="text-surface-500 text-sm text-center py-4">Ожидание данных...</p>
            )}
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-surface-400 mb-3">Системная информация</h3>
          <div className="space-y-3">
            <SystemInfoRow label="Устройство" value={useAppStore.getState().device?.name || 'N/A'} />
            <SystemInfoRow label="Протокол" value={useAppStore.getState().device?.protocol || 'N/A'} />
            <SystemInfoRow label="Напряжение" value={`${useAppStore.getState().device?.voltage || 'N/A'}V`} />
            <SystemInfoRow label="Команд выполнено" value={String(useAppStore.getState().systemInfo?.commands_executed || 0)} />
            <SystemInfoRow label="Точек данных" value={String(useAppStore.getState().systemInfo?.data_points_collected || 0)} />
          </div>
        </Card>
      </div>
    </div>
  )
}

function SystemInfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-surface-700/20 last:border-0">
      <span className="text-sm text-surface-400">{label}</span>
      <span className="text-sm font-medium text-surface-200">{value}</span>
    </div>
  )
}