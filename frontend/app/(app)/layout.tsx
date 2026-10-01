import type { ReactNode } from "react";

import AppAuthGuard from "@/components/auth/AppAuthGuard";

export default function AuthenticatedAppLayout({ children }: { children: ReactNode }) {
  return <AppAuthGuard>{children}</AppAuthGuard>;
}
