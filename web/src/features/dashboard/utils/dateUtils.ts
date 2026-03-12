// Date filter utilities for Dashboard

export type DatePreset = '24h' | '7d' | '28d' | '3mo' | 'custom'

export function calculateDateRange(preset: DatePreset): { startDate: string; endDate: string } {
  const today = new Date()
  const endDate = new Date(today)
  endDate.setDate(endDate.getDate() - 1) // GSC has 1-day delay

  const startDate = new Date(endDate)

  switch (preset) {
    case '24h':
      // Single day: startDate = endDate (yesterday)
      // No modification needed - startDate already equals endDate
      break
    case '7d':
      startDate.setDate(startDate.getDate() - 7)
      break
    case '28d':
      startDate.setDate(startDate.getDate() - 28)
      break
    case '3mo':
      startDate.setMonth(startDate.getMonth() - 3)
      break
    default:
      startDate.setDate(startDate.getDate() - 28)
  }

  return {
    startDate: startDate.toISOString().split('T')[0],
    endDate: endDate.toISOString().split('T')[0],
  }
}

export const DATE_PRESET_LABELS: Record<DatePreset, string> = {
  '24h': 'last 24 hours',
  '7d': 'past 7 days',
  '28d': 'past 28 days',
  '3mo': 'past 3 months',
  'custom': 'custom range',
}

export function formatDateDisplay(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatDateRangeDisplay(startDate: string, endDate: string): string {
  return `${formatDateDisplay(startDate)} to ${formatDateDisplay(endDate)}`
}

export function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toLocaleString()
}
