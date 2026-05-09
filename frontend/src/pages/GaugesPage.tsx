import { usePidData } from '@/hooks/usePidData'
import { useAppStore } from '@/stores/appStore'
import { Speedometer } from '@/components/gauges/Speedometer'
import { Tachometer } from '@/components/gauges/Tachometer'
import { LinearGauge } from '@/components/gauges/LinearGauge'
import { BoostGauge } from '@/components/gauges/BoostGauge'
import Card from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import {
  Gauge,
  Thermometer,
  Zap,
  Droplets,
  Wind,
  Activity,
  Timer,
  Flame,
  Battery,
  Waves,
  ArrowUp,
  Cpu,
  GaugeCircle,
} from 'lucide-react'

const MONITOR_PIDS = ['0C', '0D', '05', '0F', '04', '2F', '42', '0B', '11', '0E', '1F', '5C', '46', '0A']

export function GaugesPage() {
  const { connected } = useAppStore()
  const { data, getNumericValue, lastUpdate } = usePidData(MONITOR_PIDS, connected)

  const rpm = getNumericValue('0C') || 0
  const speed = getNumericValue('0D') || 0
  const coolant = getNumericValue('05') || 0
  const intake = getNumericValue('0F') || 0
  const load = getNumericValue('04') || 0
  const fuel = getNumericValue('2F') || 0
  const voltage = getNumericValue('42') || 0
  const map = getNumericValue('0B') || 0
  const throttle = getNumericValue('11') || 0
  const timing = getNumericValue('0E') || 0
  const runtime = getNumericValue('1F') || 0
  const oilTemp = getNumericValue('5C') || 0
  const ambientTemp = getNumericValue('46') || 0
  const fuelPressure = getNumericValue('0A') || 0

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Приборная панель</h2>
          <p className="text-surface-400 mt-1">Все показатели в реальном времени</p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-xs text-surface-500">
              Обновлено: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <Badge variant={connected ? 'success' : 'danger'} pulse={connected}>
            {connected ? 'Online' : 'Offline'}
          </Badge>
        </div>
      </div>

      {/* Основные круглые приборы - увеличенные */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Тахометр */}
        <Card className="!p-6 flex flex-col items-center min-h-[380px]">
          <div className="flex items-center gap-2 mb-4">
            <GaugeCircle className="w-5 h-5 text-orange-400" />
            <h3 className="text-lg font-semibold text-white">Тахометр</h3>
          </div>
          <div className="flex-1 flex items-center justify-center">
            <Tachometer value={rpm} max={8000} redline={6500} shiftLight={5500} />
          </div>
          <div className="mt-4 space-y-1 text-center">
            <div className="text-3xl font-bold font-mono text-white">
              {Math.round(rpm).toLocaleString()}
              <span className="text-lg text-surface-400 ml-1">RPM</span>
            </div>
            {rpm > 5500 && (
              <Badge variant="danger" pulse className="animate-pulse">SHIFT NOW!</Badge>
            )}
            {rpm > 4000 && rpm <= 5500 && (
              <Badge variant="warning">Высокие обороты</Badge>
            )}
          </div>
        </Card>

        {/* Спидометр */}
        <Card className="!p-6 flex flex-col items-center min-h-[380px]">
          <div className="flex items-center gap-2 mb-4">
            <Gauge className="w-5 h-5 text-emerald-400" />
            <h3 className="text-lg font-semibold text-white">Спидометр</h3>
          </div>
          <div className="flex-1 flex items-center justify-center">
            <Speedometer
              value={speed}
              max={260}
              unit="km/h"
              label="Скорость"
              color="#34d399"
              size="lg"
              warningZone={130}
              dangerZone={180}
            />
          </div>
          <div className="mt-2 text-center">
            <Badge variant={speed > 130 ? 'warning' : 'default'}>
              {speed === 0 ? 'Стоянка' : speed > 130 ? 'Превышение' : 'Движение'}
            </Badge>
          </div>
        </Card>
      </div>

      {/* Секция температур */}
      <div>
        <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Thermometer className="w-4 h-4" />
          Температуры
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="!p-5">
            <LinearGauge
              value={coolant}
              min={20}
              max={120}
              unit="°C"
              label="Охлаждающая жидкость"
              icon={<Thermometer className="w-4 h-4" style={{ color: '#f97316' }} />}
              color="#f97316"
              warningMin={60}
              warningMax={105}
            />
          </Card>

          <Card className="!p-5">
            <LinearGauge
              value={oilTemp}
              min={20}
              max={140}
              unit="°C"
              label="Масло двигателя"
              icon={<Droplets className="w-4 h-4" style={{ color: '#eab308' }} />}
              color="#eab308"
              warningMax={120}
            />
          </Card>

          <Card className="!p-5">
            <LinearGauge
              value={intake}
              min={-20}
              max={80}
              unit="°C"
              label="Впускной воздух"
              icon={<Wind className="w-4 h-4" style={{ color: '#38bdf8' }} />}
              color="#38bdf8"
            />
          </Card>

          <Card className="!p-5">
            <LinearGauge
              value={ambientTemp}
              min={-40}
              max={60}
              unit="°C"
              label="Окружающая среда"
              icon={<Wind className="w-4 h-4" style={{ color: '#94a3b8' }} />}
              color="#94a3b8"
            />
          </Card>
        </div>
      </div>

      {/* Секция двигателя */}
      <div>
        <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Cpu className="w-4 h-4" />
          Двигатель
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="!p-5">
            <LinearGauge
              value={load}
              min={0}
              max={100}
              unit="%"
              label="Нагрузка"
              icon={<Activity className="w-4 h-4" style={{ color: '#a78bfa' }} />}
              color="#a78bfa"
              warningMax={85}
            />
          </Card>

          <Card className="!p-5">
            <LinearGauge
              value={throttle}
              min={0}
              max={100}
              unit="%"
              label="Дроссельная заслонка"
              icon={<ArrowUp className="w-4 h-4" style={{ color: '#e879f9' }} />}
              color="#e879f9"
            />
          </Card>

          <Card className="!p-5">
            <LinearGauge
              value={timing}
              min={-20}
              max={50}
              unit="°"
              label="Угол зажигания"
              icon={<Flame className="w-4 h-4" style={{ color: '#fb923c' }} />}
              color="#fb923c"
            />
          </Card>

          <Card className="!p-5">
            <LinearGauge
              value={runtime}
              min={0}
              max={3600}
              unit="сек"
              label="Время работы"
              icon={<Timer className="w-4 h-4" style={{ color: '#64748b' }} />}
              color="#64748b"
            />
          </Card>
        </div>
      </div>

      {/* Секция топлива и давления */}
      <div>
        <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Waves className="w-4 h-4" />
          Топливо и давление
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Уровень топлива - вертикальный */}
          <Card className="!p-5 flex justify-center">
            <LinearGauge
              value={fuel}
              min={0}
              max={100}
              unit="%"
              label="Уровень топлива"
              icon={<Droplets className="w-4 h-4" style={{ color: '#fbbf24' }} />}
              color="#fbbf24"
              warningMin={15}
              vertical
              showValue={true}
            />
          </Card>

          {/* Давление впуска (Boost) */}
          <Card className="!p-5 flex flex-col items-center">
            <h4 className="text-xs text-surface-500 uppercase tracking-wider mb-2">Давление впуска</h4>
            <BoostGauge value={map} maxBoost={150} />
          </Card>

          {/* Давление топлива */}
          <Card className="!p-5">
            <LinearGauge
              value={(fuelPressure || 0) * 3}
              min={0}
              max={500}
              unit="kPa"
              label="Давление топлива"
              icon={<Waves className="w-4 h-4" style={{ color: '#06b6d4' }} />}
              color="#06b6d4"
            />
          </Card>
        </div>
      </div>

      {/* Электрика */}
      <div>
        <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4" />
          Электрика
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="!p-5">
            <LinearGauge
              value={voltage}
              min={8}
              max={16}
              unit="V"
              label="Напряжение бортовой сети"
              icon={<Battery className="w-4 h-4" style={{ color: '#818cf8' }} />}
              color="#818cf8"
              warningMin={11.5}
              warningMax={15}
            />
            <div className="mt-3 flex justify-between text-[10px] text-surface-600">
              <span>Разряд</span>
              <span className="text-amber-400">11.5V</span>
              <span>Норма</span>
              <span className="text-red-400">15V</span>
              <span>Перенапряжение</span>
            </div>
          </Card>

          <Card className="!p-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 rounded-xl bg-surface-800/40 border border-surface-700/20">
                <p className="text-[10px] text-surface-500 uppercase">Напряжение</p>
                <p className="text-2xl font-bold font-mono text-white mt-1">{voltage.toFixed(1)}</p>
                <p className="text-xs text-surface-500">V</p>
              </div>
              <div className="text-center p-3 rounded-xl bg-surface-800/40 border border-surface-700/20">
                <p className="text-[10px] text-surface-500 uppercase">Статус</p>
                <p className={`text-sm font-bold mt-1 ${voltage > 13 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {voltage > 13 ? 'Зарядка' : 'Батарея'}
                </p>
                <p className="text-xs text-surface-500">
                  {voltage > 13 ? 'Генератор' : 'Разряд'}
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}