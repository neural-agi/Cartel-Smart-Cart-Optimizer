"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  Check,
  GitCompareArrows,
  IndianRupee,
  ShoppingCart,
  Sparkles,
} from "lucide-react";

const steps = [
  {
    number: "01",
    icon: ShoppingCart,
    title: "Add your cart",
    description: "Tell Cartel what you need, once.",
  },
  {
    number: "02",
    icon: GitCompareArrows,
    title: "Cartel compares prices",
    description: "We check the same items across grocery platforms.",
  },
  {
    number: "03",
    icon: Sparkles,
    title: "Cartel optimizes the combination",
    description: "Offers, fees, and split-cart options are weighed together.",
  },
  {
    number: "04",
    icon: IndianRupee,
    title: "You save money",
    description: "See the lowest practical total before you check out.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-y border-border/60 bg-muted/20 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mx-auto max-w-3xl text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">
            How it works
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-5xl">
            From cart to smarter checkout.
          </h2>
          <p className="mt-6 text-base leading-8 text-muted-foreground sm:text-lg">
            Cartel turns a few minutes of comparison into one clear decision.
          </p>
        </motion.div>

        <div className="relative mt-16 md:mt-20">
          <div className="absolute left-[12.5%] right-[12.5%] top-8 hidden h-px bg-border md:block" />

          <div className="grid gap-10 md:grid-cols-4 md:gap-6">
            {steps.map((step, index) => {
              const Icon = step.icon;

              return (
                <motion.div
                  key={step.number}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.2 }}
                  transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
                  className="relative text-center"
                >
                  <div className="relative z-10 mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-border bg-background shadow-sm">
                    <Icon className="h-6 w-6 text-primary" aria-hidden="true" />
                  </div>

                  <p className="mt-6 text-xs font-semibold tracking-[0.2em] text-muted-foreground">
                    {step.number}
                  </p>
                  <h3 className="mx-auto mt-3 max-w-[15rem] text-lg font-semibold tracking-tight sm:text-xl">
                    {step.title}
                  </h3>
                  <p className="mx-auto mt-3 max-w-[16rem] text-sm leading-6 text-muted-foreground">
                    {step.description}
                  </p>

                  {index < steps.length - 1 && (
                    <ArrowRight
                      className="absolute -bottom-7 left-1/2 h-4 w-4 -translate-x-1/2 rotate-90 text-border md:hidden"
                      aria-hidden="true"
                    />
                  )}
                </motion.div>
              );
            })}
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="mx-auto mt-16 flex max-w-fit items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-sm font-medium text-primary"
          >
            <Check className="h-4 w-4" aria-hidden="true" />
            One cart. A clearer way to save.
          </motion.div>
        </div>
      </div>
    </section>
  );
}
