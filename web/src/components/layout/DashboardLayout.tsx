import { useEffect, useState, useCallback } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Sidebar from './Sidebar'
import MobileDock from './MobileDock'
import { AuditProgressBanner, AuditResultModal } from '@/features/dashboard/components'
import { gscService } from '@/services/gsc'
import { auditService } from '@/services/audit'
import { useWebsiteStore } from '@/stores/websiteStore'
import { useAuditStore } from '@/stores/auditStore'

export default function DashboardLayout() {
  const navigate = useNavigate()
  const { setWebsites, setLoading, selectWebsite } = useWebsiteStore()
  const { auditProgress, auditResultModal, setAuditResultModal } = useAuditStore()
  const [hasCheckedSelection, setHasCheckedSelection] = useState(false)

  const handleAuditModalClose = useCallback(() => {
    setAuditResultModal((prev) => ({ ...prev, isVisible: false }))
  }, [setAuditResultModal])

  const handleDownloadPdf = useCallback(async () => {
    const result = useAuditStore.getState().auditResultModal.result
    if (!result?.id) return
    setAuditResultModal((prev) => ({ ...prev, isDownloading: true }))
    try {
      const blob = await auditService.downloadPdf(String(result.id))
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `seo_audit_${result.id}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download PDF:', error)
      alert('Failed to download PDF. Please try again.')
    } finally {
      setAuditResultModal((prev) => ({ ...prev, isDownloading: false }))
    }
  }, [setAuditResultModal])

  const handleDownloadJson = useCallback(() => {
    const result = useAuditStore.getState().auditResultModal.result
    if (!result) return
    const dataStr = JSON.stringify(result, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `seo_audit_${result.id}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }, [])

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
      {/* Audit progress banner and result modal — visible on all dashboard routes */}
      <AuditProgressBanner
        isVisible={auditProgress.isVisible}
        progress={auditProgress.progress}
        message={auditProgress.message}
      />
      <AuditResultModal
        isVisible={auditResultModal.isVisible}
        auditResult={auditResultModal.result}
        onClose={handleAuditModalClose}
        onDownloadPdf={handleDownloadPdf}
        onDownloadJson={handleDownloadJson}
        isDownloading={auditResultModal.isDownloading}
      />

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
