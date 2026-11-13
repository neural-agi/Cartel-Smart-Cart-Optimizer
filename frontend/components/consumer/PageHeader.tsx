import type { ReactNode } from "react";

import MotionReveal from "./MotionReveal";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}

export default function PageHeader({ eyebrow, title, description, action }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-5 border-b border-border pb-7 sm:flex-row sm:items-end sm:justify-between">
      <MotionReveal className="max-w-2xl space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">{eyebrow}</p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
        <p className="text-sm leading-6 text-muted-foreground">{description}</p>
      </MotionReveal>
      {action ? <MotionReveal delay={0.08} className="shrink-0">{action}</MotionReveal> : null}
    </header>
  );
}
