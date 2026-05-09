import { useState, useEffect, useCallback, useRef } from 'react'
import { wsService } from '@/services/websocket'
import type { PIDValue, WSMessage } from '@/types/obd'

export function usePidData(pids: string[], enabled: boolean = true) {
  const [data, setData] = useState<Map<string, PIDValue>>(new Map())
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const enabledRef = useRef(enabled)

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  useEffect(() => {
    if (!enabled) return

    const handleMessage = (message: WSMessage) => {
      if (!enabledRef.current) return

      let pidArray: PIDValue[] = []

      if (message.type === 'pid_data') {
        if (Array.isArray(message.data?.data)) pidArray = message.data.data
        else if (Array.isArray(message.data?.pids)) pidArray = message.data.pids
        else if (Array.isArray(message.data)) pidArray = message.data
      }

      if (pidArray.length > 0) {
        setData(prev => {
          const newMap = new Map(prev)
          pidArray.forEach((pid: PIDValue) => {
            if (pid?.pid) newMap.set(pid.pid.toUpperCase(), pid)
          })
          return newMap
        })
        setLastUpdate(new Date())
        setError(null)
      }
    }

    const unsub = wsService.onMessage('pid_data', handleMessage)

    // Запускаем мониторинг
    wsService.send({ action: 'start_monitor', pids, interval: 0.3 })

    return () => {
      unsub()
      wsService.send({ action: 'stop_monitor' })
    }
  }, [pids.join(','), enabled])

  const getValue = useCallback((pid: string): PIDValue | undefined => {
    return data.get(pid.toUpperCase())
  }, [data])

  const getNumericValue = useCallback((pid: string): number | null => {
    const val = data.get(pid.toUpperCase())
    if (!val) return null
    if (typeof val.value === 'number') return val.value
    const num = parseFloat(val.value)
    return isNaN(num) ? null : num
  }, [data])

  return { data, lastUpdate, error, getValue, getNumericValue }
}