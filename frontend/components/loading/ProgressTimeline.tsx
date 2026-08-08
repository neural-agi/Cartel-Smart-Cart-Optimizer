"use client";

import { Loader2 } from "lucide-react";

const operations = [
  "Comparing prices across supported platforms...",
  "Checking memberships and subscriptions...",
  "Applying delivery charges...",
  "Calculating platform offers...",
  "Building the cheapest combination...",
];

interface ProgressTimelineProps {
  currentStep?: number;
}

export default function ProgressTimeline({
  currentStep = 2,
}: ProgressTimelineProps) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-2xl border border-border bg-muted/40 px-6 py-4">
      <Loader2 className="h-5 w-5 animate-spin text-primary" />

      <p className="text-sm font-medium text-muted-foreground">
        {operations[currentStep]}
      </p>
    </div>
  );
}