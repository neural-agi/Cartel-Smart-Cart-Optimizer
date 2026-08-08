"use client";

import { motion } from "framer-motion";
import { CheckCircle2, ArrowRight } from "lucide-react";

import AnimatedNumber from "@/components/shared/AnimatedNumber";

interface SuccessOverlayProps {
  savings?: number;
}

export default function SuccessOverlay({
  savings = 148,
}: SuccessOverlayProps) {
  return (
    <motion.div
      initial={{
        opacity: 0,
        backdropFilter: "blur(0px)",
      }}
      animate={{
        opacity: 1,
        backdropFilter: "blur(12px)",
      }}
      exit={{
        opacity: 0,
        transition: {
          duration: 0.4,
        },
      }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/75"
    >
      <motion.div
        initial={{
          scale: 0.92,
          opacity: 0,
          y: 20,
        }}
        animate={{
          scale: 1,
          opacity: 1,
          y: 0,
        }}
        transition={{
          type: "spring",
          stiffness: 140,
          damping: 18,
        }}
        className="w-full max-w-md rounded-3xl border border-border bg-card p-10 shadow-2xl"
      >
        {/* Success Icon */}

        <motion.div
          initial={{
            scale: 0,
            rotate: -25,
          }}
          animate={{
            scale: 1,
            rotate: 0,
          }}
          transition={{
            type: "spring",
            stiffness: 260,
            damping: 16,
            delay: 0.15,
          }}
          className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-green-500/10"
        >
          <CheckCircle2 className="h-10 w-10 text-green-500" />
        </motion.div>

        {/* Title */}

        <motion.h2
          initial={{
            opacity: 0,
            y: 10,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
          transition={{
            delay: 0.3,
          }}
          className="mt-8 text-center text-3xl font-bold"
        >
          Optimization Complete
        </motion.h2>

        {/* Subtitle */}

        <motion.p
          initial={{
            opacity: 0,
          }}
          animate={{
            opacity: 1,
          }}
          transition={{
            delay: 0.45,
          }}
          className="mt-3 text-center text-muted-foreground"
        >
          We found a cheaper way to buy your groceries.
        </motion.p>

        {/* Savings */}

        <motion.div
          initial={{
            opacity: 0,
            scale: 0.9,
          }}
          animate={{
            opacity: 1,
            scale: 1,
          }}
          transition={{
            delay: 0.6,
          }}
          className="mt-10 rounded-2xl border border-green-500/20 bg-green-500/5 py-8 text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-widest text-green-500">
            You Saved
          </p>

          <div className="mt-3 text-6xl font-bold text-green-500">
            <AnimatedNumber
              value={savings}
              prefix="₹"
              duration={1.2}
            />
          </div>
        </motion.div>

        {/* Footer */}

        <motion.div
          initial={{
            opacity: 0,
            y: 8,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
          transition={{
            delay: 0.8,
          }}
          className="mt-8 flex items-center justify-center gap-2 text-sm text-muted-foreground"
        >
          <span>Opening optimized cart</span>

          <ArrowRight className="h-4 w-4 animate-pulse" />
        </motion.div>
      </motion.div>
    </motion.div>
  );
}