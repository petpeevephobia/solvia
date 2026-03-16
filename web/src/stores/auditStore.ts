import { create } from 'zustand'
import type { AuditResult } from '@/types'

export interface AuditProgressState {
  isVisible: boolean
  progress: number
  message: string
}

export interface AuditResultModalState {
  isVisible: boolean
  result: AuditResult | null
  isDownloading: boolean
}

type AuditProgressUpdate =
  | Partial<AuditProgressState>
  | ((prev: AuditProgressState) => Partial<AuditProgressState>)
type AuditResultModalUpdate =
  | Partial<AuditResultModalState>
  | ((prev: AuditResultModalState) => Partial<AuditResultModalState>)

interface AuditState {
  auditProgress: AuditProgressState
  auditResultModal: AuditResultModalState
  setAuditProgress: (update: AuditProgressUpdate) => void
  setAuditResultModal: (update: AuditResultModalUpdate) => void
}

const initialProgress: AuditProgressState = {
  isVisible: false,
  progress: 0,
  message: 'Initializing...',
}

const initialResultModal: AuditResultModalState = {
  isVisible: false,
  result: null,
  isDownloading: false,
}

export const useAuditStore = create<AuditState>()((set) => ({
  auditProgress: initialProgress,
  auditResultModal: initialResultModal,

  setAuditProgress: (update) =>
    set((state) => ({
      auditProgress: {
        ...state.auditProgress,
        ...(typeof update === 'function' ? update(state.auditProgress) : update),
      },
    })),

  setAuditResultModal: (update) =>
    set((state) => ({
      auditResultModal: {
        ...state.auditResultModal,
        ...(typeof update === 'function' ? update(state.auditResultModal) : update),
      },
    })),
}))
