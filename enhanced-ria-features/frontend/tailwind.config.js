/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        tesla: {
          red: '#ff6b35',
          orange: '#f7931e',
          dark: '#0a0a0a',
          gray: '#1a1a1a',
        },
        zkp: {
          verified: '#00ff00',
          pending: '#ffa500',
          failed: '#ff0000',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic':
          'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'tesla-gradient': 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-in',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
