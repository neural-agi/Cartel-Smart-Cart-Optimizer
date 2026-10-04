export function consumerReason(value: string): string {
  const reason = value.toLowerCase();
  if (reason.includes("checkout") || reason.includes("ece")) return "Checkout information is not available for this comparison.";
  if (reason.includes("access") || reason.includes("unavailable") || reason.includes("provider")) return "A supported retailer source is unavailable right now.";
  if (reason.includes("stale") || reason.includes("revision")) return "This list changed. Start a new comparison from the current list.";
  if (reason.includes("identity") || reason.includes("match") || reason.includes("variant")) return "Cartel could not confirm the exact product and pack for this request.";
  return "Cartel could not complete this comparison from the information available.";
}

export function consumerReasons(values: readonly string[]): string[] {
  return [...new Set(values.map(consumerReason))];
}
