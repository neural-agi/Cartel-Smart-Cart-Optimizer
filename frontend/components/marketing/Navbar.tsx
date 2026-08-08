"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { motion } from "framer-motion";
import { ArrowRight, Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Features", href: "/features" },
  { name: "How it Works", href: "/#how-it-works" },
  { name: "Roadmap", href: "/roadmap" },
  { name: "Docs", href: "/docs" },
  { name: "Pricing", href: "/#pricing" },
];

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();

  const [isScrolled, setIsScrolled] = useState(false);
  const [hash, setHash] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 8);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const updateHash = () => {
      setHash(window.location.hash);
    };

    updateHash();
    window.addEventListener("hashchange", updateHash);

    return () => window.removeEventListener("hashchange", updateHash);
  }, []);

  const isActive = (href: string) => {
    const [pathPart, hashPart] = href.split("#");
    const targetPath = pathPart || "/";
    const targetHash = hashPart ? `#${hashPart}` : "";

    if (targetHash) {
      return pathname === targetPath && hash === targetHash;
    }

    return pathname === targetPath || pathname.startsWith(`${targetPath}/`);
  };

  const navigate = (href: string) => {
    setMobileOpen(false);
    router.push(href);
  };

  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full border-b bg-background/70 backdrop-blur-xl transition-all duration-300",
        isScrolled ? "border-border/60 shadow-sm" : "border-transparent shadow-none"
      )}
    >
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="text-2xl font-bold tracking-tight transition-opacity hover:opacity-80"
        >
          Cartel
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {navigation.map((item) => {
            const active = isActive(item.href);

            return (
              <div key={item.name} className="relative py-1">
                <Link
                  href={item.href}
                  className={cn(
                    "text-sm font-medium text-muted-foreground transition-colors hover:text-foreground",
                    active && "text-foreground"
                  )}
                >
                  {item.name}
                </Link>

                {active ? (
                  <motion.span
                    layoutId="navbar-active-underline"
                    className="absolute inset-x-0 -bottom-1 h-px bg-primary"
                  />
                ) : null}
              </div>
            );
          })}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <Button variant="ghost" onClick={() => router.push("/login")}>
            Sign In
          </Button>

          <Button onClick={() => router.push("/signup")}>
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Open navigation menu"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="right" className="w-[320px] sm:w-[360px]">
          <div className="flex h-full flex-col gap-8">
            <div>
              <Link
                href="/"
                onClick={() => setMobileOpen(false)}
                className="text-2xl font-bold tracking-tight"
              >
                Cartel
              </Link>

              <p className="mt-2 text-sm text-muted-foreground">
                One cart. Every grocery app. Lowest possible price.
              </p>
            </div>

            <nav className="flex flex-1 flex-col gap-2">
              {navigation.map((item) => {
                const active = isActive(item.href);

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "rounded-2xl border px-4 py-3 text-sm font-medium transition-all",
                      active
                        ? "border-primary bg-primary/10 text-foreground"
                        : "border-border bg-transparent text-muted-foreground hover:border-border/80 hover:bg-muted/40 hover:text-foreground"
                    )}
                  >
                    {item.name}
                  </Link>
                );
              })}
            </nav>

            <div className="flex flex-col gap-3 border-t border-border pt-6">
              <Button variant="ghost" onClick={() => navigate("/login")}>
                Sign In
              </Button>

              <Button onClick={() => navigate("/signup")}>
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  );
}