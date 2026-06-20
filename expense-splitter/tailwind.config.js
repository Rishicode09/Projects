/** @type {import('tailwindcss').Config} */
module.exports = {
  // "content" tells Tailwind which files to scan for class names like "bg-slate-100".
  content: [
    "./app/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
