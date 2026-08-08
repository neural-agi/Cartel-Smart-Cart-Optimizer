"use client";

import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";

const platforms = [
  {
    name: "Blinkit",
    mark: "B",
    accent: "bg-[#f5c400] text-[#171717]",
  },
  {
    name: "Zepto",
    mark: "Z",
    accent: "bg-[#7c3aed] text-white",
  },
  {
    name: "Swiggy Instamart",
    mark: "S",
    accent: "bg-[#fc8019] text-white",
  },
  {
    name: "BigBasket",
    mark: "B",
    accent: "bg-[#84c225] text-white",
  },
];

export default function SupportedPlatforms() {
  return (
    <section id="supported-platforms" className="border-y border-border/60 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mx-auto max-w-3xl text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">
            Supported platforms
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-5xl">
            Your cart, compared where you shop.
          </h2>
          <p className="mt-6 text-base leading-8 text-muted-foreground sm:text-lg">
            Cartel compares your grocery cart across the platforms you already use.
          </p>
        </motion.div>

        <div className="mx-auto mt-14 grid max-w-5xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {platforms.map((platform, index) => (
            <motion.div
              key={platform.name}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.45, delay: index * 0.08, ease: "easeOut" }}
              className="group flex items-center justify-between rounded-2xl border border-border bg-card/60 p-4 transition-colors hover:bg-card"
            >
              <div className="flex items-center gap-3">
                <div
                  className={`flex h-11 w-11 items-center justify-center rounded-xl text-lg font-bold ${platform.accent}`}
                  aria-hidden="true"
                >
                  {platform.mark}
                </div>
                <span className="text-sm font-semibold tracking-tight sm:text-base">
                  {platform.name}
                </span>
              </div>
              <ArrowUpRight
                className="h-4 w-4 text-muted-foreground/60 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                aria-hidden="true"
              />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
