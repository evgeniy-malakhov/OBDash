import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { useNavigate } from 'react-router-dom'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import {
  Search,
  Wifi,
  Plug,
  Server,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Bluetooth,
  Usb,
  Globe,
  Terminal,
  ChevronRight,
  Zap,
  Cpu,
  Signal,
  ArrowRight,
  Power,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConnectionType, Device } from '@/types/obd'

const connectionTypes: { type: ConnectionType; icon: any; label: string; description: string }[] = [
  { type: 'bluetooth', icon: Bluetooth, label: 'Bluetooth', description: 'Беспроводное BLE' },
  { type: 'wifi', icon: Wifi, label: 'WiFi', description: 'Локальная сеть' },
  { type: 'serial', icon: Usb, label: 'Serial', description: 'USB провод' },
]

export function ConnectionPage() {
  const [selectedTypes, setSelectedTypes] = useState<ConnectionType[]>(['wifi'])
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showCustom, setShowCustom] = useState(false)
  const [customHost, setCustomHost] = useState('127.0.0.1')
  const [customPort, setCustomPort] = useState('35000')

  const { connected, device, setDevice, setConnected } = useAppStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Если уже подключены - редирект
  useEffect(() => {
    if (connected) {
      navigate('/dashboard')
    }
  }, [connected, navigate])

  // Запрос сканирования
  const scanQuery = useQuery({
    queryKey: ['devices', selectedTypes],
    queryFn: () => api.scanDevices(selectedTypes),
    enabled: false,
    retry: 1,
  })

  // Мутация подключения
  const connectMutation = useMutation({
    mutationFn: (deviceId: string) => api.connectDevice(deviceId),
    onSuccess: (data) => {
      setDevice(data)
      setConnected(true)
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['systemInfo'] })
      setTimeout(() => navigate('/dashboard'), 500)
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  // Кастомное подключение
  const customConnectMutation = useMutation({
    mutationFn: () => {
      return fetch('/api/v1/connect/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host: customHost, port: parseInt(customPort) }),
      }).then(r => r.json())
    },
    onSuccess: (data) => {
      if (data.success && data.data?.device) {
        setDevice(data.data.device)
        setConnected(true)
        setError(null)
        queryClient.invalidateQueries({ queryKey: ['systemInfo'] })
        setTimeout(() => navigate('/dashboard'), 500)
      } else {
        setError(data.message || 'Ошибка подключения')
      }
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  // Мутация отключения
  const disconnectMutation = useMutation({
    mutationFn: () => api.disconnectDevice(),
    onSuccess: () => {
      setDevice(null)
      setConnected(false)
      setSelectedDevice(null)
      queryClient.clear()
    },
  })

  const handleScan = useCallback(() => {
    setError(null)
    setSelectedDevice(null)
    scanQuery.refetch()
  }, [scanQuery])

  const handleConnect = useCallback(async () => {
    if (!selectedDevice) return
    setError(null)
    connectMutation.mutate(selectedDevice)
  }, [selectedDevice, connectMutation])

  const handleCustomConnect = useCallback(() => {
    setError(null)
    customConnectMutation.mutate()
  }, [customConnectMutation])

  const handleDisconnect = useCallback(async () => {
    disconnectMutation.mutate()
  }, [disconnectMutation])

  const toggleType = (type: ConnectionType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    )
  }

  const devices = scanQuery.data?.devices || []
  const hasScanned = scanQuery.isFetched
  const isConnecting = connectMutation.isPending || customConnectMutation.isPending

  // Если подключены - показываем статус
  if (connected && device) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-120px)]">
        <div className="w-full max-w-md mx-auto text-center space-y-6">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-3xl bg-emerald-500/20 border border-emerald-500/30">
            <CheckCircle2 className="w-12 h-12 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Подключено!</h2>
            <p className="text-surface-400 mt-2">{device.name}</p>
            <p className="text-sm text-surface-500">{device.address}</p>
          </div>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => navigate('/dashboard')} icon={<ArrowRight className="w-4 h-4" />}>
              Перейти к приборам
            </Button>
            <Button variant="danger" onClick={handleDisconnect} loading={disconnectMutation.isPending}>
              Отключить
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-120px)]">
      <div className="w-full max-w-xl mx-auto space-y-6">
        {/* Заголовок */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500/20 to-primary-600/10 border border-primary-500/30 shadow-lg shadow-primary-500/10">
            <Plug className="w-10 h-10 text-primary-400" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-surface-300 bg-clip-text text-transparent">
            Подключение к ELM327
          </h1>
          <p className="text-surface-400 text-lg">
            Найдите устройство или подключитесь напрямую
          </p>
        </div>

        {/* Ошибка */}
        {error && (
          <Card className="!p-4 border-red-500/30 bg-red-500/5">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-red-400 text-sm flex-1">{error}</p>
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
                <XCircle className="w-4 h-4" />
              </button>
            </div>
          </Card>
        )}

        {/* Выбор типа подключения */}
        <Card className="!p-5">
          <h3 className="text-sm font-semibold text-surface-400 uppercase tracking-wider mb-4 text-center">
            Тип подключения
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {connectionTypes.map(({ type, icon: Icon, label, description }) => (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-300',
                  'hover:scale-[1.02] active:scale-[0.98]',
                  selectedTypes.includes(type)
                    ? 'bg-primary-500/10 border-primary-500/50 shadow-lg shadow-primary-500/10'
                    : 'bg-surface-800/30 border-surface-700/30 hover:border-surface-600/50'
                )}
              >
                <Icon className={cn(
                  'w-6 h-6',
                  selectedTypes.includes(type) ? 'text-primary-400' : 'text-surface-500'
                )} />
                <span className="text-sm font-medium text-surface-300">{label}</span>
                <span className="text-[10px] text-surface-500 hidden sm:block">{description}</span>
              </button>
            ))}
          </div>
        </Card>

        {/* Сканирование */}
        <div className="space-y-3">
          <Button
            onClick={handleScan}
            loading={scanQuery.isLoading}
            icon={<Search className="w-5 h-5" />}
            size="lg"
            className="w-full"
          >
            {scanQuery.isLoading ? 'Поиск устройств...' : 'Сканировать устройства'}
          </Button>

          {devices.length > 0 && (
            <button
              onClick={handleScan}
              disabled={scanQuery.isLoading}
              className="flex items-center gap-2 mx-auto text-sm text-surface-400 hover:text-primary-400 transition-colors"
            >
              <RefreshCw className={cn('w-4 h-4', scanQuery.isLoading && 'animate-spin')} />
              Повторить сканирование
            </button>
          )}
        </div>

        {/* Загрузка */}
        {scanQuery.isLoading && (
          <Card className="!p-8 text-center">
            <Loader2 className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
            <p className="text-surface-300">Поиск устройств...</p>
            <p className="text-sm text-surface-500 mt-1">Это может занять до 30 секунд</p>
          </Card>
        )}

        {/* Нет устройств */}
        {!scanQuery.isLoading && devices.length === 0 && hasScanned && (
          <Card className="!p-8 text-center">
            <Server className="w-12 h-12 text-surface-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-surface-300 mb-2">Устройства не найдены</h3>
            <p className="text-surface-500 max-w-sm mx-auto">
              Проверьте подключение адаптера и попробуйте другой тип подключения
            </p>
          </Card>
        )}

        {/* Список устройств */}
        {devices.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-surface-400 uppercase tracking-wider">
              Найденные устройства ({devices.length})
            </h3>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {devices.map((dev) => (
                <DeviceCard
                  key={dev.id}
                  device={dev}
                  selected={selectedDevice === dev.id}
                  onClick={() => setSelectedDevice(dev.id)}
                />
              ))}
            </div>

            <Button
              onClick={handleConnect}
              disabled={!selectedDevice}
              loading={isConnecting}
              size="lg"
              className="w-full"
              variant="success"
            >
              {isConnecting ? 'Подключение...' : 'Подключиться'}
            </Button>
          </div>
        )}

        {/* Кастомное подключение */}
        <div className="border-t border-surface-700/30 pt-4">
          <button
            onClick={() => setShowCustom(!showCustom)}
            className="flex items-center gap-2 text-sm text-surface-400 hover:text-primary-400 transition-colors mx-auto"
          >
            <Terminal className="w-4 h-4" />
            {showCustom ? 'Скрыть' : 'Кастомное подключение'}
            <ChevronRight className={cn('w-4 h-4 transition-transform', showCustom && 'rotate-90')} />
          </button>

          {showCustom && (
            <Card className="!p-5 mt-3 space-y-4">
              <h3 className="text-sm font-medium text-surface-300">Прямое подключение</h3>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">Хост</label>
                  <input
                    type="text"
                    value={customHost}
                    onChange={(e) => setCustomHost(e.target.value)}
                    placeholder="127.0.0.1"
                    className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 text-surface-200 text-sm focus:border-primary-500/50 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-surface-500 mb-1 block">Порт</label>
                  <input
                    type="number"
                    value={customPort}
                    onChange={(e) => setCustomPort(e.target.value)}
                    placeholder="35000"
                    className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 text-surface-200 text-sm focus:border-primary-500/50 focus:outline-none"
                  />
                </div>
              </div>

              <Button
                onClick={handleCustomConnect}
                loading={customConnectMutation.isPending}
                icon={<Globe className="w-4 h-4" />}
                className="w-full"
              >
                Подключиться к {customHost}:{customPort}
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

// Карточка устройства
function DeviceCard({ device, selected, onClick }: { device: Device; selected: boolean; onClick: () => void }) {
  const typeIcons = { bluetooth: Bluetooth, wifi: Wifi, serial: Usb }
  const Icon = typeIcons[device.type] || Power

  return (
    <div
      onClick={onClick}
      className={cn(
        'relative p-4 rounded-xl border cursor-pointer transition-all duration-300 group',
        'bg-surface-800/30 backdrop-blur-sm',
        selected
          ? 'border-primary-400/60 shadow-lg shadow-primary-500/20 scale-[1.02]'
          : 'border-surface-700/30 hover:border-surface-600/50 hover:scale-[1.01]'
      )}
    >
      <div className="flex items-center gap-4">
        <div className={cn(
          'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
          'bg-surface-800/60 border border-surface-700/30',
          selected && 'bg-primary-500/20 border-primary-500/30'
        )}>
          <Icon className={cn('w-5 h-5', selected ? 'text-primary-400' : 'text-surface-400')} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-surface-200 truncate">{device.name}</h4>
          <p className="text-xs text-surface-500 truncate">{device.address}{device.port && `:${device.port}`}</p>
        </div>
        <ChevronRight className={cn(
          'w-4 h-4 transition-all',
          selected ? 'text-primary-400 translate-x-1' : 'text-surface-600'
        )} />
      </div>
      {selected && (
        <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary-400 animate-pulse" />
      )}
    </div>
  )
}
