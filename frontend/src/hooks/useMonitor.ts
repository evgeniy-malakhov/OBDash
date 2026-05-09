import { useState, useEffect, useRef, useCallback } from 'react'
import { wsService } from '@/services/websocket'
import { api } from '@/services/api'
import type { PIDValue, WSMessage } from '@/types/obd'

interface DataPoint {
  time: string
  timestamp: number
  [key: string]: any
}

interface UseMonitorOptions {
  pids: string[]
  interval?: number
  maxPoints?: number
  autoStart?: boolean
}

export function useMonitor({ pids, interval = 0.3, maxPoints = 120, autoStart = true }: UseMonitorOptions) {
  const [dataPoints, setDataPoints] = useState<DataPoint[]>([])
  const [currentValues, setCurrentValues] = useState<Map<string, PIDValue>>(new Map())
  const [monitoring, setMonitoring] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const dataPointsRef = useRef<DataPoint[]>([])
  const monitoringRef = useRef(false)
  const counterRef = useRef(0)

  useEffect(() => {
    dataPointsRef.current = dataPoints
  }, [dataPoints])

  useEffect(() => {
    monitoringRef.current = monitoring
  }, [monitoring])

  const startMonitoring = useCallback(async () => {
    if (pids.length === 0) return

    setDataPoints([])
    setCurrentValues(new Map())
    counterRef.current = 0

    try {
      await api.startMonitoring({ pids, interval })
    } catch {}

    wsService.send({ action: 'start_monitor', pids, interval })
    setMonitoring(true)
  }, [pids.join(','), interval])

  const stopMonitoring = useCallback(async () => {
    try { await api.stopMonitoring() } catch {}
    wsService.send({ action: 'stop_monitor' })
    setMonitoring(false)
  }, [])

  useEffect(() => {
    const handleMessage = (message: WSMessage) => {
      if (!monitoringRef.current) return

      let pidArray: PIDValue[] = []
      if (message.type === 'pid_data') {
        if (Array.isArray(message.data?.data)) pidArray = message.data.data
        else if (Array.isArray(message.data?.pids)) pidArray = message.data.pids
        else if (Array.isArray(message.data)) pidArray = message.data
      }

      if (pidArray.length > 0) {
        setCurrentValues(prev => {
          const newMap = new Map(prev)
          pidArray.forEach((pid: PIDValue) => {
            if (pid?.pid) newMap.set(pid.pid.toUpperCase(), pid)
          })
          return newMap
        })

        const now = new Date()
        counterRef.current++
        const point: DataPoint = {
          time: now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          timestamp: now.getTime(),
          index: counterRef.current,
        }

        pidArray.forEach((pid: PIDValue) => {
          if (pid?.pid) {
            const key = pid.pid.toUpperCase()
            if (typeof pid.value === 'number') point[key] = pid.value
            else if (typeof pid.value === 'string') {
              const num = parseFloat(pid.value)
              if (!isNaN(num)) point[key] = num
            }
          }
        })

        setDataPoints(prev => {
          const updated = [...prev, point]
          return updated.length > maxPoints ? updated.slice(-maxPoints) : updated
        })
      }
    }

    const unsub = wsService.onMessage('pid_data', handleMessage)
    return () => unsub()
  }, [maxPoints])

  useEffect(() => {
    return () => {
      if (monitoringRef.current) {
        wsService.send({ action: 'stop_monitor' })
      }
    }
  }, [])

  return {
    dataPoints,
    currentValues,
    monitoring,
    error,
    startMonitoring,
    stopMonitoring,
    getValue: (pid: string) => currentValues.get(pid.toUpperCase()),
  }
}