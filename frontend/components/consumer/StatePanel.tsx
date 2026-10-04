import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface StatePanelProps {
  icon: LucideIcon;
  title: string;
  description: string;
  tone?: "neutral" | "warning" | "danger";
  action?: ReactNode;
}

const toneClasses = {
  neutral: "border-border bg-card",
  warning: "border-amber-500/30 bg-amber-500/5",
  danger: "border-destructive/30 bg-destructive/5",
};

export default function StatePanel({ icon: Icon, title, description, tone = "neutral", action }: StatePanelProps) {
  return (
    <section className={`rounded-2xl border px-6 py-12 text-center ${toneClasses[tone]}`} role={tone === "danger" ? "alert" : undefined}>
      <div className="mx-auto flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <Icon className="size-5" aria-hidden="true" />
      </div>
      <h2 className="mt-4 font-semibold">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </section>
  );
}
