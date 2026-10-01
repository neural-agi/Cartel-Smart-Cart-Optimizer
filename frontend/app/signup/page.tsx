import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";

export default function SignupPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-4 py-12">
      <section className="w-full max-w-md border-y border-border py-8 sm:border sm:px-8">
        <Link href="/" className="text-xl font-bold text-foreground">Cartel</Link>
        <p className="mt-8 text-sm font-medium text-primary">Account access</p>
        <h1 className="mt-2 text-2xl font-semibold">Access is provisioned by your administrator</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          This deployment does not support public self-registration. Ask your Cartel administrator for an access token, then sign in.
        </p>
        <Link href="/login" className={buttonVariants({ className: "mt-7 h-10 w-full" })}>
          Go to sign in <ArrowRight aria-hidden="true" />
        </Link>
      </section>
    </main>
  );
}
