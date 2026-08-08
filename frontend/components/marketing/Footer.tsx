import Link from "next/link";

const navigation = [
  { name: "Features", href: "/#features" },
  { name: "How it Works", href: "/#how-it-works" },
  { name: "Pricing", href: "/#pricing" },
  { name: "FAQ", href: "/#faq" },
  { name: "GitHub", href: "https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer" },
];

export default function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-8 px-6 py-12 md:flex-row">
        <div>
          <h3 className="text-2xl font-bold tracking-tight">
            Cartel
          </h3>

          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            One cart. Every grocery app. Lowest possible price.
          </p>
        </div>

        <nav className="flex flex-wrap items-center gap-6">
          {navigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              target={item.name === "GitHub" ? "_blank" : undefined}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {item.name}
            </Link>
          ))}
        </nav>
      </div>

      <div className="border-t border-border">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 text-sm text-muted-foreground">
          <span>© {new Date().getFullYear()} Cartel. All rights reserved.</span>

          <span>Built with ❤️ in India.</span>
        </div>
      </div>
    </footer>
  );
}
