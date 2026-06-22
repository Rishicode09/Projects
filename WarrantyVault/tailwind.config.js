/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./App.tsx', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Material Design 3 inspired palette
        primary: {
          DEFAULT: '#4F46E5',
          container: '#E0E7FF',
        },
        secondary: {
          DEFAULT: '#0EA5E9',
        },
        success: '#16A34A',
        warning: '#F59E0B',
        danger: '#DC2626',
        surface: {
          light: '#FFFFFF',
          dark: '#1E293B',
        },
        background: {
          light: '#F8FAFC',
          dark: '#0F172A',
        },
      },
      fontFamily: {
        sans: ['System'],
      },
    },
  },
  plugins: [],
};
