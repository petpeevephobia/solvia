import { useState, useEffect } from 'react'
import { X, Download, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { auditService } from '@/services/audit'

interface PdfPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  auditId: string
  websiteUrl?: string
}

export function PdfPreviewModal({ isOpen, onClose, auditId, websiteUrl }: PdfPreviewModalProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  useEffect(() => {
    if (isOpen && auditId) {
      loadPdf()
    }

    return () => {
      // Cleanup blob URL when modal closes
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl)
      }
    }
  }, [isOpen, auditId])

  const loadPdf = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const blob = await auditService.downloadPdf(auditId)
      const url = URL.createObjectURL(blob)
      setPdfUrl(url)
    } catch (err) {
      console.error('Failed to load PDF:', err)
      setError('Failed to load PDF preview. Please try downloading instead.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownload = async () => {
    setIsDownloading(true)
    try {
      const blob = await auditService.downloadPdf(auditId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `seo_audit_${auditId}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to download PDF:', err)
      alert('Failed to download PDF. Please try again.')
    } finally {
      setIsDownloading(false)
    }
  }

  const handleClose = () => {
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl)
      setPdfUrl(null)
    }
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl mx-4 h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">PDF Preview</h3>
            {websiteUrl && (
              <p className="text-sm text-gray-500 mt-0.5">{websiteUrl}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleDownload}
              disabled={isDownloading || isLoading}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                'bg-primary-600 text-white hover:bg-primary-700',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isDownloading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {isDownloading ? 'Downloading...' : 'Download PDF'}
            </button>
            <button
              onClick={handleClose}
              className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
              title="Close"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* PDF Content */}
        <div className="flex-1 bg-gray-100 overflow-hidden">
          {isLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Loader2 className="w-10 h-10 text-primary-600 animate-spin mx-auto mb-4" />
                <p className="text-gray-600">Loading PDF preview...</p>
              </div>
            </div>
          )}

          {error && !isLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-5xl mb-4">📄</div>
                <p className="text-gray-600 mb-4">{error}</p>
                <button
                  onClick={handleDownload}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all mx-auto',
                    'bg-primary-600 text-white hover:bg-primary-700'
                  )}
                >
                  <Download className="w-4 h-4" />
                  Download PDF Instead
                </button>
              </div>
            </div>
          )}

          {pdfUrl && !isLoading && !error && (
            <object
              data={pdfUrl}
              type="application/pdf"
              className="w-full h-full"
            >
              {/* Fallback for browsers that don't support PDF embedding */}
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="text-5xl mb-4">📄</div>
                  <p className="text-gray-600 mb-4">
                    Your browser doesn't support PDF preview.
                  </p>
                  <button
                    onClick={handleDownload}
                    className={clsx(
                      'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all mx-auto',
                      'bg-primary-600 text-white hover:bg-primary-700'
                    )}
                  >
                    <Download className="w-4 h-4" />
                    Download PDF
                  </button>
                </div>
              </div>
            </object>
          )}
        </div>
      </div>
    </div>
  )
}
