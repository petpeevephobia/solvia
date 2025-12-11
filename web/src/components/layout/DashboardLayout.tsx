import { useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Sidebar from './Sidebar'
import MobileDock from './MobileDock'
import { gscService } from '@/services/gsc'
import { useWebsiteStore } from '@/stores/websiteStore'

export default function DashboardLayout() {
  const navigate = useNavigate()
  const { setWebsites, setLoading, selectWebsite } = useWebsiteStore()
  const [hasCheckedSelection, setHasCheckedSelection] = useState(false)

  // Fetch websites on mount
  const { data: websites, isLoading: websitesLoading } = useQuery({
    queryKey: ['gsc-websites'],
    queryFn: () => gscService.getWebsites(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    retry: 1,
  })

  // Fetch selected website from backend (1:1 parity with original Python)
  const { data: selectedWebsite, isLoading: selectedLoading, isFetched } = useQuery({
    queryKey: ['gsc-selected-website'],
    queryFn: () => gscService.getSelectedWebsite(),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  // Update store when websites are fetched
  useEffect(() => {
    setLoading(websitesLoading || selectedLoading)
    if (websites && websites.length > 0) {
      setWebsites(websites)
    }
  }, [websites, websitesLoading, selectedLoading, setWebsites, setLoading])

  // Update store when selected website is fetched from backend
  useEffect(() => {
    if (selectedWebsite) {
      selectWebsite(selectedWebsite)
    }
  }, [selectedWebsite, selectWebsite])

  // Redirect to domain-selection if no website selected (1:1 parity with original)
  useEffect(() => {
    if (isFetched && !hasCheckedSelection) {
      setHasCheckedSelection(true)
      if (!selectedWebsite) {
        // No website selected, redirect to domain selection
        navigate('/domain-selection', { replace: true })
      }
    }
  }, [isFetched, selectedWebsite, hasCheckedSelection, navigate])

  return (
    <div className="min-h-screen flex bg-[#F9FAFB]">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Main Content Area - matches original .main-content */}
      <main className="flex-1 h-screen max-h-screen overflow-y-auto">
        <div className="p-8 pb-24 md:pb-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile Dock */}
      <MobileDock />
    </div>
  )
}
