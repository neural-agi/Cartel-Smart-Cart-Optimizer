"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Calculator,
  CircleUserRound,
  LayoutDashboard,
  Search,
  Settings,
  ShoppingCart,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";

export const appNavigation = [
  { label: "Home", href: "/home", icon: LayoutDashboard },
  { label: "Search", href: "/search", icon: Search },
  { label: "Cart", href: "/cart", icon: ShoppingCart },
  { label: "Optimize", href: "/optimize", icon: Sparkles },
  { label: "Results", href: "/results", icon: BarChart3 },
  { label: "Wrapped", href: "/wrapped", icon: Calculator },
  { label: "Profile", href: "/profile", icon: CircleUserRound },
  { label: "Settings", href: "/settings", icon: Settings },
] as const;

interface AppSidebarProps {
  onNavigate?: () => void;
}

export default function AppSidebar({ onNavigate }: AppSidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-background">
      <div className="flex h-16 shrink-0 items-center border-b border-border px-6">
        <Link href="/home" className="text-xl font-bold tracking-tight" onClick={onNavigate}>
          Cartel
        </Link>
      </div>

      <nav aria-label="Application navigation" className="flex-1 space-y-1 overflow-y-auto p-4">
        {appNavigation.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4">
        <p className="px-3 text-xs text-muted-foreground">Your grocery command center</p>
      </div>
    </aside>
  );
}
