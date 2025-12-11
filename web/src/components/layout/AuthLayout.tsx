import { Outlet } from 'react-router-dom'

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex">
      {/* Left side - Hero Image */}
      <div className="hidden lg:block lg:w-1/2 relative bg-gray-100">
        <img
          src="/images/login-image.jpg"
          alt="Professional on phone call"
          className="absolute inset-0 w-full h-full object-cover"
        />
      </div>

      {/* Right side - Auth content */}
      <div className="flex-1 flex items-center justify-center p-8 lg:p-16 bg-white">
        <div className="w-full max-w-[400px]">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
