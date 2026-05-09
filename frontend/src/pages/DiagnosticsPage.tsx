import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import {
  AlertTriangle,
  CheckCircle,
  Trash2,
  Loader2,
  Search,
  Shield,
  Car,
  Cog,
  AlertCircle,
  XCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DTCInfo } from '@/types/obd'

const errorModes = [
  { mode: '03', label: 'Подтверждённые', icon: AlertTriangle, description: 'Активные ошибки, вызывающие MIL' },
  { mode: '07', label: 'Ожидающие', icon: AlertCircle, description: 'Обнаруженные, но ещё не подтверждённые' },
  { mode: '0A', label: 'Постоянные', icon: Shield, description: 'Подтверждённые и сохранённые в памяти' },
]

const specializedSystems = [
  { header: '7B0', name: 'SRS (Подушки)', icon: Shield },
  { header: '7A0', name: 'ABS (Тормоза)', icon: Car },
  { header: '7E0', name: 'Трансмиссия', icon: Cog },
]

export function DiagnosticsPage() {
  const [activeMode, setActiveMode] = useState('03')
  const queryClient = useQueryClient()

  // Запрос ошибок
  const errorsQuery = useQuery({
    queryKey: ['errors', activeMode],
    queryFn: () => api.readErrors(activeMode),
    refetchInterval: 10000,
  })

  // Запрос статуса MIL
  const milQuery = useQuery({
    queryKey: ['milStatus'],
    queryFn: () => api.executeCommand('01 01'),
    refetchInterval: 5000,
  })

  // Сброс ошибок
  const clearMutation = useMutation({
    mutationFn: () => api.clearErrors(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['errors'] })
      queryClient.invalidateQueries({ queryKey: ['milStatus'] })
    },
  })

  // Запрос специализированной системы
  const [specializedResult, setSpecializedResult] = useState<string | null>(null)
  const specializedMutation = useMutation({
    mutationFn: async (header: string) => {
      await api.executeCommand(`AT SH ${header}`)
      const result = await api.executeCommand('19 02 01')
      await api.executeCommand('AT SH 7DF')
      return result
    },
    onSuccess: (data) => {
      setSpecializedResult(data.response || 'Нет данных')
    },
  })

  const errors = errorsQuery.data || []
  const hasErrors = errors.length > 0

  // Парсим статус MIL
  const milOn = milQuery.data?.response?.includes('81') || milQuery.data?.response?.includes('80')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Диагностика ошибок</h2>
          <p className="text-surface-400 mt-1">Чтение и сброс кодов неисправностей</p>
        </div>
        {hasErrors && (
          <Button
            variant="danger"
            onClick={() => {
              if (confirm('Вы уверены? Это сбросит все ошибки и выключит Check Engine.')) {
                clearMutation.mutate()
              }
            }}
            loading={clearMutation.isPending}
            icon={<Trash2 className="w-4 h-4" />}
          >
            Сбросить ошибки
          </Button>
        )}
      </div>

      {/* Статус MIL */}
      <Card className={cn(
        '!p-5',
        milOn ? 'border-red-500/30 bg-red-500/5' : 'border-emerald-500/30 bg-emerald-500/5'
      )}>
        <div className="flex items-center gap-4">
          <div className={cn(
            'w-12 h-12 rounded-xl flex items-center justify-center',
            milOn ? 'bg-red-500/20' : 'bg-emerald-500/20'
          )}>
            {milOn ? (
              <AlertTriangle className="w-6 h-6 text-red-400 animate-pulse" />
            ) : (
              <CheckCircle className="w-6 h-6 text-emerald-400" />
            )}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">
              {milOn ? 'Check Engine ВКЛЮЧЕН' : 'Check Engine выключен'}
            </h3>
            <p className="text-sm text-surface-400">
              {milOn
                ? `Обнаружено ошибок: ${errors.length}`
                : 'Ошибки не обнаружены'}
            </p>
          </div>
        </div>
      </Card>

      {/* Выбор режима */}
      <div className="grid grid-cols-3 gap-3">
        {errorModes.map(({ mode, label, icon: Icon, description }) => (
          <button
            key={mode}
            onClick={() => setActiveMode(mode)}
            className={cn(
              'p-4 rounded-xl border-2 transition-all duration-300 text-left',
              activeMode === mode
                ? 'bg-primary-500/10 border-primary-500/50'
                : 'bg-surface-800/30 border-surface-700/30 hover:border-surface-600/50'
            )}
          >
            <Icon className={cn(
              'w-5 h-5 mb-2',
              activeMode === mode ? 'text-primary-400' : 'text-surface-500'
            )} />
            <h4 className="font-medium text-surface-200 text-sm">{label}</h4>
            <p className="text-[10px] text-surface-500 mt-1">{description}</p>
          </button>
        ))}
      </div>

      {/* Таблица ошибок */}
      <Card className="!p-0 overflow-hidden">
        <div className="p-4 border-b border-surface-700/30">
          <h3 className="font-medium text-surface-200">
            {errorModes.find(m => m.mode === activeMode)?.label} ошибки
          </h3>
        </div>

        {errorsQuery.isLoading ? (
          <div className="p-8 text-center">
            <Loader2 className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-3" />
            <p className="text-surface-400">Чтение ошибок...</p>
          </div>
        ) : errors.length === 0 ? (
          <div className="p-8 text-center">
            <CheckCircle className="w-12 h-12 text-emerald-500/50 mx-auto mb-3" />
            <p className="text-surface-300 font-medium">Ошибок нет</p>
            <p className="text-sm text-surface-500 mt-1">Система работает нормально</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-700/30">
                  <th className="text-left p-4 text-xs font-medium text-surface-500 uppercase">Код</th>
                  <th className="text-left p-4 text-xs font-medium text-surface-500 uppercase">Категория</th>
                  <th className="text-left p-4 text-xs font-medium text-surface-500 uppercase">Описание</th>
                  <th className="text-left p-4 text-xs font-medium text-surface-500 uppercase">Статус</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((error, index) => (
                  <tr key={index} className="border-b border-surface-700/20 last:border-0 hover:bg-surface-800/30 transition-colors">
                    <td className="p-4">
                      <span className="font-mono font-bold text-red-400">{error.code}</span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-surface-300">{error.category}</span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-surface-400">
                        {error.description || 'Описание недоступно'}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={cn(
                        'inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full',
                        activeMode === '03' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'
                      )}>
                        {activeMode === '03' ? 'Активна' : activeMode === '07' ? 'Ожидает' : 'Постоянная'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Специализированные системы */}
      <Card className="!p-5">
        <h3 className="font-medium text-surface-200 mb-4">Специализированные системы</h3>
        <div className="grid grid-cols-3 gap-3">
          {specializedSystems.map(({ header, name, icon: Icon }) => (
            <button
              key={header}
              onClick={() => specializedMutation.mutate(header)}
              disabled={specializedMutation.isPending}
              className="flex flex-col items-center gap-3 p-4 rounded-xl bg-surface-800/40 border border-surface-700/30 hover:border-surface-600/50 transition-all disabled:opacity-50"
            >
              <Icon className="w-6 h-6 text-surface-400" />
              <span className="text-sm font-medium text-surface-300">{name}</span>
              <span className="text-[10px] text-surface-500">Запросить ошибки</span>
            </button>
          ))}
        </div>

        {specializedResult && (
          <div className="mt-4 p-3 rounded-lg bg-surface-800/60 border border-surface-700/30">
            <p className="text-sm font-mono text-surface-300">{specializedResult}</p>
          </div>
        )}
      </Card>
    </div>
  )
}