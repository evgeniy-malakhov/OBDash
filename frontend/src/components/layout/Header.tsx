import { useAppStore } from '@/stores/appStore'
import { wsService } from '@/services/websocket'
import { api } from '@/services/api'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { Wifi, WifiOff, Activity, Clock, Zap, Cpu } from 'lucide-react'
import { useEffect, useState } from 'react'

export function Header() {
  const { connected, device, wsConnected, systemInfo, setSystemInfo } = useAppStore()
  const [currentTime, setCurrentTime] = useState(new Date())

  // Запрос системной информации
  const { data: sysInfo } = useQuery({
    queryKey: ['systemInfo'],
    queryFn: () => api.getSystemInfo(),
    refetchInterval: 5000,
    enabled: connected,
  })

  useEffect(() => {
    if (sysInfo) {
      setSystemInfo(sysInfo)
    }
  }, [sysInfo, setSystemInfo])

  // Часы
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="h-16 border-b border-surface-700/30 bg-surface-900/50 backdrop-blur-xl flex items-center justify-between px-6 flex-shrink-0">
      {/* Левая часть - хлебные крошки */}
      <div className="flex items-center gap-3">
        {device && connected && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-500/10 border border-primary-500/20 flex items-center justify-center">
              <Activity className="w-4 h-4 text-primary-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-200">{device.name}</p>
              <p className="text-[10px] text-surface-500">
                {device.protocol && `Протокол: ${device.protocol}`}
              </p>
            </div>
          </div>
        )}
        {!connected && (
          <p className="text-surface-400 text-sm">Не подключено</p>
        )}
      </div>

      {/* Правая часть - статусы */}
      <div className="flex items-center gap-4">
        {/* Время */}
        <div className="flex items-center gap-2 text-sm text-surface-400">
          <Clock className="w-4 h-4" />
          <span>{currentTime.toLocaleTimeString()}</span>
        </div>

        {/* WebSocket статус */}
        <div className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border',
          wsConnected
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : 'bg-red-500/10 text-red-400 border-red-500/20'
        )}>
          {wsConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          WS
        </div>

        {/* Статистика */}
        {systemInfo && (
          <div className="flex items-center gap-3 text-xs text-surface-500">
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3" />
              {systemInfo.commands_executed} ком.
            </span>
            <span className="flex items-center gap-1">
              <Zap className="w-3 h-3" />
              {systemInfo.data_points_collected} точ.
            </span>
          </div>
        )}
      </div>
    </header>
  )
}