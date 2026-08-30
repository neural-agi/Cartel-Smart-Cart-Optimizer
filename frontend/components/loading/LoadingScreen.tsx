"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import CartJourney from "./CartJourney";
import LoadingFact from "./LoadingFact";
import ProgressTimeline from "./ProgressTimeline";
import SavingsCounter from "./SavingsCounter";
import SuccessOverlay from "./SuccessOverlay";

interface LoadingScreenProps {
  isComplete?: boolean;
  savings?: number;
}

export default function LoadingScreen({
  isComplete = false,
  savings = 148,
}: LoadingScreenProps) {
  const router = useRouter();
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    if (!isComplete) {
      return;
    }

    const showTimeout = window.setTimeout(() => setShowSuccess(true), 0);
    const timeout = window.setTimeout(() => {
      router.push("/results");
    }, 1800);

    return () => {
      window.clearTimeout(showTimeout);
      window.clearTimeout(timeout);
    };
  }, [isComplete, router]);

  return (
    <AnimatePresence mode="wait">
      {!showSuccess ? (
        <motion.div
          key="loading"
          initial={{
            opacity: 0,
          }}
          animate={{
            opacity: 1,
          }}
          exit={{
            opacity: 0,
            transition: {
              duration: 0.35,
            },
          }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/90 p-4 backdrop-blur-xl sm:p-6"
        >
          <motion.div
            initial={{
              opacity: 0,
              scale: 0.96,
              y: 12,
            }}
            animate={{
              opacity: 1,
              scale: 1,
              y: 0,
            }}
            transition={{
              duration: 0.4,
              ease: "easeOut",
            }}
            className="w-full max-w-5xl rounded-3xl border border-border bg-card/90 p-6 shadow-2xl sm:p-8 lg:p-12"
          >
            {/* Header */}

            <motion.div
              initial={{
                opacity: 0,
                y: 12,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                delay: 0.15,
                duration: 0.45,
                ease: "easeOut",
              }}
              className="text-center"
            >
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Building your cheapest grocery cart...
              </h2>

              <div className="mx-auto mt-5 max-w-2xl space-y-1 text-sm text-muted-foreground sm:text-base">
                <p>Comparing prices across supported platforms</p>
                <p>Applying memberships and delivery fees</p>
                <p>Building your lowest possible total</p>
              </div>
            </motion.div>

            {/* Cart Journey */}

            <motion.div
              initial={{
                opacity: 0,
                y: 18,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                delay: 0.35,
                duration: 0.5,
                ease: "easeOut",
              }}
              className="mt-10 sm:mt-12"
            >
              <CartJourney />
            </motion.div>

            {/* Current Backend Step */}

            <motion.div
              initial={{
                opacity: 0,
                y: 18,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                delay: 0.55,
                duration: 0.5,
                ease: "easeOut",
              }}
              className="mt-8"
            >
              <ProgressTimeline />
            </motion.div>

            {/* Bottom Cards */}

            <motion.div
              initial={{
                opacity: 0,
                y: 18,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                delay: 0.7,
                duration: 0.5,
                ease: "easeOut",
              }}
              className="mt-8 grid gap-6 lg:mt-10 lg:grid-cols-[300px_1fr]"
            >
              <SavingsCounter />

              <LoadingFact />
            </motion.div>
          </motion.div>
        </motion.div>
      ) : (
        <SuccessOverlay
          key="success"
          savings={savings}
        />
      )}
    </AnimatePresence>
  );
}
