"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";

const navigation = [
  { name: "Features", href: "/features" },
  { name: "Roadmap", href: "/roadmap" },
  { name: "Docs", href: "/docs" },
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link
          href="/"
          className="text-2xl font-bold tracking-tight transition-opacity hover:opacity-80"
        >
          Cartel
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {navigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {item.name}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost">
              Log in
            </Button>
          </Link>

          <Link href="/signup">
            <Button>
              Get Started
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}