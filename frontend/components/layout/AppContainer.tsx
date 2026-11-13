import { ReactNode } from "react";

interface AppContainerProps {
  children: ReactNode;
  className?: string;
}

export default function AppContainer({
  children,
  className = "",
}: AppContainerProps) {
  return (
    <main
      className={`mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-10 lg:py-10 ${className}`}
    >
      {children}
    </main>
  );
}
