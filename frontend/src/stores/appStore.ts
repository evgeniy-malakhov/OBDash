import { create } from 'zustand'
import type { Device, SystemInfo, MonitorStatus } from '@/types/obd'

interface AppState {
  connected: boolean
  device: Device | null
  systemInfo: SystemInfo | null
  monitorActive: boolean
  monitorStatus: MonitorStatus | null
  wsConnected: boolean
  sidebarCollapsed: boolean
  activeTab: string

  setConnected: (connected: boolean) => void
  setDevice: (device: Device | null) => void
  setSystemInfo: (info: SystemInfo | null) => void
  setMonitorActive: (active: boolean) => void
  setMonitorStatus: (status: MonitorStatus | null) => void
  setWsConnected: (connected: boolean) => void
  toggleSidebar: () => void
  setActiveTab: (tab: string) => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  connected: false,
  device: null,
  systemInfo: null,
  monitorActive: false,
  monitorStatus: null,
  wsConnected: false,
  sidebarCollapsed: false,
  activeTab: 'dashboard',

  setConnected: (connected) => {
    console.log('🔄 Store: connected =', connected)
    set({ connected })
  },
  setDevice: (device) => {
    console.log('🔄 Store: device =', device?.name)
    set({ device, connected: !!device })
  },
  setSystemInfo: (systemInfo) => set({ systemInfo }),
  setMonitorActive: (monitorActive) => {
    console.log('🔄 Store: monitorActive =', monitorActive)
    set({ monitorActive })
  },
  setMonitorStatus: (monitorStatus) => set({ monitorStatus }),
  setWsConnected: (wsConnected) => {
    console.log('🔄 Store: wsConnected =', wsConnected)
    set({ wsConnected })
  },
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setActiveTab: (activeTab) => set({ activeTab }),
  reset: () => set({
    connected: false,
    device: null,
    monitorActive: false,
    monitorStatus: null,
  }),
}))