import "./globals.css";

// "metadata" sets the browser tab title and description.
export const metadata = {
  title: "Household Expense Splitter",
  description: "Split shared expenses fairly with your flatmates",
};

// RootLayout wraps EVERY page. Here it just sets a light grey background
// and centers our content. {children} is whatever page is being shown.
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-100 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
