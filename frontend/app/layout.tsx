import "./globals.css";

import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export const metadata = {
  title: "AgentBench Lite",
  description: "Agent execution and benchmark harness",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main className="mx-auto min-h-screen max-w-7xl px-6 py-8">
          <nav className="mb-8 flex flex-wrap items-center justify-between gap-4" aria-label="Main navigation">
            <Link href="/dashboard" className="text-xl font-semibold">
              AgentBench Lite
            </Link>
            <div className="flex gap-2">
              <Button variant="ghost" asChild>
                <Link href="/dashboard">Dashboard</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/tasks">Tasks</Link>
              </Button>
              <Button variant="ghost" asChild>
                <Link href="/benchmarks">Benchmarks</Link>
              </Button>
            </div>
          </nav>
          {children}
        </main>
      </body>
    </html>
  );
}
