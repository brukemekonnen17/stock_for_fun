import './globals.css'

export const metadata = {
  title: 'Catalyst Radar',
  description: 'Real-time catalyst scanning and trading insights',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

