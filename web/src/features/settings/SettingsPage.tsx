import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { gscService } from '@/services/gsc'
import { useWebsiteStore } from '@/stores/websiteStore'
import { useAuthStore } from '@/stores/authStore'
import { authService } from '@/services/auth'
import type { GSCWebsite } from '@/types'
import { clsx } from 'clsx'

export default function SettingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { selectedWebsite, selectWebsite, setWebsites } = useWebsiteStore()
  const { user, logout } = useAuthStore()
  const [pendingSelection, setPendingSelection] = useState<string | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  // Fetch websites
  const { data: websites, isLoading: isLoadingWebsites } = useQuery({
    queryKey: ['gsc-websites'],
    queryFn: () => gscService.getWebsites(),
  })

  // Initialize pending selection with current selected website
  useEffect(() => {
    if (selectedWebsite && !pendingSelection) {
      setPendingSelection(selectedWebsite)
    }
  }, [selectedWebsite, pendingSelection])

  // Select website mutation
  const selectMutation = useMutation({
    mutationFn: (propertyUrl: string) => gscService.selectProperty(propertyUrl),
    onSuccess: (_, propertyUrl) => {
      selectWebsite(propertyUrl)
      if (websites) {
        setWebsites(websites)
      }
      // Update localStorage
      const selectedDomain = websites?.find(w => w.site_url === propertyUrl)
      if (selectedDomain) {
        localStorage.setItem('selected_domain', JSON.stringify({
          siteUrl: selectedDomain.site_url,
          siteName: getDomainName(selectedDomain)
        }))
      }
      // Invalidate all queries to refresh data
      queryClient.invalidateQueries()
      setHasChanges(false)
    },
  })

  const getDomainName = (website: GSCWebsite): string => {
    try {
      const url = new URL(website.site_url)
      return url.hostname.replace('www.', '')
    } catch {
      return website.site_url.replace(/^https?:\/\//, '').replace('www.', '').replace(/\/$/, '')
    }
  }

  const getDisplayUrl = (siteUrl: string): string => {
    return siteUrl.replace(/^https?:\/\//, '').replace(/\/$/, '')
  }

  const isHttps = (siteUrl: string): boolean => {
    return siteUrl.startsWith('https://')
  }

  const handleCardClick = (siteUrl: string) => {
    setPendingSelection(siteUrl)
    setHasChanges(siteUrl !== selectedWebsite)
  }

  const handleSaveChanges = () => {
    if (pendingSelection && pendingSelection !== selectedWebsite) {
      selectMutation.mutate(pendingSelection)
    }
  }

  const handleLogout = async () => {
    if (!confirm('Are you sure you want to log out?')) {
      return
    }
    try {
      await authService.logout()
    } catch {
      // Ignore errors
    }
    logout()
    navigate('/login')
  }

  return (
    <div className="p-8">
      {/* Page Header */}
      <div className="mb-10">
        <h1 className="text-h1 font-heading font-bold text-text-primary mb-2">Settings</h1>
        <p className="text-p1 font-sans text-text-secondary">Manage your Solvia preferences and configuration</p>
      </div>

      {/* Website Configuration Section */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-6">
        <h2 className="text-h2 font-heading font-semibold text-text-primary mb-2">Website Configuration</h2>
        <p className="text-p1 font-sans text-text-secondary mb-6">Select the Google Search Console property you want Solvia to analyze</p>

        {/* Card Selection Grid */}
        {isLoadingWebsites ? (
          <div className="text-center py-10">
            <div className="inline-block w-10 h-10 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin" />
            <p className="text-gray-500 mt-4">Loading your websites...</p>
          </div>
        ) : websites && websites.length > 0 ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
              {websites.map((website) => {
                const isSelected = pendingSelection === website.site_url

                return (
                  <div
                    key={website.site_url}
                    onClick={() => handleCardClick(website.site_url)}
                    className={clsx(
                      'relative bg-white border-2 rounded-xl p-5 cursor-pointer transition-all duration-200 overflow-hidden',
                      isSelected
                        ? 'border-primary-600 shadow-lg shadow-primary-600/15'
                        : 'border-gray-200 hover:border-primary-600 hover:shadow-md hover:-translate-y-0.5'
                    )}
                    style={isSelected ? {
                      background: 'linear-gradient(135deg, rgba(236, 96, 25, 0.05) 0%, rgba(236, 96, 25, 0.02) 100%)'
                    } : undefined}
                  >
                    {/* Top orange stripe for selected */}
                    {isSelected && (
                      <div
                        className="absolute top-0 left-0 right-0 h-[3px]"
                        style={{ background: 'linear-gradient(90deg, #EC6019, #FF8040)' }}
                      />
                    )}

                    {/* Check mark for selected state */}
                    <div className={clsx(
                      'absolute top-3 right-3 w-6 h-6 rounded-full bg-primary-600 flex items-center justify-center transition-all duration-300',
                      isSelected ? 'opacity-100 scale-100' : 'opacity-0 scale-0'
                    )}>
                      <Check className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
                    </div>

                    {/* Website Icon */}
                    <div
                      className="w-10 h-10 rounded-[10px] flex items-center justify-center mb-4"
                      style={{ background: 'linear-gradient(135deg, #EC6019 0%, #FF8040 100%)' }}
                    >
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        <path d="M2 17L12 22L22 17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        <path d="M2 12L12 17L22 12" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>

                    {/* Website URL */}
                    <div className="text-p1 font-sans font-semibold text-text-primary mb-2 break-words">
                      {getDisplayUrl(website.site_url)}
                    </div>

                    {/* Website Type Badge */}
                    <div className="text-p2 font-sans text-text-secondary flex items-center gap-1.5">
                      {isHttps(website.site_url) ? (
                        <>
                          <svg className="w-3.5 h-3.5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                          </svg>
                          <span>HTTPS</span>
                        </>
                      ) : (
                        <>
                          <svg className="w-3.5 h-3.5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 2a5 5 0 00-5 5v2a2 2 0 00-2 2v5a2 2 0 002 2h10a2 2 0 002-2v-5a2 2 0 00-2-2H7V7a3 3 0 015.905-.75 1 1 0 001.937-.5A5.002 5.002 0 0010 2z" />
                          </svg>
                          <span>HTTP</span>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Save Button */}
            <button
              onClick={handleSaveChanges}
              disabled={!hasChanges || selectMutation.isPending}
              className={clsx(
                'px-6 py-3 rounded-lg text-p1 font-sans font-medium transition-all',
                hasChanges && !selectMutation.isPending
                  ? 'bg-primary-600 text-white hover:bg-primary-700 cursor-pointer'
                  : 'bg-primary-600 text-white opacity-50 cursor-not-allowed'
              )}
            >
              {selectMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </>
        ) : (
          <div className="text-center py-10 text-p1 font-sans text-text-secondary">
            <p>No websites found in your Google Search Console account.</p>
          </div>
        )}
      </div>

      {/* Account Information Section */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 className="text-h2 font-heading font-semibold text-text-primary mb-5">Account Information</h2>
        <div>
          <label className="block text-p2 font-sans font-medium text-text-primary mb-2">Email Address</label>
          <div className="px-4 py-3 bg-gray-50 rounded-lg text-p1 font-sans text-text-primary">
            {user?.email || 'Loading...'}
          </div>
        </div>

        {/* Logout Link */}
        <button
          onClick={handleLogout}
          className="mt-8 text-p2 font-sans text-[#CB0000] hover:opacity-90 underline cursor-pointer bg-transparent border-none p-0 text-left"
        >
          Log out
        </button>
      </div>
    </div>
  )
}
