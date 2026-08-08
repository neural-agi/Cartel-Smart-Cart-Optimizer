import { ReactNode } from "react";

import AppContainer from "./AppContainer";
import AppNavbar from "./AppNavbar";

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({
  children,
}: AppShellProps) {
  return (
    <>
      <AppNavbar />

      <AppContainer>
        {children}
      </AppContainer>
    </>
  );
}