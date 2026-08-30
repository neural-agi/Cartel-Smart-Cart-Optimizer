"use client";

import { motion } from "framer-motion";
import { ArrowDown, Clock3, IndianRupee, Layers3 } from "lucide-react";

const problems = [
  {
    icon: IndianRupee,
    title: "Prices keep changing",
    description:
      "The same products can have different prices, discounts, and delivery charges across grocery platforms.",
  },
  {
    icon: Layers3,
    title: "Every platform has different deals",
    description:
      "Membership benefits, platform offers, minimum order values, and delivery fees make the cheapest option difficult to spot.",
  },
  {
    icon: Clock3,
    title: "Comparing everything takes time",
    description:
      "Checking multiple apps item by item turns a simple grocery run into unnecessary tab-hopping and mental arithmetic.",
  },
];

export default function Problem() {
  return (
    <section
      id="problem"
      className="relative overflow-hidden border-t border-border/50 py-24 sm:py-32"
    >
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        {/* Section Header */}

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mx-auto max-w-3xl text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">
            The problem
          </p>

          <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-5xl">
            Grocery shopping shouldn&apos;t require
            <span className="text-muted-foreground">
              {" "}a spreadsheet.
            </span>
          </h2>

          <p className="mt-6 text-base leading-8 text-muted-foreground sm:text-lg">
            You already know what you want to buy. The annoying part is
            figuring out where to buy each item for the lowest total.
          </p>
        </motion.div>

        {/* Problem Cards */}

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {problems.map((problem, index) => {
            const Icon = problem.icon;

            return (
              <motion.div
                key={problem.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{
                  duration: 0.5,
                  delay: index * 0.1,
                  ease: "easeOut",
                }}
                whileHover={{ y: -4 }}
                className="group rounded-3xl border border-border bg-card/60 p-7 transition-colors hover:bg-card"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border bg-background transition-colors group-hover:border-primary/30 group-hover:bg-primary/10">
                  <Icon className="h-5 w-5 text-primary" />
                </div>

                <h3 className="mt-6 text-xl font-semibold tracking-tight">
                  {problem.title}
                </h3>

                <p className="mt-3 leading-7 text-muted-foreground">
                  {problem.description}
                </p>
              </motion.div>
            );
          })}
        </div>

        {/* Transition */}

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="mt-16 flex flex-col items-center text-center"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card">
            <ArrowDown className="h-4 w-4 text-muted-foreground" />
          </div>

          <p className="mt-4 text-sm font-medium text-muted-foreground">
            Cartel handles the comparison for you.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
