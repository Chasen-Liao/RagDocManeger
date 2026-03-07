/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        'sans': ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Text', 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'sans-serif'],
        'mono': ['SF Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
      colors: {
        // Anthropic-style neutral palette - warm grays
        gray: {
          25: '#FAFAF9',
          50: '#F5F5F4',
          100: '#E7E7E5',
          200: '#D4D4D1',
          300: '#A3A3A0',
          400: '#71716E',
          500: '#57554E',
          600: '#44443F',
          700: '#36352F',
          800: '#292825',
          850: '#1F1F1D',
          900: '#151514',
        },
        // Anthropic blue accent
        accent: {
          50: '#F0F5FF',
          100: '#E0EBFF',
          200: '#C7D9FF',
          300: '#A4C0FF',
          400: '#7096FF',
          500: '#4B7AFF',
          600: '#2A5EFF',
          700: '#0A35CC',
          800: '#082999',
          900: '#052066',
        },
        light: {
          bg: '#F7F7F5',
          card: '#FFFFFF',
          cta: '#0A35CC',
          text: '#31312D',
          border: '#E8E8E6',
          'text-secondary': '#6B6B65',
        },
        dark: {
          bg: '#0D0D0C',
          card: '#1A1A19',
          cta: '#7096FF',
          text: '#EAEAE8',
          border: '#3A3A38',
          'text-secondary': '#989894',
        }
      },
      boxShadow: {
        'soft': '0 1px 2px 0 rgba(0, 0, 0, 0.04)',
        'card': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'card-hover': '0 4px 8px -2px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
        'dropdown': '0 10px 20px -5px rgba(0, 0, 0, 0.15)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
        'scale-in': 'scaleIn 0.15s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      borderRadius: {
        'xl': '0.5rem',
        '2xl': '0.625rem',
        '3xl': '0.875rem',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      }
    },
  },
  plugins: [],
}