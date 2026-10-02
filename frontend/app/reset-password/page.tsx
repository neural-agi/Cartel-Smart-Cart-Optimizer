"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useHashToken } from "@/lib/useHashToken";

export default function ResetPasswordPage() {
  const router = useRouter(); const token = useHashToken();
  const [password, setPassword] = useState(""); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    try { const response = await apiFetch("/api/v2/auth/password/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token, new_password: password }) }); if (!response.ok) throw new Error("This recovery link is invalid or expired."); router.replace("/login"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Password reset failed."); }
  }
  return <main className="grid min-h-screen place-items-center px-4"><form onSubmit={submit} className="w-full max-w-md space-y-5"><h1 className="text-2xl font-semibold">Choose a new password</h1><Input type="password" autoComplete="new-password" minLength={12} required value={password} onChange={(event) => setPassword(event.target.value)} aria-label="New password" />{error && <p role="alert">{error}</p>}<Button className="w-full">Reset password</Button></form></main>;
}
