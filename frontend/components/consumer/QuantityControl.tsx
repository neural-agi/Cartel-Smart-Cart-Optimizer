import { Minus, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";

interface QuantityControlProps {
  value: number;
  label: string;
  disabled?: boolean;
  onChange: (value: number) => void;
}

export default function QuantityControl({ value, label, disabled = false, onChange }: QuantityControlProps) {
  return (
    <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-background p-1" aria-label={`${label}, quantity ${value}`}>
      <Button type="button" variant="ghost" size="icon-sm" aria-label={`Decrease ${label}`} disabled={disabled} onClick={() => onChange(value - 1)}><Minus className="size-3.5" aria-hidden="true" /></Button>
      <span className="min-w-7 text-center text-sm font-medium tabular-nums" aria-live="polite">{value}</span>
      <Button type="button" variant="ghost" size="icon-sm" aria-label={`Increase ${label}`} disabled={disabled || value >= 999} onClick={() => onChange(value + 1)}><Plus className="size-3.5" aria-hidden="true" /></Button>
    </div>
  );
}
