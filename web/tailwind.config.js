/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Solvia Brand Colors - Primary Orange
        primary: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f97316',
          600: '#EC6019', // Main Solvia Orange
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
          950: '#431407',
        },
        // Background Colors
        background: {
          light: '#F5F5FA',
          card: '#FFFFFF',
          sidebar: '#1A1A2E',
          'sidebar-hover': '#252542',
        },
        // Text Colors
        text: {
          primary: '#1F2937',
          secondary: '#6B7280',
          muted: '#9CA3AF',
          inverse: '#FFFFFF',
        },
        // Status Colors
        status: {
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
          info: '#3B82F6',
        },
        // SEO Score Colors
        score: {
          excellent: '#22c55e', // 80-100
          good: '#84cc16',      // 60-79
          average: '#eab308',   // 40-59
          poor: '#f97316',      // 20-39
          critical: '#ef4444',  // 0-19
        },
        // SEO Stage Colors
        stage: {
          hidden: '#EF4444',
          emerging: '#F59E0B',
          discoverable: '#3B82F6',
          trusted: '#10B981',
        },
      },
      fontFamily: {
        sans: ['Nunito', 'system-ui', 'sans-serif'],
        heading: ['Poppins', 'system-ui', 'sans-serif'],
        ui: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display': ['3rem', { lineHeight: '1.1', fontWeight: '700' }],
        'h1': ['2rem', { lineHeight: '1.2', fontWeight: '600' }],
        'h2': ['1.5rem', { lineHeight: '1.3', fontWeight: '600' }],
        'h3': ['1.25rem', { lineHeight: '1.4', fontWeight: '600' }],
        'h4': ['1.125rem', { lineHeight: '1.4', fontWeight: '600' }],
        'body': ['1rem', { lineHeight: '1.5' }],
        'body-sm': ['0.875rem', { lineHeight: '1.5' }],
        'caption': ['0.75rem', { lineHeight: '1.4' }],
      },
      spacing: {
        'sidebar-collapsed': '80px',
        'sidebar-expanded': '233px',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.12)',
        'button': '0 2px 4px rgba(236, 96, 25, 0.2)',
        'button-hover': '0 4px 8px rgba(236, 96, 25, 0.3)',
        'sidebar': '2px 0 8px rgba(0, 0, 0, 0.1)',
        'modal': '0 8px 32px rgba(0, 0, 0, 0.2)',
      },
      borderRadius: {
        'card': '16px',
        'button': '12px',
        'input': '8px',
        'full': '9999px',
      },
      transitionDuration: {
        'sidebar': '300ms',
      },
      transitionTimingFunction: {
        'sidebar': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      animation: {
        'score-fill': 'scoreFill 1s ease-out forwards',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s infinite',
      },
      keyframes: {
        scoreFill: {
          '0%': { strokeDashoffset: '283' },
          '100%': { strokeDashoffset: 'var(--score-offset)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #EC6019 0%, #f97316 100%)',
        'gradient-sidebar': 'linear-gradient(180deg, #1A1A2E 0%, #16162A 100%)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
