import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/authStore'

// Navigation items matching original
const navItems = [
  {
    path: '/dashboard',
    label: 'Dashboard',
    icon: (
      <svg className="nav-item-icon" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
      </svg>
    ),
  },
  {
    path: '/audit',
    label: 'Audit History',
    icon: (
      <svg className="nav-item-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
      </svg>
    ),
  },
]

export default function Sidebar() {
  const [isHovered, setIsHovered] = useState(false)
  const { logout, user } = useAuthStore()

  return (
    <aside
      className={clsx(
        'hidden md:flex flex-col bg-white border-r border-gray-200',
        'h-screen flex-shrink-0 transition-all duration-300 ease-in-out',
        isHovered ? 'w-[233px]' : 'w-[80px]'
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Logo Header - matches original sidebar-header */}
      <div
        className={clsx(
          'min-h-[80px] border-b border-gray-200 flex items-center',
          isHovered ? 'px-6 justify-start gap-3' : 'justify-center'
        )}
      >
        <div className="flex-shrink-0">
          <img
            src={isHovered ? '/images/logo_v2.png' : '/images/orange-svg-emblem.svg'}
            alt="Solvia"
            className={clsx(
              'transition-all duration-300',
              isHovered ? 'h-7 w-auto max-w-[140px]' : 'w-7 h-7'
            )}
          />
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-5 px-4">
        {navItems.map(({ path, icon, label }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              clsx(
                'nav-item flex items-center rounded-lg cursor-pointer transition-all duration-200 mb-1',
                'text-gray-500 hover:bg-gray-100 hover:text-gray-900',
                isHovered ? 'justify-start px-4 py-3 gap-3' : 'justify-center p-3',
                isActive && 'bg-[#FEF3E7] !text-primary-600'
              )
            }
          >
            {icon}
            <span
              className={clsx(
                'nav-item-text text-sm font-medium transition-all duration-300',
                isHovered ? 'opacity-100 w-auto' : 'opacity-0 w-0 overflow-hidden'
              )}
            >
              {label}
            </span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        {/* AI Chat Model indicator */}
        <div
          className={clsx(
            'transition-all duration-300 mb-3',
            isHovered ? 'opacity-100 px-4' : 'opacity-0 h-0 overflow-hidden'
          )}
        >
          <p className="text-xs text-gray-400 whitespace-nowrap">AI Model: Gemini 2.0</p>
        </div>

        {/* Separator below AI model text */}
        <div className={clsx('h-px bg-gray-200 mb-3', !isHovered && 'hidden')} />

        {/* Settings */}
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            clsx(
              'sidebar-footer-item flex items-center rounded-lg cursor-pointer transition-all duration-200 mb-1',
              'text-gray-500 hover:bg-gray-100 hover:text-gray-900',
              isHovered ? 'justify-start px-4 py-3 gap-3' : 'justify-center p-3',
              isActive && 'bg-[#FEF3E7] !text-primary-600'
            )
          }
        >
          <svg className="nav-item-icon w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
          </svg>
          <span
            className={clsx(
              'nav-item-text text-sm font-medium transition-all duration-300',
              isHovered ? 'opacity-100 w-auto' : 'opacity-0 w-0 overflow-hidden'
            )}
          >
            Settings
          </span>
        </NavLink>

        {/* Logout */}
        <button
          onClick={logout}
          className={clsx(
            'sidebar-footer-item flex items-center rounded-lg cursor-pointer transition-all duration-200 mb-1 w-full',
            'text-gray-500 hover:bg-gray-100 hover:text-gray-900',
            isHovered ? 'justify-start px-4 py-3 gap-3' : 'justify-center p-3'
          )}
        >
          <svg className="nav-item-icon w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clipRule="evenodd" />
          </svg>
          <span
            className={clsx(
              'nav-item-text text-sm font-medium transition-all duration-300',
              isHovered ? 'opacity-100 w-auto' : 'opacity-0 w-0 overflow-hidden'
            )}
          >
            Log out
          </span>
        </button>

        {/* Separator */}
        <div className={clsx('h-px bg-gray-200 my-3', !isHovered && 'hidden')} />

        {/* User Info */}
        <div
          className={clsx(
            'user-info flex items-center rounded-lg',
            isHovered ? 'justify-start px-4 py-3 gap-3' : 'justify-center p-3'
          )}
        >
          {/* User Avatar - Orange badge */}
          <div className="w-8 h-8 bg-[#FFEADE] rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-[18px] h-[18px] text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
          </div>
          {/* User Email */}
          <div
            className={clsx(
              'transition-all duration-300 overflow-hidden',
              isHovered ? 'opacity-100 w-auto max-w-[150px]' : 'opacity-0 w-0'
            )}
          >
            <p className="text-[13px] text-gray-500 truncate">
              {user?.email || 'Loading...'}
            </p>
          </div>
        </div>
      </div>
    </aside>
  )
}
