"use client";

import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";

export default function SavingsCounter() {
  const count = useMotionValue(0);

  const rounded = useTransform(count, (latest) => Math.round(latest));

  useEffect(() => {
    const controls = animate(count, 148, {
      duration: 2.5,
      ease: "easeOut",
    });

    return controls.stop;
  }, [count]);

  return (
    <motion.div
      whileHover={{
        scale: 1.02,
      }}
      className="flex h-full flex-col justify-center rounded-2xl border border-green-500/20 bg-green-500/5 p-6"
    >
      <p className="text-sm font-medium uppercase tracking-wide text-green-500">
        Estimated Savings
      </p>

      <motion.h2
        className="mt-4 text-6xl font-bold text-green-500"
        animate={{
          scale: [1, 1.03, 1],
        }}
        transition={{
          duration: 1.8,
          repeat: Infinity,
        }}
      >
        ₹
        <motion.span>
          {rounded}
        </motion.span>
      </motion.h2>

      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        Based on live prices, memberships,
        delivery fees and platform offers.
      </p>
    </motion.div>
  );
}