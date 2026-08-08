"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";

const plans = [
  {
    name: "Explore",
    description: "A simple starting point for trying Cartel with a grocery cart.",
    note: "Development preview",
    featured: false,
    features: ["Add a grocery cart", "Compare supported platforms", "See the optimized combination"],
  },
  {
    name: "Plan",
    description: "For shoppers who want a more complete view of every cart decision.",
    note: "Recommended preview",
    featured: true,
    features: ["Everything in Explore", "Account-aware evaluation", "Clear cost and savings context"],
  },
  {
    name: "More to come",
    description: "Future plans will reflect the product as real usage and billing needs take shape.",
    note: "Not available yet",
    featured: false,
    features: ["No billing details set", "No payment integration", "No commitment required"],
  },
];

export default function Pricing() {
  return (
    <section id="pricing" className="border-y border-border/60 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mx-auto max-w-3xl text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">
            Pricing preview
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-5xl">
            Start with a smarter cart.
          </h2>
          <p className="mt-6 text-base leading-8 text-muted-foreground sm:text-lg">
            Plans are still being shaped. This preview shows the intended product path, not final commercial pricing.
          </p>
        </motion.div>

        <div className="mx-auto mt-14 grid max-w-6xl gap-5 lg:grid-cols-3">
          {plans.map((plan, index) => (
            <motion.article
              key={plan.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: index * 0.08, ease: "easeOut" }}
              className={`relative flex h-full flex-col rounded-2xl border p-7 ${
                plan.featured
                  ? "border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/10"
                  : "border-border bg-card"
              }`}
            >
              <p className={`text-xs font-semibold uppercase tracking-[0.18em] ${plan.featured ? "text-primary-foreground/70" : "text-primary"}`}>
                {plan.note}
              </p>
              <h3 className="mt-5 text-2xl font-semibold tracking-tight">{plan.name}</h3>
              <p className={`mt-3 min-h-20 text-sm leading-6 ${plan.featured ? "text-primary-foreground/75" : "text-muted-foreground"}`}>
                {plan.description}
              </p>
              <div className={`my-6 h-px ${plan.featured ? "bg-primary-foreground/20" : "bg-border"}`} />
              <ul className="space-y-3 text-sm">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <Check className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
