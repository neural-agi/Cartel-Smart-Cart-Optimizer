import Link from "next/link";

interface CartelMarkProps {
  href?: string;
  compact?: boolean;
  onNavigate?: () => void;
}

export default function CartelMark({ href = "/home", compact = false, onNavigate }: CartelMarkProps) {
  const content = <span className="inline-flex items-center gap-2 font-semibold tracking-tight"><span className="grid size-7 place-items-center rounded-[9px] bg-primary text-xs font-bold text-primary-foreground shadow-sm">C</span><span className={compact ? "sr-only" : "text-lg"}>Cartel</span></span>;
  return href ? <Link href={href} aria-label="Cartel home" onClick={onNavigate}>{content}</Link> : content;
}
