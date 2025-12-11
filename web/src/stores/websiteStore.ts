import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { GSCWebsite } from '@/types'

interface WebsiteState {
  websites: GSCWebsite[]
  selectedWebsite: string | null
  isLoading: boolean

  // Actions
  setWebsites: (websites: GSCWebsite[]) => void
  selectWebsite: (url: string) => void
  setLoading: (loading: boolean) => void
}

export const useWebsiteStore = create<WebsiteState>()(
  persist(
    (set) => ({
      websites: [],
      selectedWebsite: null,
      isLoading: false,

      setWebsites: (websites) =>
        set({
          websites,
          // Do NOT auto-select - match original behavior
          // User must manually select website in Settings page
        }),

      selectWebsite: (url) =>
        set({
          selectedWebsite: url,
        }),

      setLoading: (isLoading) =>
        set({
          isLoading,
        }),
    }),
    {
      name: 'solvia-website',
      partialize: (state) => ({
        selectedWebsite: state.selectedWebsite,
      }),
    }
  )
)
