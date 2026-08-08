"use client";

import Link from "next/link";

import { ShoppingCart } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function AppNavbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          href="/app"
          className="text-2xl font-bold tracking-tight"
        >
          Cartel
        </Link>

        <div className="flex items-center gap-3">
          <Button variant="ghost">
            Search
          </Button>

          <Button variant="ghost">
            Profile
          </Button>

          <Button>
            <ShoppingCart className="mr-2 h-4 w-4" />
            Cart
          </Button>
        </div>
      </div>
    </header>
  );
}