import "./globals.css";

export const metadata = {
  title: "Household Expense Splitter",
  description: "Split shared expenses fairly with your flatmates",
  manifest: "/manifest.json",
};

export const viewport = {
  themeColor: "#0f172a",
};

// This tiny script runs BEFORE the page paints, so dark mode never "flashes"
// the light theme on load. It also registers the service worker for offline use.
const headScript = `
  try {
    if (localStorage.getItem('es_dark') === 'true') {
      document.documentElement.classList.add('dark');
    }
  } catch (e) {}
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js').catch(function () {});
    });
  }
`;

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: headScript }} />
      </head>
      <body className="min-h-screen bg-slate-100 text-slate-900 antialiased transition-colors dark:bg-slate-950 dark:text-slate-100">
        {children}
      </body>
    </html>
  );
}
