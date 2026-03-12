import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, Globe, Settings } from 'lucide-react'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/authStore'
import { useWebsiteStore } from '@/stores/websiteStore'
import { authService } from '@/services/auth'

export default function Header() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { websites, selectedWebsite, selectWebsite } = useWebsiteStore()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showWebsiteMenu, setShowWebsiteMenu] = useState(false)

  const handleLogout = async () => {
    try {
      await authService.logout()
    } catch {
      // Ignore errors
    }
    logout()
    navigate('/login')
  }

  return (
    <header className="h-16 bg-background-card border-b border-gray-100 flex items-center justify-between px-4 md:px-6 shadow-sm">
      {/* Website selector */}
      <div className="relative">
        <button
          onClick={() => setShowWebsiteMenu(!showWebsiteMenu)}
          className={clsx(
            'flex items-center gap-2 px-3 py-2 rounded-lg',
            'transition-all duration-200',
            'hover:bg-gray-50 border border-transparent',
            showWebsiteMenu && 'bg-gray-50 border-gray-200'
          )}
        >
          <div className="p-1.5 bg-primary-100 rounded-lg">
            <Globe className="w-4 h-4 text-primary-600" />
          </div>
          <span className="text-p2 font-medium text-text-primary max-w-[200px] truncate hidden sm:block">
            {selectedWebsite || 'Select website'}
          </span>
          <ChevronDown className={clsx(
            'w-4 h-4 text-text-muted transition-transform duration-200',
            showWebsiteMenu && 'rotate-180'
          )} />
        </button>

        {showWebsiteMenu && websites.length > 0 && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setShowWebsiteMenu(false)} />
            <div className="absolute top-full left-0 mt-2 w-72 bg-background-card rounded-card shadow-modal border border-gray-100 py-2 z-20 animate-fade-in">
              <div className="px-4 py-2 border-b border-gray-100">
                <p className="text-note font-sans text-text-muted font-medium uppercase tracking-wide">
                  Connected Sites
                </p>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {websites.map((site) => (
                  <button
                    key={site.site_url}
                    onClick={() => {
                      selectWebsite(site.site_url)
                      setShowWebsiteMenu(false)
                    }}
                    className={clsx(
                      'w-full text-left px-4 py-3 text-p2 transition-colors',
                      'hover:bg-gray-50',
                      selectedWebsite === site.site_url && 'bg-primary-50 text-primary-700'
                    )}
                  >
                    <span className="block truncate">{site.site_url}</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* User menu */}
      <div className="relative">
        <button
          onClick={() => setShowUserMenu(!showUserMenu)}
          className={clsx(
            'flex items-center gap-3 px-3 py-2 rounded-lg',
            'transition-all duration-200',
            'hover:bg-gray-50 border border-transparent',
            showUserMenu && 'bg-gray-50 border-gray-200'
          )}
        >
          {user?.picture ? (
            <img
              src={user.picture}
              alt={user.name}
              className="w-8 h-8 rounded-full ring-2 ring-primary-100"
            />
          ) : (
            <div className="w-8 h-8 bg-gradient-primary rounded-full flex items-center justify-center">
              <span className="text-white text-p2 font-sans font-medium">
                {user?.email?.charAt(0).toUpperCase()}
              </span>
            </div>
          )}
          <div className="text-left hidden sm:block">
            <p className="text-p2 font-medium text-text-primary line-clamp-1">
              {user?.name || user?.email?.split('@')[0]}
            </p>
          </div>
          <ChevronDown className={clsx(
            'w-4 h-4 text-text-muted transition-transform duration-200 hidden sm:block',
            showUserMenu && 'rotate-180'
          )} />
        </button>

        {showUserMenu && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setShowUserMenu(false)} />
            <div className="absolute top-full right-0 mt-2 w-56 bg-background-card rounded-card shadow-modal border border-gray-100 py-2 z-20 animate-fade-in">
              {/* User info */}
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-p2 font-medium text-text-primary truncate">
                  {user?.name || user?.email?.split('@')[0]}
                </p>
                <p className="text-note font-sans text-text-muted truncate">{user?.email}</p>
              </div>

              {/* Menu items */}
              <div className="py-1">
                <button
                  onClick={() => {
                    navigate('/settings')
                    setShowUserMenu(false)
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-p2 text-text-primary hover:bg-gray-50 transition-colors"
                >
                  <Settings className="w-4 h-4 text-text-muted" />
                  Settings
                </button>
              </div>

              {/* Logout */}
              <div className="border-t border-gray-100 pt-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-p2 text-status-error hover:bg-red-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </header>
  )
}
