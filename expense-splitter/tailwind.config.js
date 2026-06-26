/** @type {import('tailwindcss').Config} */
module.exports = {
  // "class" = dark mode turns on when a "dark" class is on the <html> element.
  darkMode: "class",
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
