import { useQuery } from '@tanstack/react-query'
import { Search, TrendingUp, ExternalLink } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import { gscService } from '@/services/gsc'
import { useWebsiteStore } from '@/stores/websiteStore'

export default function GSCPage() {
  const { selectedWebsite } = useWebsiteStore()

  const { data: queries, isLoading: queriesLoading } = useQuery({
    queryKey: ['gsc-queries', selectedWebsite],
    queryFn: () => gscService.getQueries(selectedWebsite!),
    enabled: !!selectedWebsite,
  })

  const { data: pages, isLoading: pagesLoading } = useQuery({
    queryKey: ['gsc-pages', selectedWebsite],
    queryFn: () => gscService.getPages(selectedWebsite!),
    enabled: !!selectedWebsite,
  })

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Search Console</h1>
        <p className="text-gray-600 mt-1">View your Google Search Console data</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Queries */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="w-5 h-5" />
              Top Queries
            </CardTitle>
          </CardHeader>
          <CardContent>
            {queriesLoading ? (
              <p className="text-gray-500">Loading...</p>
            ) : queries && queries.length > 0 ? (
              <div className="space-y-3">
                {queries.slice(0, 10).map((query, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">{query.query}</p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                        <span>{query.clicks} clicks</span>
                        <span>{query.impressions} impr.</span>
                        <span>{(query.ctr * 100).toFixed(1)}% CTR</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-sm text-gray-600">
                      <TrendingUp className="w-4 h-4" />
                      {query.position.toFixed(1)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No query data available</p>
            )}
          </CardContent>
        </Card>

        {/* Top Pages */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ExternalLink className="w-5 h-5" />
              Top Pages
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pagesLoading ? (
              <p className="text-gray-500">Loading...</p>
            ) : pages && pages.length > 0 ? (
              <div className="space-y-3">
                {pages.slice(0, 10).map((page, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate text-sm">{page.page}</p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                        <span>{page.clicks} clicks</span>
                        <span>{page.impressions} impr.</span>
                        <span>{(page.ctr * 100).toFixed(1)}% CTR</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-sm text-gray-600">
                      <TrendingUp className="w-4 h-4" />
                      {page.position.toFixed(1)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No page data available</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
