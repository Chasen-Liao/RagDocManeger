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
        'title': ['Archivo', 'system-ui', 'sans-serif'],
        'body': ['Space Grotesk', 'system-ui', 'sans-serif'],
      },
      colors: {
        light: {
          bg: '#F8FAFC',
          card: '#FFFFFF',
          cta: '#2563EB',
          text: '#1E293B',
          border: '#E2E8F0',
        },
        dark: {
          bg: '#0F172A',
          card: '#1E293B',
          cta: '#3B82F6',
          text: '#F1F5F9',
          border: '#334155',
        }
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.07)',
        'glass-dark': '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
