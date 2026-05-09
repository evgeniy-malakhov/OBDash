import { NavLink, useLocation } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Wifi,
  Activity,
  AlertTriangle,
  Car,
  Settings,
  Power,
  Gauge,
  Thermometer,
  Zap,
  ChevronLeft,
  ChevronRight,
  GaugeCircle,
  BarChart3,
  Cpu,
} from 'lucide-react'
import { useState } from 'react'

const navigation = [
  {
    section: 'Панель',
    items: [
      {
        to: '/dashboard',
        icon: LayoutDashboard,
        label: 'Главная',
        description: 'Сводка основных показателей',
        badge: null,
      },
      {
        to: '/gauges',
        icon: GaugeCircle,
        label: 'Приборы',
        description: 'Все датчики и индикаторы',
        badge: null,
      },
      {
        to: '/monitoring',
        icon: BarChart3,
        label: 'Графики',
        description: 'Мониторинг параметров',
        badge: 'Live',
      },
    ]
  },
  {
    section: 'Диагностика',
    items: [
      {
        to: '/diagnostics',
        icon: AlertTriangle,
        label: 'Ошибки',
        description: 'Коды DTC и их расшифровка',
        badge: null,
      },
      {
        to: '/vehicle',
        icon: Car,
        label: 'Автомобиль',
        description: 'VIN, ECU, протоколы',
        badge: null,
      },
      {
        to: '/performance',
        icon: Cpu,
        label: 'Производительность',
        description: 'Замеры и статистика',
        badge: 'New',
      },
    ]
  },
  {
    section: 'Система',
    items: [
      {
        to: '/',
        icon: Wifi,
        label: 'Подключение',
        description: 'Поиск устройств',
        badge: null,
      },
      {
        to: '/settings',
        icon: Settings,
        label: 'Настройки',
        description: 'Конфигурация и консоль',
        badge: null,
      },
    ]
  },
]

const quickPids = [
  { pid: '0C', icon: Gauge, label: 'RPM', color: '#f97316' },
  { pid: '0D', icon: Activity, label: 'Speed', color: '#34d399' },
  { pid: '05', icon: Thermometer, label: 'Temp', color: '#ef4444' },
  { pid: '42', icon: Zap, label: 'Volt', color: '#818cf8' },
]

