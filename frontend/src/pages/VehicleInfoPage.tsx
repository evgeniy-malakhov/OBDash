import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import Card from '@/components/ui/Card'
import {
  Car,
  Cpu,
  Hash,
  Battery,
  Wifi,
  FileText,
  Calendar,
  Gauge,
  Loader2,
  Clipboard,
  Check,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

export function VehicleInfoPage() {
  const [copied, setCopied] = useState<string | null>(null)

  // Запрос информации об авто
  const vehicleQuery = useQuery({
    queryKey: ['vehicleInfo'],
    queryFn: () => api.getVehicleInfo(),
    refetchInterval: 30000,
  })

  // Запрос поддерживаемых PID
  const pidsQuery = useQuery({
    queryKey: ['supportedPids'],
    queryFn: async () => {
      const result = await api.executeCommand('01 00')
      return result
    },
    refetchInterval: 60000,
  })

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(key)
      setTimeout(() => setCopied(null), 2000)
    } catch {}
  }

  if (vehicleQuery.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    )
  }

  const info = vehicleQuery.data || {}

  const infoCards = [
    {
      title: 'VIN номер',
      value: info.vin || info['09 02'] || 'N/A',
      icon: Hash,
      key: 'vin',
      description: 'Идентификационный номер автомобиля',
      copyable: true,
    },
    {
      title: 'ECU',
      value: info.ecu_name || info['09 0A'] || 'N/A',
      icon: Cpu,
      key: 'ecu',
      description: 'Электронный блок управления',
    },
    {
      title: 'Версия ELM327',
      value: info.elm_version || info.ATI || 'N/A',
      icon: Wifi,
      key: 'elm',
      description: 'Версия прошивки адаптера',
    },
    {
      title: 'Напряжение',
      value: info.voltage || info.ATRV || 'N/A',
      icon: Battery,
      key: 'voltage',
      description: 'Напряжение бортовой сети',
    },
    {
      title: 'Протокол',
      value: info.protocol || info.ATDP || 'N/A',
      icon: FileText,
      key: 'protocol',
      description: 'Используемый OBD2 протокол',
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Информация об автомобиле</h2>
        <p className="text-surface-400 mt-1">Идентификационные данные и параметры системы</p>
      </div>

      {/* Основная информация */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {infoCards.map(({ title, value, icon: Icon, key, description, copyable }) => (
          <Card key={key} className="!p-5 relative group">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center flex-shrink-0">
                <Icon className="w-5 h-5 text-primary-400" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-surface-400">{title}</h3>
                <p className="text-lg font-mono font-bold text-white mt-1 truncate">
                  {value}
                </p>
                <p className="text-[10px] text-surface-500 mt-1">{description}</p>
              </div>
            </div>

            {copyable && value !== 'N/A' && (
              <button
                onClick={() => copyToClipboard(String(value), key)}
                className="absolute top-3 right-3 w-8 h-8 rounded-lg flex items-center justify-center bg-surface-800/60 border border-surface-700/30 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-surface-700/50"
              >
                {copied === key ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Clipboard className="w-4 h-4 text-surface-400" />
                )}
              </button>
            )}
          </Card>
        ))}
      </div>

      {/* Детальная информация */}
      <Card className="!p-5">
        <h3 className="font-medium text-surface-200 mb-4">Все данные</h3>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(info).map(([key, value]) => (
            <div
              key={key}
              className="flex items-center justify-between p-3 rounded-lg bg-surface-800/30 border border-surface-700/20"
            >
              <span className="text-sm text-surface-400 font-mono">{key}</span>
              <span className="text-sm text-surface-200 font-medium">
                {String(value)}
              </span>
            </div>
          ))}
          {Object.keys(info).length === 0 && (
            <p className="text-surface-500 text-sm col-span-2 text-center py-4">
              Нет данных
            </p>
          )}
        </div>
      </Card>

      {/* Поддерживаемые PID */}
      {pidsQuery.data && (
        <Card className="!p-5">
          <h3 className="font-medium text-surface-200 mb-4">Поддерживаемые PID</h3>
          <p className="text-sm text-surface-400 mb-3">
            Ответ на запрос 01 00 (битовая маска поддерживаемых PID)
          </p>
          <div className="p-3 rounded-lg bg-surface-800/60 border border-surface-700/30">
            <code className="text-sm font-mono text-primary-300 break-all">
              {pidsQuery.data.response}
            </code>
          </div>
        </Card>
      )}
    </div>
  )
}