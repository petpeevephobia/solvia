import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { gscService } from '@/services/gsc'
import { useWebsiteStore } from '@/stores/websiteStore'
import type { GSCWebsite } from '@/types'

export default function DomainSelectionPage() {
  const navigate = useNavigate()
  const { selectWebsite, setWebsites } = useWebsiteStore()
  const [selectedUrl, setSelectedUrl] = useState<string | null>(null)

  // Fetch and sync websites from GSC
  const { data: websites, isLoading, error, refetch } = useQuery({
    queryKey: ['gsc-websites-sync'],
    queryFn: async () => {
      // First sync websites from GSC, then get the list
      await gscService.syncWebsites()
      return gscService.getWebsites()
    },
    staleTime: 0, // Always fetch fresh on this page
    retry: 1,
  })

  // Mutation to select property
  const selectMutation = useMutation({
    mutationFn: async (propertyUrl: string) => {
      await gscService.selectProperty(propertyUrl)
      return propertyUrl
    },
    onSuccess: (propertyUrl) => {
      // Update store
      selectWebsite(propertyUrl)
      if (websites) {
        setWebsites(websites)
      }
      // Store in localStorage for compatibility
      const selectedDomain = websites?.find(w => w.site_url === propertyUrl)
      if (selectedDomain) {
        localStorage.setItem('selected_domain', JSON.stringify({
          siteUrl: selectedDomain.site_url,
          siteName: getDomainName(selectedDomain)
        }))
      }
      // Redirect to dashboard
      setTimeout(() => {
        navigate('/dashboard', { replace: true })
      }, 300)
    },
  })

  const getDomainName = (website: GSCWebsite): string => {
    try {
      const url = new URL(website.site_url)
      return url.hostname.replace('www.', '')
    } catch {
      return website.site_url.replace(/^https?:\/\//, '').replace('www.', '')
    }
  }

  const handleSelect = (siteUrl: string) => {
    setSelectedUrl(siteUrl)
    selectMutation.mutate(siteUrl)
  }

  const handleRefresh = () => {
    refetch()
  }

  const handleReAuthenticate = () => {
    localStorage.removeItem('solvia-auth')
    localStorage.removeItem('selected_domain')
    window.location.href = '/login'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f8fafc] to-[#e2e8f0] flex items-center justify-center p-8">
      <div className="w-full max-w-[600px]">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Header */}
          <div className="text-center py-12 px-8 bg-gradient-to-br from-[#fff7ed] to-[#fed7aa]">
            <img
              src="/images/orange-svg-emblem.svg"
              alt="Solvia"
              className="w-16 h-16 mx-auto mb-6"
            />
            <h1 className="text-[2rem] font-bold text-gray-900 mb-2">
              Select Your Domain
            </h1>
            <p className="text-gray-500 text-lg">
              Choose which website you'd like Solvia to track and analyze
            </p>
          </div>

          {/* Domain List */}
          <div className="p-8">
            {isLoading ? (
              <div className="text-center text-gray-500 py-8">
                <svg className="w-8 h-8 animate-spin mx-auto mb-4 text-[#EC6019]" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Loading your domains...
              </div>
            ) : error ? (
              <div className="text-center text-gray-500 py-8">
                <p className="mb-4">Error loading domains. Please try again.</p>
                <button
                  onClick={handleRefresh}
                  className="text-[#EC6019] hover:underline"
                >
                  Retry
                </button>
              </div>
            ) : websites && websites.length > 0 ? (
              <div className="space-y-4">
                {websites.map((website) => {
                  const domainName = getDomainName(website)
                  const isSelected = selectedUrl === website.site_url
                  const isSelecting = selectMutation.isPending && selectedUrl === website.site_url

                  return (
                    <div
                      key={website.site_url}
                      onClick={() => !selectMutation.isPending && handleSelect(website.site_url)}
                      className={`flex items-center p-6 border-2 rounded-xl cursor-pointer transition-all duration-200 ${
                        isSelected
                          ? 'border-[#f97316] bg-[#fff7ed]'
                          : 'border-gray-200 hover:border-[#f97316] hover:shadow-lg hover:-translate-y-0.5'
                      } ${selectMutation.isPending && !isSelected ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {/* Icon */}
                      <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center mr-4 flex-shrink-0">
                        <svg className="w-6 h-6 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                          <polyline points="9,22 9,12 15,12 15,22" />
                        </svg>
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="text-lg font-semibold text-gray-900 truncate">
                          {domainName}
                        </div>
                        <div className="text-gray-500 text-sm truncate">
                          {website.site_url}
                        </div>
                      </div>

                      {/* Indicator */}
                      <div className={`w-6 h-6 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                        isSelected
                          ? 'border-[#f97316] bg-[#f97316]'
                          : 'border-gray-300'
                      }`}>
                        {isSelecting ? (
                          <svg className="w-3 h-3 animate-spin text-white" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                        ) : isSelected ? (
                          <div className="w-2 h-2 bg-white rounded-full" />
                        ) : null}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                <p className="mb-4">No domains found in your Google Search Console account.</p>
                <p className="text-sm mb-4">This usually means you need to re-authenticate with Google.</p>
                <button
                  onClick={handleReAuthenticate}
                  className="px-6 py-3 bg-[#EC6019] text-white rounded-lg hover:bg-[#d45415] transition-all"
                >
                  Re-authenticate with Google
                </button>
              </div>
            )}
          </div>

          {/* Actions */}
          {websites && websites.length > 0 && (
            <div className="px-8 py-6 border-t border-gray-200 flex items-center justify-center gap-4">
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-all disabled:opacity-50"
              >
                <svg className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="23 4 23 10 17 10" />
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                </svg>
                Refresh Domains
              </button>
              <button
                onClick={handleReAuthenticate}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#EC6019] text-white rounded-lg hover:bg-[#d45415] transition-all"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 12l2 2 4-4" />
                  <circle cx="12" cy="12" r="10" />
                </svg>
                Re-authenticate with Google
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
