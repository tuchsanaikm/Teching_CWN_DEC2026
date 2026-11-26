import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#070d19',
          900: '#0b132b',
          800: '#131f3d',
          700: '#1c2d54',
        },
      },
      fontFamily: {
        sans: ['Sarabun', 'IBM Plex Sans Thai', 'Noto Sans Thai', 'Leelawadee UI', 'Tahoma', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
