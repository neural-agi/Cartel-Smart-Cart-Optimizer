"use client";

import { useEffect, useState } from "react";

import { loadingMessages } from "@/constants/loadingMessages";

export default function LoadingFact() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((current) => (current + 1) % loadingMessages.length);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const current = loadingMessages[index];

  return (
  <div className="flex h-full flex-col justify-center rounded-2xl border border-border bg-card p-6">
    <p className="text-sm font-semibold uppercase tracking-wide text-primary">
      {current.title}
    </p>

    <p className="mt-4 text-lg leading-8">
      {current.message}
    </p>
  </div>
);
}