export function Sidebar() {
  const { connected, device, systemInfo, wsConnected } = useAppStore()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={cn(
      'relative bg-surface-950/90 border-r border-surface-800/50 backdrop-blur-2xl flex flex-col flex-shrink-0 transition-all duration-500 ease-in-out',
      collapsed ? 'w-[72px]' : 'w-[280px]'
    )}>
      {/* Кнопка сворачивания */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-surface-800 border border-surface-700/50 flex items-center justify-center text-surface-400 hover:text-white hover:bg-surface-700 transition-all z-10 shadow-lg"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>

      {/* Логотип */}
      <div className={cn(
        'border-b border-surface-800/50 transition-all duration-500',
        collapsed ? 'px-4 py-5' : 'px-6 py-5'
      )}>
        <div className="flex items-center gap-3">
          {/* Иконка логотипа */}
          <div className="relative flex-shrink-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 flex items-center justify-center shadow-xl shadow-primary-500/20">
              <Gauge className="w-5 h-5 text-white" />
            </div>
            {/* Пульсирующее кольцо при подключении */}
            {connected && (
              <span className="absolute -top-0.5 -right-0.5 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500 border-2 border-surface-950" />
              </span>
            )}
          </div>

          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-lg font-bold tracking-tight">
                <span className="bg-gradient-to-r from-white via-primary-200 to-primary-400 bg-clip-text text-transparent">
                  OBDash
                </span>
              </h1>
              <p className="text-[10px] text-surface-500 font-medium tracking-wide uppercase">
                ELM327 Scanner Pro
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Статус устройства */}
      {device && !collapsed && (
        <div className="mx-4 mt-4">
          <div className={cn(
            'flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-300',
            connected
              ? 'bg-emerald-500/5 border-emerald-500/20 shadow-lg shadow-emerald-500/5'
              : 'bg-red-500/5 border-red-500/20'
          )}>
            <div className="relative flex-shrink-0">
              <div className={cn(
                'w-2.5 h-2.5 rounded-full',
                connected ? 'bg-emerald-400' : 'bg-red-400'
              )} />
              {connected && (
                <div className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping opacity-50" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className={cn(
                'text-xs font-medium truncate',
                connected ? 'text-emerald-300' : 'text-red-300'
              )}>
                {device.name}
              </p>
              {device.address && (
                <p className="text-[9px] text-surface-500 truncate mt-0.5">
                  {device.address}{device.port ? `:${device.port}` : ''}
                </p>
              )}
            </div>
            {connected && (
              <div className="flex-shrink-0 flex items-center gap-1.5">
                {wsConnected && (
                  <div className="w-1 h-1 rounded-full bg-emerald-400" title="WebSocket Online" />
                )}
                {device.voltage && (
                  <span className="text-[9px] font-mono text-surface-400">
                    {device.voltage}V
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Свёрнутый статус */}
      {device && collapsed && (
        <div className="flex justify-center mt-4">
          <div className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center border transition-all',
            connected
              ? 'bg-emerald-500/10 border-emerald-500/30'
              : 'bg-red-500/10 border-red-500/30'
          )}>
            <div className={cn(
              'w-2.5 h-2.5 rounded-full',
              connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
            )} />
          </div>
        </div>
      )}

      {/* Навигация */}
      <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-8 scrollbar-thin">
        {navigation.map((section, sectionIdx) => (
          <div key={section.section}>
            {!collapsed && (
              <h3 className="px-3 mb-2 text-[11px] font-bold text-surface-500 uppercase tracking-[0.15em]">
                {section.section}
              </h3>
            )}
            {collapsed && sectionIdx > 0 && (
              <div className="my-4 border-t border-surface-800/50 mx-2" />
            )}
            <div className="space-y-1.5">
              {section.items.map((item) => {
                const isActive = location.pathname === item.to
                const isMainConnection = item.to === '/' && !connected

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive: active }) => cn(
                      'flex items-center gap-3 rounded-2xl transition-all duration-300 group relative overflow-hidden',
                      collapsed ? 'justify-center p-3' : 'px-4 py-3',
                      active || isActive
                        ? 'bg-primary-500/15 text-primary-200 border border-primary-500/30 shadow-lg shadow-primary-500/5'
                        : isMainConnection
                          ? 'text-surface-200 border border-emerald-500/30 bg-emerald-500/10 shadow-lg shadow-emerald-500/5 hover:bg-emerald-500/20'
                          : 'text-surface-400 border border-transparent hover:text-surface-200 hover:bg-surface-800/40 hover:border-surface-700/30',
                    )}
                    title={collapsed ? `${item.label} - ${item.description}` : undefined}
                  >
                    {/* Активный индикатор слева */}
                    {(isActive || isMainConnection) && !collapsed && (
                      <div className={cn(
                        'absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-r-full',
                        isMainConnection ? 'bg-emerald-400' : 'bg-primary-400'
                      )} />
                    )}

                    {/* Иконка */}
                    <div className={cn(
                      'relative flex-shrink-0 transition-all duration-300',
                      collapsed ? 'w-6 h-6' : 'w-5 h-5'
                    )}>
                      <item.icon className={cn(
                        'w-full h-full transition-all duration-300',
                        isActive ? 'text-primary-400' :
                        isMainConnection ? 'text-emerald-400' :
                        'text-surface-500 group-hover:text-surface-300'
                      )} />

                      {/* Свечение для активной иконки */}
                      {(isActive || isMainConnection) && (
                        <div className={cn(
                          'absolute inset-0 blur-xl opacity-30',
                          isMainConnection ? 'bg-emerald-400' : 'bg-primary-400'
                        )} />
                      )}
                    </div>

                    {!collapsed && (
                      <>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className={cn(
                              'text-sm font-semibold transition-colors duration-300',
                              isActive ? 'text-primary-100' :
                              isMainConnection ? 'text-emerald-100' :
                              'text-surface-300 group-hover:text-surface-100'
                            )}>
                              {item.label}
                            </span>
                            {item.badge && (
                              <span className={cn(
                                'text-[10px] font-bold px-2 py-0.5 rounded-full ml-2 flex-shrink-0',
                                item.badge === 'Live'
                                  ? 'bg-red-500/20 text-red-400 animate-pulse border border-red-500/30'
                                  : 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                              )}>
                                {item.badge}
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] text-surface-500 mt-0.5 leading-tight truncate">
                            {item.description}
                          </p>
                        </div>

                        {/* Стрелка для активного */}
                        {isActive && (
                          <div className="w-1.5 h-1.5 rounded-full bg-primary-400 flex-shrink-0 shadow-lg shadow-primary-400/50" />
                        )}
                      </>
                    )}
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Быстрые PID */}
      {connected && (
        <div className={cn(
          'border-t border-surface-800/50 transition-all duration-500',
          collapsed ? 'px-3 py-4' : 'px-5 py-4'
        )}>
          {!collapsed && (
            <h3 className="px-1 mb-3 text-[11px] font-bold text-surface-500 uppercase tracking-[0.15em]">
              Быстрый доступ
            </h3>
          )}
          <div className={cn(
            'grid gap-1.5',
            collapsed ? 'grid-cols-2' : 'grid-cols-4'
          )}>
            {quickPids.map(({ pid, icon: Icon, label, color }) => (
              <button
                key={pid}
                className={cn(
                  'flex items-center gap-1.5 rounded-xl transition-all duration-300',
                  'hover:scale-105 active:scale-95',
                  collapsed
                    ? 'flex-col justify-center p-2 border border-surface-800/50 hover:border-surface-700/50 bg-surface-900/50'
                    : 'flex-col justify-center py-2.5 border border-surface-800/50 hover:border-surface-700/50 bg-surface-900/30 hover:bg-surface-800/40'
                )}
                title={`PID ${pid}: ${label}`}
                onClick={() => {
                  // TODO: Быстрый переход к PID на графиках
                }}
              >
                <Icon className="w-4 h-4 flex-shrink-0" style={{ color }} />
                {!collapsed && (
                  <span className="text-[9px] font-semibold text-surface-400">
                    {label}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Нижняя панель */}
      {connected && !collapsed && (
        <div className="p-4 border-t border-surface-800/50 space-y-2">
          {/* Статистика */}
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div className="text-center p-2 rounded-lg bg-surface-900/50 border border-surface-800/50">
              <p className="text-[9px] text-surface-500 uppercase">Команд</p>
              <p className="text-xs font-bold font-mono text-surface-300">
                {systemInfo?.commands_executed || 0}
              </p>
            </div>
            <div className="text-center p-2 rounded-lg bg-surface-900/50 border border-surface-800/50">
              <p className="text-[9px] text-surface-500 uppercase">Точек</p>
              <p className="text-xs font-bold font-mono text-surface-300">
                {systemInfo?.data_points_collected || 0}
              </p>
            </div>
          </div>

          {/* Кнопка отключения */}
          <button
            onClick={() => {
              // TODO: Имплементировать диалог подтверждения
            }}
            className="flex items-center justify-center gap-2.5 w-full px-4 py-2.5 rounded-xl bg-red-500/5 text-red-400 border border-red-500/20 hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-300 transition-all duration-300 text-sm font-semibold group"
          >
            <Power className="w-4 h-4 transition-transform group-hover:scale-110" />
            <span>Отключить устройство</span>
          </button>
        </div>
      )}

      {!connected && !collapsed && (
        <div className="p-4 border-t border-surface-800/50">
          <div className="text-center p-4 rounded-xl bg-surface-900/50 border border-dashed border-surface-700/50">
            <Wifi className="w-6 h-6 text-surface-600 mx-auto mb-2" />
            <p className="text-xs text-surface-500">Нет подключения</p>
            <NavLink
              to="/"
              className="text-[10px] text-primary-400 hover:text-primary-300 mt-1 inline-block font-medium"
            >
              Подключиться →
            </NavLink>
          </div>
        </div>
      )}
    </aside>
  )
}