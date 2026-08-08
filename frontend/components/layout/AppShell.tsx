import { ReactNode } from "react";

import AppContainer from "./AppContainer";
import AppNavbar from "./AppNavbar";
import AppSidebar from "./AppSidebar";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-background">
      <AppNavbar />
      <div className="flex min-h-[calc(100vh-4rem)]">
        <div className="hidden shrink-0 lg:block">
          <AppSidebar />
        </div>
        <AppContainer>{children}</AppContainer>
      </div>
    </div>
  );
}
