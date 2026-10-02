import { useSyncExternalStore } from "react";

function subscribe(callback: () => void): () => void {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

function getSnapshot(): string {
  return new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
}

function getServerSnapshot(): string {
  return "";
}

export function useHashToken(): string {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
