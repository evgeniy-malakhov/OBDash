import { useState } from 'react'
import { useAppStore } from '@/stores/appStore'
import { wsService } from '@/services/websocket'
import { api } from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import {
  Settings,
  Wifi,
  Server,
  Clock,
  Activity,
  Save,
  RotateCcw,
  Terminal,
  Info,
  Trash2,
} from 'lucide-react'

export function SettingsPage() {
  const { connected, device, systemInfo } = useAppStore()
  const [commandInput, setCommandInput] = useState('')
  const [commandResult, setCommandResult] = useState<string | null>(null)
  const [commandLoading, setCommandLoading] = useState(false)

  // Выполнить сырую команду
  const executeRawCommand = async () => {
    if (!commandInput.trim()) return
    setCommandLoading(true)
    setCommandResult(null)

    try {
      const result = await api.executeCommand(commandInput.trim())
      setCommandResult(result.response || result.error || 'Нет ответа')
    } catch (e: any) {
      setCommandResult(`Ошибка: ${e.message}`)
    } finally {
      setCommandLoading(false)
    }
  }

  // WebSocket статус
  const wsStatus = wsService.isConnected()

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold text-white">Настройки</h2>
        <p className="text-surface-400 mt-1">Конфигурация и информация о системе</p>
      </div>

      {/* Системная информация */}
      <Card className="!p-5">
        <div className="flex items-center gap-3 mb-4">
          <Info className="w-5 h-5 text-primary-400" />
          <h3 className="font-medium text-surface-200">Системная информация</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <InfoItem label="Версия API" value={systemInfo?.version || 'N/A'} />
          <InfoItem label="WebSocket" value={wsStatus ? 'Online' : 'Offline'}
            color={wsStatus ? 'text-emerald-400' : 'text-red-400'} />
          <InfoItem label="Устройство" value={connected ? 'Подключено' : 'Отключено'}
            color={connected ? 'text-emerald-400' : 'text-red-400'} />
          <InfoItem label="Мониторинг" value={systemInfo?.monitor_active ? 'Активен' : 'Остановлен'} />
        </div>

        {device && (
          <div className="mt-4 pt-4 border-t border-surface-700/30">
            <h4 className="text-sm font-medium text-surface-300 mb-2">Подключенное устройство</h4>
            <div className="grid grid-cols-2 gap-2">
              <InfoItem label="Имя" value={device.name} />
              <InfoItem label="Адрес" value={device.address} />
              <InfoItem label="Протокол" value={device.protocol || 'N/A'} />
              <InfoItem label="Напряжение" value={device.voltage ? `${device.voltage}V` : 'N/A'} />
            </div>
          </div>
        )}
      </Card>

      {/* Статистика */}
      <Card className="!p-5">
        <div className="flex items-center gap-3 mb-4">
          <Activity className="w-5 h-5 text-primary-400" />
          <h3 className="font-medium text-surface-200">Статистика сессии</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <InfoItem label="Команд выполнено" value={String(systemInfo?.commands_executed || 0)} />
          <InfoItem label="Точек данных" value={String(systemInfo?.data_points_collected || 0)} />
          <InfoItem label="Время работы" value={`${Math.round((systemInfo?.uptime || 0) / 60)} мин`} />
          <InfoItem label="Буфер" value={`${systemInfo?.buffer_size || 0} зап.`} />
        </div>
      </Card>

      {/* Консоль команд */}
      <Card className="!p-5">
        <div className="flex items-center gap-3 mb-4">
          <Terminal className="w-5 h-5 text-primary-400" />
          <h3 className="font-medium text-surface-200">Консоль команд</h3>
          <span className="text-xs text-surface-500">
            {connected ? 'Устройство подключено' : 'Устройство не подключено'}
          </span>
        </div>

        <div className="flex gap-3">
          <input
            type="text"
            value={commandInput}
            onChange={(e) => setCommandInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && executeRawCommand()}
            placeholder="ATRV, 01 0C, ATI..."
            disabled={!connected}
            className="flex-1 px-4 py-2.5 rounded-xl bg-surface-800 border border-surface-700 text-surface-200 text-sm font-mono focus:border-primary-500/50 focus:outline-none disabled:opacity-50"
          />
          <Button
            onClick={executeRawCommand}
            disabled={!connected || !commandInput.trim()}
            loading={commandLoading}
          >
            Выполнить
          </Button>
        </div>

        {commandResult !== null && (
          <div className="mt-3 p-3 rounded-lg bg-surface-800/60 border border-surface-700/30">
            <p className="text-xs text-surface-500 mb-1">Ответ:</p>
            <code className="text-sm font-mono text-primary-300 break-all">
              {commandResult}
            </code>
          </div>
        )}

        <div className="mt-3 flex gap-2 flex-wrap">
          {['ATI', 'ATRV', 'ATDP', '01 0C', '01 0D', '01 05', '0100'].map(cmd => (
            <button
              key={cmd}
              onClick={() => setCommandInput(cmd)}
              disabled={!connected}
              className="px-2 py-1 rounded text-[10px] font-mono bg-surface-800/50 text-surface-400 hover:text-primary-300 hover:bg-surface-700/50 transition-colors disabled:opacity-50"
            >
              {cmd}
            </button>
          ))}
        </div>
      </Card>

      {/* Очистка данных */}
      <Card className="!p-5">
        <div className="flex items-center gap-3 mb-4">
          <Trash2 className="w-5 h-5 text-red-400" />
          <h3 className="font-medium text-surface-200">Управление данными</h3>
        </div>

        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={async () => {
              await fetch('/api/v1/monitor/data', { method: 'DELETE' })
            }}
          >
            Очистить буфер данных
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              localStorage.clear()
              window.location.reload()
            }}
          >
            Сбросить кэш
          </Button>
        </div>
      </Card>
    </div>
  )
}

function InfoItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="p-3 rounded-lg bg-surface-800/40 border border-surface-700/20">
      <p className="text-[10px] text-surface-500 uppercase mb-1">{label}</p>
      <p className={`text-sm font-medium ${color || 'text-surface-200'}`}>
        {value}
      </p>
    </div>
  )
}